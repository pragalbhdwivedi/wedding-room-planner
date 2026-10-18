import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.config import Settings
from app.db import SessionLocal
from app.main import app
from app.models import Audit, LoginSession, LoginThrottle, User, now
from app.security import COOKIE, digest, verify_password

PASSWORD = "Synthetic test passphrase 2026!"


def viewer(client, owner, role="family", side="bride"):
    response = client.post("/api/users", json={"username": "synthetic.viewer", "display_name": "Synthetic Viewer", "password": PASSWORD, "role": role, "side": side}, headers={"X-CSRF-Token": owner["csrf_token"]})
    assert response.status_code == 201
    return response.json()


def login_as_viewer():
    c = TestClient(app)
    response = c.post("/api/auth/login", json={"username": "synthetic.viewer", "password": PASSWORD})
    assert response.status_code == 200
    return c, response.json()


def test_health_and_unconfigured_state(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/setup/status").json() == {"setup_required": True}
    assert client.get("/api/inventory").status_code == 401
    assert client.get("/api/users").status_code == 401


def test_setup_requires_private_key_and_is_single_use(client, setup_key):
    body = {"username": "synthetic.owner", "display_name": "Synthetic Owner", "password": PASSWORD}
    assert client.post("/api/setup", json=body).status_code == 403
    assert client.post("/api/setup", json=body, headers={"X-Bootstrap-Token": setup_key}).status_code == 201
    assert client.post("/api/setup", json={**body,"username":"other.owner"}, headers={"X-Bootstrap-Token": setup_key}).status_code == 409
    assert client.get("/api/setup/status").json() == {"setup_required": False}


def test_concurrent_setup_cannot_create_two_owners(setup_key):
    def create(index):
        with TestClient(app) as c:
            return c.post("/api/setup", json={"username": f"synthetic.owner{index}", "display_name": "Synthetic Owner", "password": PASSWORD}, headers={"X-Bootstrap-Token": setup_key}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, [1,2])) == [201,409]


def test_passwords_and_sessions_are_hashed(client, owner):
    raw = client.cookies.get(COOKIE)
    with SessionLocal() as db:
        user = db.scalar(select(User))
        assert user.password_hash.startswith("$argon2id$") and verify_password(user.password_hash, PASSWORD)
        assert db.get(LoginSession, digest(raw)) is not None
        assert db.get(LoginSession, raw) is None
        assert PASSWORD not in json.dumps([a.details for a in db.scalars(select(Audit))])
    assert "password" not in json.dumps(client.get("/api/users").json()).lower()


def test_cookie_and_csrf_protection(client, setup_key):
    r=client.post("/api/setup", json={"username":"synthetic.owner","display_name":"Synthetic Owner","password":PASSWORD}, headers={"X-Bootstrap-Token":setup_key})
    cookie=r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    body={"username":"synthetic.viewer","display_name":"Synthetic Viewer","password":PASSWORD,"role":"reception","side":None}
    assert client.post("/api/users",json=body).status_code==403
    assert client.post("/api/users",json=body,headers={"X-CSRF-Token":"wrong"}).status_code==403
    assert client.post("/api/users",json=body,headers={"X-CSRF-Token":r.json()["csrf_token"]}).status_code==201


@pytest.mark.parametrize("role,side", [("family","bride"),("family","groom"),("reception",None)])
def test_viewer_is_read_only_and_never_receives_costs(client, owner, role, side):
    viewer(client,owner,role,side)
    c, auth=login_as_viewer()
    result=c.get("/api/inventory")
    assert result.status_code==200 and len(result.json()["rooms"])==50
    assert "cost_policy" not in result.json() and "paise" not in result.text
    assert auth["user"]["role"]==role and auth["user"]["side"]==side
    assert c.get("/api/users").status_code==403
    assert c.post("/api/users",json={"username":"another.viewer","display_name":"Synthetic Viewer","password":PASSWORD,"role":"reception","side":None},headers={"X-CSRF-Token":auth["csrf_token"]}).status_code==403


def test_access_change_revokes_session_and_rejects_stale_update(client, owner):
    v=viewer(client,owner)
    c,_=login_as_viewer()
    body={"version":v["version"],"display_name":"Synthetic Reception","role":"reception","side":None,"active":True}
    headers={"X-CSRF-Token":owner["csrf_token"]}
    response=client.patch('/api/users/'+v['id'],json=body,headers=headers)
    assert response.status_code==200 and response.json()["version"]==2
    assert c.get('/api/auth/me').status_code==401
    assert client.patch('/api/users/'+v['id'],json=body,headers=headers).status_code==409


def test_owner_cannot_be_demoted_or_removed_and_second_owner_rejected(client, owner):
    with SessionLocal() as db:
        db.add(User(username="another.owner",display_name="Synthetic",password_hash="synthetic-not-a-credential",role="owner",side=None,active=True))
        with pytest.raises(IntegrityError):db.commit()
    for sql in ["DELETE FROM users WHERE role='owner'", "UPDATE users SET role='reception' WHERE role='owner'", "UPDATE users SET active=false WHERE role='owner'"]:
        with SessionLocal() as db:
            with pytest.raises(DBAPIError):db.execute(text(sql))
    body={"version":1,"display_name":"Synthetic","role":"reception","side":None,"active":True}
    assert client.patch('/api/users/'+owner['user']['id'],json=body,headers={"X-CSRF-Token":owner["csrf_token"]}).status_code==403


def test_database_roles_and_append_only_audit(owner):
    with SessionLocal() as db:
        assert db.scalar(text("SELECT current_user"))=='planner_app'
        assert db.scalar(text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")) is False
    for sql in ["CREATE TABLE not_allowed (id int)", "DELETE FROM change_history", "UPDATE change_history SET action='changed'"]:
        with SessionLocal() as db:
            with pytest.raises(DBAPIError):db.execute(text(sql))


def test_inventory_reconciles_and_reserved_rooms_not_guessed(client, owner):
    d=client.get('/api/inventory').json();rooms=d['rooms'];w=[r for r in rooms if r['hotel_id']=='wyndham']
    assert len(w)==44 and len([r for r in w if r['category']=='superior'])==20
    assert len([r for r in w if r['floor']==0])==20 and len([r for r in w if r['bed_type']=='twin'])==4
    assert len(d['staff_beds'])==12 and d['family_reserve_pending']==4
    assert all(r['number'] is None for r in rooms if r['hotel_id']=='second')
    assert d['cost_policy']['wyndham_allowance']==128 and d['cost_policy']['staff_meal_paise']==15000
    assert d['allocation_available'] is True and d['guest_entry_available'] is True


def test_login_throttle_survives_requests_and_expires(client, owner):
    for _ in range(5):
        assert client.post('/api/auth/login',json={"username":"synthetic.owner","password":"not the password"}).status_code==401
    assert client.post('/api/auth/login',json={"username":"synthetic.owner","password":PASSWORD}).status_code==429
    with SessionLocal.begin() as db:
        for throttle in db.scalars(select(LoginThrottle)):throttle.started_at=now()-timedelta(minutes=16)
    assert client.post('/api/auth/login',json={"username":"synthetic.owner","password":PASSWORD}).status_code==200


def test_logout_and_expiry(client, owner):
    assert client.post('/api/auth/logout',json={},headers={"X-CSRF-Token":owner['csrf_token']}).status_code==200
    assert client.get('/api/auth/me').status_code==401
    assert client.post('/api/auth/login',json={"username":"synthetic.owner","password":PASSWORD}).status_code==200
    with SessionLocal.begin() as db:
        for session in db.scalars(select(LoginSession)):session.expires_at=now()-timedelta(seconds=1)
    assert client.get('/api/auth/me').status_code==401


def test_untrusted_origin_and_validation_redaction(client, setup_key):
    body={"username":"synthetic.owner","display_name":"Synthetic Owner","password":PASSWORD}
    assert client.post('/api/setup',json=body,headers={"X-Bootstrap-Token":setup_key,"Origin":"https://untrusted.example"}).status_code==403
    response=client.post('/api/setup',json={**body,"password":"SENSITIVE"},headers={"X-Bootstrap-Token":setup_key})
    assert response.status_code==422 and 'SENSITIVE' not in response.text


def test_production_transport_fails_closed():
    with pytest.raises(ValueError):Settings(mode="production",cookie_secure=False,allowed_origins="http://127.0.0.1:8080").validate_transport()
    with pytest.raises(ValueError):Settings(mode="local",cookie_secure=False,allowed_origins="http://untrusted.example").validate_transport()


def test_lan_preview_accepts_only_explicit_private_origins():
    Settings(mode="lan", cookie_secure=False, allowed_origins="http://192.168.1.20:8080,http://127.0.0.1:8769").validate_transport()
    for origin in ["http://8.8.8.8:8080", "http://public.example", "http://0.0.0.0:8080", "http://192.168.1.20:99999", "http://user@192.168.1.20:8080", "http://192.168.1.20/path", "http://192.168.1.20?value=1"]:
        with pytest.raises(ValueError):
            Settings(mode="lan", cookie_secure=False, allowed_origins=origin).validate_transport()
    with pytest.raises(ValueError):
        Settings(mode="production", cookie_secure=False, allowed_origins="http://192.168.1.20:8080").validate_transport()
    with pytest.raises(ValueError):
        Settings(mode="lan", cookie_secure=True, allowed_origins="http://192.168.1.20:8080").validate_transport()
