"""Private planning, scoped guests, revision-safe changes and estimates."""
from alembic import op
import json
from pathlib import Path

revision = "0002_planning"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None

TABLES = ["plan_state", "families", "guests", "planning_resources", "assignments", "room_locks", "guest_links", "room_connections", "planning_rules", "pending_changes", "plan_changes", "allocation_runs", "meal_attendance", "billing_settings", "hotel_charge_days", "bill_snapshots", "guest_presence", "function_events", "event_attendance"]


def upgrade():
    # Frozen SQL deliberately has no dependency on future ORM model changes.
    statements=json.loads((Path(__file__).resolve().parent.parent/'frozen_0002.json').read_text())
    for statement in statements:op.execute(statement)
    op.create_check_constraint("family_side", "families", "side IN ('bride','groom')")
    op.create_check_constraint("guest_age", "guests", "age IS NULL OR age BETWEEN 0 AND 120")
    op.create_check_constraint("guest_category", "guests", "category IN ('guest','driver','staff','vendor')")
    op.create_check_constraint("guest_arrival", "guests", "arrival IS NULL OR arrival IN ('2026-11-24','2026-11-25')")
    op.create_check_constraint("resource_kind", "planning_resources", "(room_id IS NULL) <> (staff_bed_id IS NULL)")
    op.create_index("resource_room_unique", "planning_resources", ["room_id"], unique=True)
    op.create_index("resource_bed_unique", "planning_resources", ["staff_bed_id"], unique=True)
    op.create_check_constraint("assignment_night", "assignments", "night IN ('2026-11-24','2026-11-25')")
    op.create_check_constraint("lock_night", "room_locks", "night IN ('2026-11-24','2026-11-25')")
    op.create_check_constraint("link_pair", "guest_links", "a <> b")
    op.create_unique_constraint("link_unique", "guest_links", ["a", "b", "kind"])
    op.create_check_constraint("link_kind", "guest_links", "kind IN ('may_share','must_share','cannot_share','nearby','same_building')")
    op.create_check_constraint("link_severity", "guest_links", "severity IN ('hard','warning')")
    op.create_check_constraint("connection_kind", "room_connections", "a <> b AND kind IN ('neighbour','opposite')")
    op.create_check_constraint("meal_day", "meal_attendance", "day BETWEEN '2026-11-24' AND '2026-11-26'")
    op.create_check_constraint("meal_kind", "meal_attendance", "meal IN ('breakfast','lunch','dinner')")
    op.create_check_constraint("meal_location", "meal_attendance", "location IN ('wyndham','second','external')")
    op.create_check_constraint("meal_inclusion", "meal_attendance", "inclusion IN ('included','chargeable','unconfirmed')")
    op.create_check_constraint("hotel_charge_day", "hotel_charge_days", "day BETWEEN '2026-11-24' AND '2026-11-26'")
    op.create_check_constraint("function_day", "function_events", "day BETWEEN '2026-11-24' AND '2026-11-26'")
    op.create_check_constraint("function_side", "function_events", "side IS NULL OR side IN ('bride','groom')")
    op.create_check_constraint("presence_order", "guest_presence", "arrived_at IS NULL OR departed_at IS NULL OR departed_at >= arrived_at")
    op.execute("INSERT INTO plan_state(id,revision,redo) VALUES (1,1,'[]'::jsonb)")
    op.execute("INSERT INTO billing_settings(id,guest_meals,second_extra_paise) VALUES (1,'{}'::jsonb,NULL)")
    op.execute("""INSERT INTO planning_resources(id,room_id,reserved,near_restaurant,x,y)
      SELECT id,id,false,false,
        CASE WHEN hotel_id='wyndham' THEN (block-1)*620 + ((row_number() OVER (PARTITION BY hotel_id,block,floor ORDER BY number)-1) % 2)*250 ELSE 3900 END,
        CASE WHEN hotel_id='wyndham' THEN floor*560 + floor((row_number() OVER (PARTITION BY hotel_id,block,floor ORDER BY number)-1)/2.0)*250
        ELSE floor*900 + (row_number() OVER (PARTITION BY hotel_id,floor ORDER BY id)-1)*250 END
      FROM rooms""")
    op.execute("INSERT INTO planning_resources(id,staff_bed_id,reserved,near_restaurant,x,y) SELECT 'bed-'||id,id,false,false,4500+((id-1)%3)*250,((id-1)/3)*250 FROM staff_beds")
    op.execute("REVOKE UPDATE, DELETE ON plan_changes, bill_snapshots FROM planner_app")


def downgrade():
    for name in reversed(TABLES):
        op.drop_table(name)
