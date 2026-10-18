import hashlib
import hmac
import secrets
from datetime import timedelta

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import database
from .models import LoginSession, User, now

hasher = PasswordHasher(type=Type.ID)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
COOKIE = "planner_session"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(raw_token: str) -> str:
    return hmac.new(raw_token.encode(), b"planner-csrf-v1", hashlib.sha256).hexdigest()


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def current_user(request: Request, db: Session = Depends(database)) -> User:
    raw = request.cookies.get(COOKIE, "")
    if not raw or len(raw) > 128:
        raise HTTPException(401, "Please sign in")
    session = db.get(LoginSession, digest(raw))
    if not session or session.expires_at <= now():
        raise HTTPException(401, "Your session has expired")
    user = db.get(User, session.user_id)
    if not user or not user.active:
        raise HTTPException(401, "Please sign in")
    return user


def require_owner(user: User = Depends(current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(403, "Only the owner can make changes")
    return user


def require_csrf(request: Request) -> None:
    raw = request.cookies.get(COOKIE, "")
    supplied = request.headers.get("x-csrf-token", "")
    if not raw or not hmac.compare_digest(csrf_for(raw).encode(), supplied.encode()):
        raise HTTPException(403, "Refresh this page before trying again")


def public_user(user: User) -> dict:
    return {"id": str(user.id), "username": user.username, "display_name": user.display_name,
            "role": user.role, "side": user.side, "active": user.active, "version": user.version}
