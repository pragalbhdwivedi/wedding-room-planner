from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.config import settings
from app.main import app

if settings().mode != "test" or settings().database_host != "testdb":
    raise RuntimeError("Tests are permitted only against the isolated testdb service")
migration_url = settings().database_url().set(username="planner_migrate", password=Path("/run/secrets/db_migration_password").read_text().strip())
admin = create_engine(migration_url)


@pytest.fixture(autouse=True)
def reset_identities():
    with admin.begin() as db:
        db.execute(text("TRUNCATE sessions, change_history, login_throttle, users CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def setup_key():
    return Path(settings().bootstrap_token_file).read_text().strip()


@pytest.fixture
def owner(client, setup_key):
    response = client.post("/api/setup", json={"username": "synthetic.owner", "display_name": "Synthetic Owner", "password": "Synthetic test passphrase 2026!"}, headers={"X-Bootstrap-Token": setup_key})
    assert response.status_code == 201
    return response.json()
