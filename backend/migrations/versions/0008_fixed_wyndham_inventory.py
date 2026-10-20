"""Restore and lock the physical Wyndham room numbers and categories."""
import json
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0008_fixed_wyndham_inventory"
down_revision = "0007_family_room_type"
branch_labels = None
depends_on = None

SUPERIOR = {1: [102, 104, 202, 204], 2: [206, 208], 3: [110, 112, 210, 212],
            4: [115, 117, 215, 217], 5: [219, 221], 6: [123, 125, 223, 225]}
PREMIUM = {1: [101, 103, 201, 203], 2: [105, 107, 205, 207], 3: [109, 111, 209, 211],
           4: [114, 116, 214, 216], 5: [118, 120, 218, 220], 6: [122, 124, 222, 224]}


def _source_rooms():
    return {f"w-{number}": (str(number), category, block, 0 if number < 200 else 1,
                            "twin" if number in (114, 115, 116, 117) else "king", capacity)
            for category, blocks, capacity in (("superior", SUPERIOR, 3), ("premium", PREMIUM, 4))
            for block, numbers in blocks.items() for number in numbers}


def upgrade():
    bind = op.get_bind()
    rows = bind.execute(sa.text("""SELECT id, number, category, block, floor, bed_type, adult_capacity
                                   FROM rooms WHERE hotel_id = 'wyndham' ORDER BY id FOR UPDATE""")).mappings().all()
    source = _source_rooms()
    if len(rows) != 44 or set(source) != {r["id"] for r in rows}:
        raise RuntimeError("Wyndham inventory differs from the 44 source room identities; inspect before locking it.")
    drift = [(r["id"], tuple(r[k] for k in ("number", "category", "block", "floor", "bed_type", "adult_capacity")), source[r["id"]])
             for r in rows if tuple(r[k] for k in ("number", "category", "block", "floor", "bed_type", "adult_capacity")) != source[r["id"]]]
    # The live preflight established one historical UI error. Any other drift needs an explicit review.
    if drift and drift != [("w-101", ("101", "superior", 1, 0, "king", 3), source["w-101"])]:
        raise RuntimeError("Wyndham inventory has an unreviewed number/type change; inspect before locking it.")
    if drift:
        incompatible = bind.execute(sa.text("""SELECT count(*) FROM assignments a
            JOIN guests g ON g.id = a.guest_id JOIN families f ON f.id = g.family_id
            WHERE a.resource_id = 'w-101' AND f.required_room_type = 'superior'""")).scalar_one()
        if incompatible:
            raise RuntimeError("Room 101 has Superior-required guests; review their placements before restoring Premium.")
        bind.execute(sa.text("UPDATE rooms SET category='premium', adult_capacity=4 WHERE id='w-101'"))
        next_revision = bind.execute(sa.text("UPDATE plan_state SET revision=revision+1 WHERE id=1 RETURNING revision")).scalar_one()
        bind.execute(sa.text("""INSERT INTO change_history (id, actor_id, action, entity_id, details, created_at)
             VALUES (:id, NULL, 'room.inventory_restored', :entity, CAST(:details AS jsonb), now())"""),
             {"id": uuid.uuid4(), "entity": str(next_revision),
              "details": json.dumps({"resource_id": "w-101", "number": "101", "from": "superior", "to": "premium", "source": "hotel_room_layout"})})
    op.execute("""CREATE FUNCTION lock_wyndham_inventory() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
        IF TG_OP = 'INSERT' THEN
          IF NEW.hotel_id = 'wyndham' THEN RAISE EXCEPTION 'Wyndham room inventory is fixed by the hotel layout'; END IF;
          RETURN NEW;
        END IF;
        IF OLD.hotel_id = 'wyndham' THEN
          IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Wyndham room inventory is fixed by the hotel layout'; END IF;
          IF (NEW.hotel_id, NEW.number, NEW.category, NEW.block, NEW.floor, NEW.bed_type, NEW.adult_capacity)
             IS DISTINCT FROM (OLD.hotel_id, OLD.number, OLD.category, OLD.block, OLD.floor, OLD.bed_type, OLD.adult_capacity)
          THEN RAISE EXCEPTION 'Wyndham room inventory is fixed by the hotel layout'; END IF;
        END IF;
        RETURN NEW;
      END; $$""")
    op.execute("CREATE TRIGGER lock_wyndham_inventory BEFORE INSERT OR UPDATE OR DELETE ON rooms FOR EACH ROW EXECUTE FUNCTION lock_wyndham_inventory()")


def downgrade():
    op.execute("DROP TRIGGER lock_wyndham_inventory ON rooms")
    op.execute("DROP FUNCTION lock_wyndham_inventory()")
