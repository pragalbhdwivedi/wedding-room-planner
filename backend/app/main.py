import hmac
import secrets
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .config import settings
from .db import database
from .models import Audit, EventPolicy, Hotel, LoginSession, LoginThrottle, Room, StaffBed, User, now
from .security import COOKIE, csrf_for, current_user, digest, dummy_hash, hasher, public_user, require_csrf, require_editor, verify_password

app = FastAPI(title="Wedding Room Planner", docs_url=None, redoc_url=None, openapi_url=None)
DB = Annotated[Session, Depends(database)]
Editor = Annotated[User, Depends(require_editor)]
SignedIn = Annotated[User, Depends(current_user)]


@app.middleware("http")
async def transport_guard(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/planning/import/preview":
        try:
            length=int(request.headers.get("content-length", "-1"))
        except ValueError:
            return JSONResponse({"detail":"Invalid upload length"},status_code=400)
        if length<0:return JSONResponse({"detail":"Upload Content-Length is required"},status_code=411)
        if length>5500000:return JSONResponse({"detail":"Workbook exceeds the upload limit"},status_code=413)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin.rstrip("/") not in settings().origins):
            return JSONResponse({"detail": "This request came from an untrusted page"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # Never reflect password or setup-token input in validation responses.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse({"detail": "Please check the highlighted fields", "errors": errors}, status_code=422)


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Payload):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]+$")
    password: str = Field(min_length=1, max_length=256)


class Setup(Credentials):
    display_name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=14, max_length=256)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a display name")
        return value.strip()


class ViewerCreate(Setup):
    role: Literal["editor", "family", "reception"]
    side: Literal["bride", "groom"] | None = None

    @model_validator(mode="after")
    def valid_scope(self):
        if (self.role == "family") != (self.side is not None):
            raise ValueError("Family viewers require a side; editors and reception have no side")
        return self


class ViewerUpdate(Payload):
    version: int = Field(ge=1)
    display_name: str = Field(min_length=1, max_length=80)
    role: Literal["editor", "family", "reception"]
    side: Literal["bride", "groom"] | None = None
    active: bool
    password: str | None = Field(default=None, min_length=14, max_length=256)

    @field_validator("display_name")
    @classmethod
    def clean_name(cls, value):
        if not value.strip():
            raise ValueError("Enter a display name")
        return value.strip()

    @model_validator(mode="after")
    def valid_scope(self):
        if (self.role == "family") != (self.side is not None):
            raise ValueError("Family viewers require a side; editors and reception have no side")
        return self


def audit(db: Session, actor: User, action: str, entity_id: str, details: dict):
    db.add(Audit(actor_id=actor.id, action=action, entity_id=entity_id, details=details))


def start_session(db: Session, user: User, response: Response) -> dict:
    raw = secrets.token_urlsafe(32)
    db.add(LoginSession(token_hash=digest(raw), user_id=user.id, expires_at=now() + timedelta(hours=settings().session_hours)))
    db.commit()
    response.set_cookie(COOKIE, raw, max_age=settings().session_hours * 3600, httponly=True,
                        secure=settings().cookie_secure, samesite="strict", path="/")
    return {"user": public_user(user), "csrf_token": csrf_for(raw)}


@app.get("/api/health")
def health(db: DB):
    revision = db.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "0006_editors_child_beds":
        raise HTTPException(503, "Database migration is pending")
    return {"status": "ok"}


@app.get("/api/setup/status")
def setup_status(db: DB):
    return {"setup_required": db.scalar(select(User.id).where(User.role == "owner")) is None}


@app.post("/api/setup", status_code=201)
def setup(body: Setup, request: Request, response: Response, db: DB):
    expected = Path(settings().bootstrap_token_file).read_text().strip()
    supplied = request.headers.get("x-bootstrap-token", "")
    if len(expected) < 32 or not hmac.compare_digest(expected.encode(), supplied.encode()):
        raise HTTPException(403, "The setup key is not valid")
    db.execute(text("SELECT pg_advisory_xact_lock(90029601)"))
    if db.scalar(select(User.id).where(User.role == "owner")) is not None:
        raise HTTPException(409, "The owner account is already configured")
    user = User(username=body.username.lower(), display_name=body.display_name.strip(),
                password_hash=hasher.hash(body.password), role="owner", side=None, active=True)
    db.add(user)
    db.flush()
    audit(db, user, "owner.created", str(user.id), {})
    return start_session(db, user, response)


@app.post("/api/auth/login")
def login(body: Credentials, request: Request, response: Response, db: DB):
    username = body.username.lower()
    address = request.client.host if request.client else "unknown"
    keys = [(digest("user:" + username), 5), (digest("address:" + address), 25)]
    throttles = []
    for key, limit in sorted(keys):
        lock_id = int.from_bytes(bytes.fromhex(key[:16]), "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        throttle = db.get(LoginThrottle, key)
        if not throttle:
            throttle = LoginThrottle(key=key, failures=0, started_at=now())
            db.add(throttle)
        if throttle.started_at < now() - timedelta(minutes=15):
            throttle.failures, throttle.started_at = 0, now()
        if throttle.failures >= limit:
            db.commit()
            raise HTTPException(429, "Too many attempts. Please wait 15 minutes.", headers={"Retry-After": "900"})
        throttles.append(throttle)
    user = db.scalar(select(User).where(User.username == username))
    valid = verify_password(user.password_hash if user and user.active else dummy_hash, body.password)
    if not valid or not user or not user.active:
        for throttle in throttles:
            throttle.failures += 1
        db.commit()
        raise HTTPException(401, "Username or password is incorrect")
    # A successful login clears only the account throttle, not shared-source abuse history.
    for throttle in throttles:
        if throttle.key == keys[0][0]:
            throttle.failures = 0
    audit(db, user, "session.created", str(user.id), {})
    return start_session(db, user, response)


@app.get("/api/auth/me")
def me(user: SignedIn, request: Request):
    return {"user": public_user(user), "csrf_token": csrf_for(request.cookies[COOKIE])}


@app.post("/api/auth/logout", dependencies=[Depends(require_csrf)])
def logout(user: SignedIn, request: Request, response: Response, db: DB):
    db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(request.cookies[COOKIE])))
    audit(db, user, "session.ended", str(user.id), {})
    db.commit()
    response.delete_cookie(COOKIE, path="/", secure=settings().cookie_secure, httponly=True, samesite="strict")
    return {"ok": True}


@app.get("/api/users")
def list_users(editor: Editor, db: DB):
    return {"users": [public_user(u) for u in db.scalars(select(User).order_by(User.created_at))]}


@app.post("/api/users", status_code=201, dependencies=[Depends(require_csrf)])
def create_user(body: ViewerCreate, editor: Editor, db: DB):
    user = User(username=body.username.lower(), display_name=body.display_name.strip(),
                password_hash=hasher.hash(body.password), role=body.role, side=body.side, active=True)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That username is already in use")
    audit(db, editor, "account.created", str(user.id), {"role": user.role, "side": user.side})
    db.commit()
    return public_user(user)


@app.patch("/api/users/{user_id}", dependencies=[Depends(require_csrf)])
def update_user(user_id: uuid.UUID, body: ViewerUpdate, editor: Editor, db: DB):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise HTTPException(404, "Viewer not found")
    if user.role == "owner":
        raise HTTPException(403, "The owner account cannot be changed here")
    if user.version != body.version:
        raise HTTPException(409, "This account changed in another session. Refresh and try again.")
    before = {"role": user.role, "side": user.side, "active": user.active}
    user.display_name, user.role, user.side, user.active = body.display_name.strip(), body.role, body.side, body.active
    if body.password:
        user.password_hash = hasher.hash(body.password)
    user.version += 1
    # Any access/password change revokes existing sessions immediately.
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
    audit(db, editor, "account.updated", str(user.id), {"before": before, "after": {"role": user.role, "side": user.side, "active": user.active}, "password_reset": body.password is not None})
    db.commit()
    return public_user(user)


@app.get("/api/inventory")
def inventory(user: SignedIn, db: DB):
    hotels = [{"id": h.id, "name": h.name, "kind": h.kind} for h in db.scalars(select(Hotel).order_by(Hotel.id))]
    rooms = [{"id": r.id, "hotel_id": r.hotel_id, "number": r.number, "category": r.category,
              "block": r.block, "floor": r.floor, "bed_type": r.bed_type, "adult_capacity": r.adult_capacity}
             for r in db.scalars(select(Room).order_by(Room.hotel_id, Room.block, Room.floor, Room.number, Room.id))]
    policy = db.get(EventPolicy, 1)
    result = {"hotels": hotels, "rooms": rooms, "family_reserve_pending": policy.family_reserve,
              "staff_beds": [{"id": b.id, "hotel_id": b.hotel_id} for b in db.scalars(select(StaffBed).order_by(StaffBed.id))],
              "stage": "planning", "guest_entry_available": True, "allocation_available": True}
    if user.role in {"owner", "editor"}:
        result["cost_policy"] = {"wyndham_allowance": policy.wyndham_allowance,
            "wyndham_excess_paise": policy.wyndham_excess_paise, "staff_meal_paise": policy.staff_meal_paise,
            "second_hotel_day_paise": policy.second_hotel_day_paise, "second_hotel_included": policy.second_hotel_included,
            "second_hotel_rate_status": "provisional", "non_resident_meal_rate": None}
    return result


from .planning_api import router as planning_router
from .spreadsheet_api import router as spreadsheet_router
app.include_router(planning_router)
app.include_router(spreadsheet_router)
