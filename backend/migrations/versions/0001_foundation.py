"""Foundation identities, sessions, structural inventory, and owner invariants."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False, unique=True),
        sa.Column("display_name", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("side", sa.String(8)), sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('owner','family','reception')", name="user_role"),
        sa.CheckConstraint("(role = 'family' AND side IS NOT NULL AND side IN ('bride','groom')) OR (role <> 'family' AND side IS NULL)", name="user_scope"),
        sa.CheckConstraint("role <> 'owner' OR active", name="owner_active"))
    op.create_index("one_owner", "users", ["role"], unique=True, postgresql_where=sa.text("role = 'owner'"))
    op.create_table("sessions", sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])
    op.create_table("login_throttle", sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("change_history", sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(64), nullable=False), sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("details", pg.JSONB(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("hotels", sa.Column("id", sa.String(24), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False), sa.Column("kind", sa.String(16), nullable=False))
    op.create_table("rooms", sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("hotel_id", sa.String(24), sa.ForeignKey("hotels.id"), nullable=False),
        sa.Column("number", sa.String(16)), sa.Column("category", sa.String(16), nullable=False),
        sa.Column("block", sa.Integer()), sa.Column("floor", sa.Integer()),
        sa.Column("bed_type", sa.String(16), nullable=False), sa.Column("adult_capacity", sa.Integer(), nullable=False))
    op.create_index("ix_rooms_hotel_id", "rooms", ["hotel_id"])
    op.create_index("room_number_per_hotel", "rooms", ["hotel_id", "number"], unique=True)
    op.create_table("staff_beds", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hotel_id", sa.String(24), sa.ForeignKey("hotels.id"), nullable=False))
    op.create_table("event_policy", sa.Column("id", sa.Integer(), primary_key=True),
        *[sa.Column(n, sa.Integer(), nullable=False) for n in ["family_reserve", "wyndham_allowance", "wyndham_excess_paise", "staff_meal_paise", "second_hotel_day_paise", "second_hotel_included"]])
    op.create_table("worker_heartbeat", sa.Column("id", sa.String(24), primary_key=True), sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False))
    op.execute("""CREATE FUNCTION protect_owner() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF OLD.role = 'owner' THEN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'The designated owner cannot be removed'; END IF;
          IF NEW.role <> 'owner' OR NOT NEW.active THEN RAISE EXCEPTION 'The designated owner must remain active'; END IF;
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        RETURN NEW;
      END; $$""")
    op.execute("CREATE TRIGGER protect_owner_record BEFORE UPDATE OR DELETE ON users FOR EACH ROW EXECUTE FUNCTION protect_owner()")
    op.execute("REVOKE UPDATE, DELETE ON change_history FROM planner_app")
    hotels = sa.table("hotels", sa.column("id"), sa.column("name"), sa.column("kind"))
    op.bulk_insert(hotels, [{"id": "wyndham", "name": "Wyndham Garden", "kind": "guest"},
        {"id": "second", "name": "Second hotel", "kind": "guest"}, {"id": "staff", "name": "Staff dormitory", "kind": "staff"}])
    roomtable = sa.table("rooms", *[sa.column(n) for n in ["id", "hotel_id", "number", "category", "block", "floor", "bed_type", "adult_capacity"]])
    # Derived structural inventory only; no people or assignments.
    superior = {1: [102,104,202,204], 2: [206,208], 3: [110,112,210,212], 4: [115,117,215,217], 5: [219,221], 6: [123,125,223,225]}
    premium = {1: [101,103,201,203], 2: [105,107,205,207], 3: [109,111,209,211], 4: [114,116,214,216], 5: [118,120,218,220], 6: [122,124,222,224]}
    rows = []
    for category, blocks, capacity in [("superior", superior, 3), ("premium", premium, 4)]:
        for block, numbers in blocks.items():
            for number in numbers:
                rows.append({"id": f"w-{number}", "hotel_id": "wyndham", "number": str(number), "category": category,
                    "block": block, "floor": 0 if number < 200 else 1,
                    "bed_type": "twin" if number in [114,115,116,117] else "king", "adult_capacity": capacity})
    for floor in [0,1]:
        for index in range(1,4):
            rows.append({"id": f"second-{floor}-{index}", "hotel_id": "second", "number": None, "category": "pending",
                "block": None, "floor": floor, "bed_type": "pending", "adult_capacity": 4})
    op.bulk_insert(roomtable, rows)
    op.bulk_insert(sa.table("staff_beds", sa.column("id"), sa.column("hotel_id")), [{"id": i, "hotel_id": "staff"} for i in range(1,13)])
    op.bulk_insert(sa.table("event_policy", *[sa.column(n) for n in ["id", "family_reserve", "wyndham_allowance", "wyndham_excess_paise", "staff_meal_paise", "second_hotel_day_paise", "second_hotel_included"]]),
        [{"id": 1, "family_reserve": 4, "wyndham_allowance": 128, "wyndham_excess_paise": 500000,
          "staff_meal_paise": 15000, "second_hotel_day_paise": 1800000, "second_hotel_included": 12}])


def downgrade():
    for name in ["worker_heartbeat", "event_policy", "staff_beds", "rooms", "hotels", "change_history", "login_throttle", "sessions", "users"]:
        op.drop_table(name)
    op.execute("DROP FUNCTION protect_owner()")
