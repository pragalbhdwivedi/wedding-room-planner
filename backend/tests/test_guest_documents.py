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
    assert b"/Count 1" in pdf.content
    assert "guest_documents" not in client.get("/api/planning").text
    with SessionLocal() as db:
        actions = list(db.scalars(select(Audit.action)))
        assert actions.count("guest_document.uploaded") == 2
        assert "guest_document.pdf_downloaded" in actions


def test_all_id_images_fit_on_one_page_without_dropping_images():
    from types import SimpleNamespace
    from app.documents_api import build_pdf
    for count in (1, 2, 3, 12):
        rows = [SimpleNamespace(content=image_bytes("blue" if i % 2 else "green")) for i in range(count)]
        pdf = build_pdf(rows)
        assert b"/Count 1" in pdf
        assert b"/Count 2" not in pdf


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


def test_unmatched_collection_preserves_roster_and_match_uses_stable_guest(client, owner):
    guest = family(client, owner)[0]
    before = plan(client)
    def collect():
        return client.post('/api/planning/id-collection', headers=headers(owner),
            data={'revision': revision(client), 'label': 'Synthetic ID awaiting review'},
            files={'file': ('synthetic.png', image_bytes(), 'image/png')})
    result = collect()
    assert result.status_code == 200, result.text
    doc = result.json()['document']
    assert doc['guest_id'] is None
    assert collect().json()['duplicate'] is True
    assert len(client.get('/api/planning/id-collection').json()['documents']) == 1
    assert plan(client)['guests'] == before['guests']
    assert plan(client)['assignments'] == before['assignments']
    body = {'revision': revision(client), 'guest_id': guest['id']}
    matched = client.post(f"/api/planning/id-collection/{doc['id']}/match", headers=headers(owner), json=body)
    assert matched.status_code == 200 and matched.json()['document']['guest_id'] == guest['id']
    assert collect().json()['duplicate'] is True
    assert len(client.get(f"/api/planning/guests/{guest['id']}/documents").json()['documents']) == 1
    assert plan(client)['guests'] == before['guests']
    assert client.post(f"/api/planning/id-collection/{doc['id']}/match", headers=headers(owner),
        json={'revision': revision(client), 'guest_id': guest['id']}).status_code == 409


def test_collection_reception_reads_but_cannot_match_and_families_cannot_read(client, owner):
    guest = family(client, owner)[0]
    result = client.post('/api/planning/id-collection', headers=headers(owner), data={'revision': revision(client)},
        files={'file': ('synthetic.png', image_bytes(), 'image/png')})
    doc = result.json()['document']
    for role, side in [('reception', None), ('family', 'bride')]:
        username = 'synthetic.collection.' + role
        assert client.post('/api/users', headers=headers(owner), json={'username': username, 'display_name': 'Synthetic Viewer',
            'password': PASSWORD, 'role': role, 'side': side}).status_code == 201
        viewer = TestClient(app)
        auth = viewer.post('/api/auth/login', json={'username': username, 'password': PASSWORD}).json()
        for path in ['/api/planning/id-collection', f"/api/planning/id-collection/{doc['id']}/image", f"/api/planning/id-collection/{doc['id']}/document.pdf"]:
            assert viewer.get(path).status_code == (200 if role == 'reception' else 403)
            assert TestClient(app).get(path).status_code == 401
        assert viewer.post('/api/planning/id-collection', headers=headers(auth), data={'revision': revision(client)},
            files={'file': ('synthetic.png', image_bytes(), 'image/png')}).status_code == 403
        assert viewer.post(f"/api/planning/id-collection/{doc['id']}/match", headers=headers(auth),
            json={'revision': revision(client), 'guest_id': guest['id']}).status_code == 403
