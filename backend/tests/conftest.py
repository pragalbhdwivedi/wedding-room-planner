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
        db.execute(text("TRUNCATE families, guests, assignments, room_locks, guest_links, room_connections, planning_rules, hotel_charge_days, meal_attendance, guest_presence, function_events, event_attendance CASCADE"))
        db.execute(text("UPDATE plan_state SET revision=1,cursor=NULL,redo='[]'::jsonb WHERE id=1"))
        db.execute(text("UPDATE planning_resources SET reserved=false,near_restaurant=false"))
        db.execute(text("UPDATE event_policy SET wyndham_allowance=128,wyndham_excess_paise=500000,staff_meal_paise=15000,second_hotel_day_paise=1800000,second_hotel_included=12 WHERE id=1"))
        db.execute(text("UPDATE billing_settings SET guest_meals='{}'::jsonb,second_extra_paise=NULL WHERE id=1"))


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
