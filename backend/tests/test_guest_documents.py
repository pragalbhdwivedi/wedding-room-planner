import io
import uuid

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.db import SessionLocal
from app.main import app
from app.models import Audit, GuestDocument
from test_planning import PASSWORD, family, headers, plan, revision


def image_bytes(color="white"):
    content = io.BytesIO()
    Image.new("RGB", (400, 250), color).save(content, "PNG")
    return content.getvalue()


def upload(client, auth, guest, data=None, rev=None):
    return client.post(f"/api/planning/guests/{guest['id']}/documents", headers=headers(auth),
        data={"revision": revision(client) if rev is None else rev},
        files={"file": ("synthetic-id.png", image_bytes() if data is None else data, "image/png")})


def test_id_upload_deduplication_pdf_and_audit(client, owner):
    guest = family(client, owner)[0]
    before = plan(client)
    response = upload(client, owner, guest)
    assert response.status_code == 200, response.text
    doc = response.json()["document"]
    rev = revision(client)
    assert upload(client, owner, guest).json()["duplicate"] is True
    assert revision(client) == rev
    assert len(plan(client)["guests"]) == len(before["guests"])
    assert plan(client)["assignments"] == before["assignments"]
    assert upload(client, owner, guest, image_bytes("blue")).status_code == 200
    base = f"/api/planning/guests/{guest['id']}"
    assert len(client.get(base + "/documents").json()["documents"]) == 2
    content = client.get(base + f"/documents/{doc['id']}/image")
    assert content.status_code == 200 and content.headers["content-type"] == "image/jpeg"
    assert content.headers["cache-control"] == "no-store"
    assert not Image.open(io.BytesIO(content.content)).getexif()
    pdf = client.get(base + "/documents.pdf?download=true")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
    assert pdf.headers["content-disposition"].startswith("attachment")
    assert b"/Count 2" in pdf.content
    assert "guest_documents" not in client.get("/api/planning").text
    with SessionLocal() as db:
        actions = list(db.scalars(select(Audit.action)))
        assert actions.count("guest_document.uploaded") == 2
        assert "guest_document.pdf_downloaded" in actions


def test_document_role_boundaries_and_foreign_guest(client, owner):
    guest = family(client, owner)[0]
    other = family(client, owner, label="Synthetic Other")[0]
    doc = upload(client, owner, guest).json()["document"]
    base = f"/api/planning/guests/{guest['id']}"
    paths = [base + "/documents", base + "/documents.pdf", base + f"/documents/{doc['id']}/image"]
    signed_out = TestClient(app)
    for path in paths:
        assert signed_out.get(path).status_code == 401
    assert client.get(f"/api/planning/guests/{other['id']}/documents/{doc['id']}/image").status_code == 404
    for role, side in [("family", "bride"), ("family", "groom"), ("reception", None), ("editor", None)]:
        username = f"synthetic.{role}.{side or 'all'}"
        response = client.post("/api/users", headers=headers(owner), json={"username": username,
            "display_name": "Synthetic Viewer", "password": PASSWORD, "role": role, "side": side})
        assert response.status_code == 201
        viewer = TestClient(app)
        auth = viewer.post("/api/auth/login", json={"username": username, "password": PASSWORD}).json()
        for path in paths:
            assert viewer.get(path).status_code == (403 if role == "family" else 200)
        result = upload(viewer, auth, guest, image_bytes("green"), rev=revision(client))
        assert result.status_code == (200 if role == "editor" else 403)
        if role in {"family", "reception"}:
            assert viewer.get("/api/planning/billing").status_code == 403


def test_invalid_stale_and_cross_site_documents(client, owner):
    guest = family(client, owner)[0]
    assert upload(client, owner, guest, b"<svg><script>bad()</script></svg>").status_code == 415
    assert upload(client, owner, guest, b"%PDF-1.7 executable content").status_code == 415
    assert upload(client, owner, guest, b"x" * (5 * 1024 * 1024 + 1)).status_code == 413
    assert upload(client, owner, guest, rev=revision(client) - 1).status_code in {409, 422}
    assert client.post(f"/api/planning/guests/{guest['id']}/documents", files={"file": ("a.png", image_bytes())}, data={"revision": revision(client)}).status_code == 403
    denied = client.post(f"/api/planning/guests/{guest['id']}/documents", files={"file": ("a.png", image_bytes())},
        data={"revision": revision(client)}, headers={**headers(owner), "Origin": "https://example.invalid"})
    assert denied.status_code == 403
    assert upload(client, owner, {"id": str(uuid.uuid4())}).status_code == 404
    with SessionLocal() as db:
        assert db.scalar(select(GuestDocument.id)) is None
