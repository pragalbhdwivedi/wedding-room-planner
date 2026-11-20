"""Private guest identity images; no public file URLs or family-view access."""
import hashlib
import io
import uuid
import warnings
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import defer

from .models import Audit, Guest, GuestDocument, User
from .planning_api import DB, Editor, WRITE, record
from .planning_store import locked_state
from .security import current_user

router = APIRouter(prefix="/api/planning")
MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_DOCUMENTS = 12


def document_reader(user: Annotated[User, Depends(current_user)]):
    if user.role not in {"owner", "editor", "reception"}:
        raise HTTPException(403, "Guest IDs are available only to editors and Reception")
    return user


Reader = Annotated[User, Depends(document_reader)]


def guest_or_404(db, guest_id):
    guest = db.get(Guest, guest_id)
    if not guest:
        raise HTTPException(404, "Guest not found")
    return guest


def prepare_image(content: bytes) -> bytes:
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Choose an ID image of up to 5 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(415, "Choose a JPG, PNG or WebP image")
                if source.width * source.height > MAX_PIXELS or getattr(source, "n_frames", 1) != 1:
                    raise HTTPException(415, "Choose one still ID image of at most 20 megapixels")
                source.load()
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((3200, 3200))
                # Re-encode pixels only. Do not retain location, embedded files or EXIF metadata.
                output = io.BytesIO()
                image.save(output, "JPEG", quality=95, optimize=True)
                result = output.getvalue()
        if len(result) > MAX_BYTES:
            raise HTTPException(413, "Choose a smaller ID image")
        return result
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise HTTPException(415, "The file is not a supported, readable ID image") from None


def metadata(row):
    return {"id": str(row.id), "created_at": row.created_at.isoformat(),
            "guest_id": str(row.guest_id) if row.guest_id else None, "label": row.label}


def store_document(db, guest_id, content, user, revision):
    """Shared import/UI path: validate guest, lock revision, deduplicate, audit."""
    encoded = prepare_image(content)
    source_hash = hashlib.sha256(content).hexdigest()
    state = locked_state(db, revision)
    guest_or_404(db, guest_id)
    existing = db.scalar(select(GuestDocument).options(defer(GuestDocument.content)).where(
        GuestDocument.guest_id == guest_id, GuestDocument.source_hash == source_hash))
    if existing:
        return {"revision": state.revision, "document": metadata(existing), "duplicate": True}
    count = db.scalar(select(func.count()).select_from(GuestDocument).where(GuestDocument.guest_id == guest_id))
    if count >= MAX_DOCUMENTS:
        raise HTTPException(409, "This guest already has 12 ID images; ask an editor to review duplicates")
    row = GuestDocument(guest_id=guest_id, uploaded_by=user.id, source_hash=source_hash, content=encoded, label="Guest ID")
    db.add(row)
    db.flush()
    result = record(db, user, state, "guest_document.uploaded", {"guest_id": str(guest_id), "document_id": str(row.id)})
    return {**result, "document": metadata(row), "duplicate": False}


@router.get("/guests/{guest_id}/documents")
def list_documents(guest_id: uuid.UUID, user: Reader, db: DB):
    guest_or_404(db, guest_id)
    rows = db.scalars(select(GuestDocument).options(defer(GuestDocument.content)).where(
        GuestDocument.guest_id == guest_id).order_by(GuestDocument.created_at, GuestDocument.id))
    return {"documents": [metadata(row) for row in rows]}


@router.post("/guests/{guest_id}/documents", dependencies=WRITE)
async def upload_document(guest_id: uuid.UUID, file: UploadFile, user: Editor, db: DB,
                          revision: Annotated[int, Form(ge=1)]):
    try:
        content = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    return store_document(db, guest_id, content, user, revision)


def audit_read(db, user, guest_id, action, document_id=None):
    details = {"guest_id": str(guest_id)}
    if document_id:
        details["document_id"] = str(document_id)
    db.add(Audit(actor_id=user.id, action=action, entity_id=str(guest_id), details=details))
    db.commit()


@router.get("/guests/{guest_id}/documents/{document_id}/image")
def image_document(guest_id: uuid.UUID, document_id: uuid.UUID, user: Reader, db: DB):
    guest_or_404(db, guest_id)
    row = db.scalar(select(GuestDocument).where(GuestDocument.id == document_id, GuestDocument.guest_id == guest_id))
    if not row:
        raise HTTPException(404, "ID image not found")
    content = row.content
    audit_read(db, user, guest_id, "guest_document.viewed", row.id)
    return Response(content, media_type="image/jpeg", headers={
        "Cache-Control": "no-store", "Content-Disposition": 'inline; filename="guest-id.jpg"',
        "Cross-Origin-Resource-Policy": "same-origin", "X-Content-Type-Options": "nosniff"})


def build_pdf(rows):
    pages = []
    try:
        for index, row in enumerate(rows, 1):
            with Image.open(io.BytesIO(row.content)) as source:
                image = source.convert("RGB")
                image.thumbnail((1120, 1534))
                page = Image.new("RGB", (1240, 1754), "white")
                page.paste(image, ((1240 - image.width) // 2, (1754 - image.height) // 2))
                ImageDraw.Draw(page).text((60, 35), f"Guest ID - page {index} of {len(rows)}", fill="black")
                pages.append(page)
        output = io.BytesIO()
        pages[0].save(output, "PDF", save_all=True, append_images=pages[1:], resolution=150.0,
                      title="Guest identification", author="Wedding Room Planner")
        content = output.getvalue()
    finally:
        for page in pages:
            page.close()
    return content


def pdf_response(content, identity, download):
    return Response(content, media_type="application/pdf", headers={
        "Cache-Control": "no-store", "Content-Disposition": f'{"attachment" if download else "inline"}; filename="guest-id-{identity}.pdf"',
        "Cross-Origin-Resource-Policy": "same-origin", "X-Content-Type-Options": "nosniff"})


@router.get("/guests/{guest_id}/documents.pdf")
def guest_pdf(guest_id: uuid.UUID, user: Reader, db: DB, download: bool = False):
    guest_or_404(db, guest_id)
    rows = list(db.scalars(select(GuestDocument).where(GuestDocument.guest_id == guest_id)
                          .order_by(GuestDocument.created_at, GuestDocument.id)))
    if not rows:
        raise HTTPException(404, "No ID images uploaded for this guest")
    content = build_pdf(rows)
    audit_read(db, user, guest_id, "guest_document.pdf_downloaded" if download else "guest_document.pdf_viewed")
    return pdf_response(content, guest_id, download)


def store_intake(db, content, user, revision, label="ID awaiting match"):
    encoded = prepare_image(content)
    source_hash = hashlib.sha256(content).hexdigest()
    state = locked_state(db, revision)
    existing = db.scalar(select(GuestDocument).options(defer(GuestDocument.content)).where(
        GuestDocument.source_hash == source_hash).limit(1))
    if existing:
        return {"revision": state.revision, "document": metadata(existing), "duplicate": True}
    count = db.scalar(select(func.count()).select_from(GuestDocument).where(GuestDocument.guest_id.is_(None)))
    if count >= 1000:
        raise HTTPException(409, "Review the existing ID collection before adding more images")
    row = GuestDocument(guest_id=None, uploaded_by=user.id, source_hash=source_hash, content=encoded,
                        label=label.strip()[:100] or "ID awaiting match")
    db.add(row); db.flush()
    result = record(db, user, state, "guest_document.collected", {"document_id": str(row.id)})
    return {**result, "document": metadata(row), "duplicate": False}


@router.get("/id-collection")
def collection(user: Reader, db: DB):
    rows = db.scalars(select(GuestDocument).options(defer(GuestDocument.content))
                      .order_by(GuestDocument.created_at, GuestDocument.id))
    return {"documents": [metadata(row) for row in rows]}


@router.post("/id-collection", dependencies=WRITE)
async def collect_image(file: UploadFile, user: Editor, db: DB, revision: Annotated[int, Form(ge=1)],
                         label: Annotated[str, Form(max_length=100)] = "ID awaiting match"):
    try:
        content = await file.read(MAX_BYTES + 1)
    finally:
        await file.close()
    return store_intake(db, content, user, revision, label)


def collection_row(db, identity):
    row = db.get(GuestDocument, identity)
    if not row:
        raise HTTPException(404, "ID image not found")
    return row


@router.get("/id-collection/{identity}/image")
def collection_image(identity: uuid.UUID, user: Reader, db: DB):
    row = collection_row(db, identity)
    content = row.content
    audit_read(db, user, row.guest_id or row.id, "guest_document.viewed", row.id)
    return Response(content, media_type="image/jpeg", headers={"Cache-Control": "no-store",
        "Cross-Origin-Resource-Policy": "same-origin", "X-Content-Type-Options": "nosniff"})


@router.get("/id-collection/{identity}/document.pdf")
def collection_pdf(identity: uuid.UUID, user: Reader, db: DB, download: bool = False):
    row = collection_row(db, identity)
    content = build_pdf([row])
    audit_read(db, user, row.guest_id or row.id, "guest_document.pdf_downloaded" if download else "guest_document.pdf_viewed", row.id)
    return pdf_response(content, row.id, download)


class MatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guest_id: uuid.UUID
    revision: int = Field(ge=1)


@router.post("/id-collection/{identity}/match", dependencies=WRITE)
def match_document(identity: uuid.UUID, body: MatchInput, user: Editor, db: DB):
    state = locked_state(db, body.revision)
    row = collection_row(db, identity)
    guest_or_404(db, body.guest_id)
    if row.guest_id:
        raise HTTPException(409, "This image is already matched to a guest")
    duplicate = db.scalar(select(GuestDocument.id).where(GuestDocument.guest_id == body.guest_id,
        GuestDocument.source_hash == row.source_hash))
    if duplicate:
        raise HTTPException(409, "This image is already attached to that guest")
    count = db.scalar(select(func.count()).select_from(GuestDocument).where(GuestDocument.guest_id == body.guest_id))
    if count >= MAX_DOCUMENTS:
        raise HTTPException(409, "This guest already has 12 ID images")
    row.guest_id = body.guest_id
    result = record(db, user, state, "guest_document.matched", {"guest_id": str(body.guest_id), "document_id": str(row.id)})
    return {**result, "document": metadata(row)}
