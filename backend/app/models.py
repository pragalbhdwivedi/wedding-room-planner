import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (
        CheckConstraint("role IN ('owner','family','reception')", name="user_role"),
        CheckConstraint("(role = 'family' AND side IS NOT NULL AND side IN ('bride','groom')) OR (role <> 'family' AND side IS NULL)", name="user_scope"),
        CheckConstraint("role <> 'owner' OR active", name="owner_active"),
        Index("one_owner", "role", unique=True, postgresql_where=text("role = 'owner'")),
    )


class LoginSession(Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LoginThrottle(Base):
    __tablename__ = "login_throttle"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Audit(Base):
    __tablename__ = "change_history"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Hotel(Base):
    __tablename__ = "hotels"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(16))


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotels.id"), index=True)
    number: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str] = mapped_column(String(16))
    block: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bed_type: Mapped[str] = mapped_column(String(16))
    adult_capacity: Mapped[int] = mapped_column(Integer)
    __table_args__ = (Index("room_number_per_hotel", "hotel_id", "number", unique=True),)


class EventPolicy(Base):
    __tablename__ = "event_policy"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    family_reserve: Mapped[int] = mapped_column(Integer)
    wyndham_allowance: Mapped[int] = mapped_column(Integer)
    wyndham_excess_paise: Mapped[int] = mapped_column(Integer)
    staff_meal_paise: Mapped[int] = mapped_column(Integer)
    second_hotel_day_paise: Mapped[int] = mapped_column(Integer)
    second_hotel_included: Mapped[int] = mapped_column(Integer)


class StaffBed(Base):
    __tablename__ = "staff_beds"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hotel_id: Mapped[str] = mapped_column(ForeignKey("hotels.id"))


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeat"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PlanState(Base):
    __tablename__ = "plan_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    cursor: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    redo: Mapped[list] = mapped_column(JSONB, default=list)


class Family(Base):
    __tablename__ = "families"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label: Mapped[str] = mapped_column(String(100))
    side: Mapped[str] = mapped_column(String(8))
    reserved_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    couple_children: Mapped[bool] = mapped_column(Boolean, default=False)


class Guest(Base):
    __tablename__ = "guests"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("families.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_band: Mapped[str] = mapped_column(String(8), default="unknown", server_default="unknown")
    gender: Mapped[str] = mapped_column(String(16), default="unspecified", server_default="unspecified")
    sharing_mode: Mapped[str] = mapped_column(String(8), default="family", server_default="family")
    category: Mapped[str] = mapped_column(String(16), default="guest")
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    arrival: Mapped[object | None] = mapped_column(Date, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")


class Resource(Base):
    __tablename__ = "planning_resources"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    staff_bed_id: Mapped[int | None] = mapped_column(ForeignKey("staff_beds.id"), nullable=True)
    reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    near_restaurant: Mapped[bool] = mapped_column(Boolean, default=False)
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)


class Assignment(Base):
    __tablename__ = "assignments"
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), primary_key=True)
    night: Mapped[object] = mapped_column(Date, primary_key=True)
    resource_id: Mapped[str] = mapped_column(ForeignKey("planning_resources.id"), index=True)


class RoomLock(Base):
    __tablename__ = "room_locks"
    resource_id: Mapped[str] = mapped_column(ForeignKey("planning_resources.id"), primary_key=True)
    night: Mapped[object] = mapped_column(Date, primary_key=True)


class GuestLink(Base):
    __tablename__ = "guest_links"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    a: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), index=True)
    b: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(8), default="hard")


class RoomConnection(Base):
    __tablename__ = "room_connections"
    a: Mapped[str] = mapped_column(ForeignKey("planning_resources.id"), primary_key=True)
    b: Mapped[str] = mapped_column(ForeignKey("planning_resources.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))


class PlanningRule(Base):
    __tablename__ = "planning_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(24))
    severity: Mapped[str] = mapped_column(String(8))
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parameters: Mapped[dict] = mapped_column(JSONB, default=dict)


class PendingChange(Base):
    __tablename__ = "pending_changes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict] = mapped_column(JSONB)
    warnings: Mapped[list] = mapped_column(JSONB, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PlanChange(Base):
    __tablename__ = "plan_changes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    before: Mapped[list] = mapped_column(JSONB)
    after: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AllocationRun(Base):
    __tablename__ = "allocation_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    snapshot: Mapped[dict] = mapped_column(JSONB)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class MealAttendance(Base):
    __tablename__ = "meal_attendance"
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), primary_key=True)
    day: Mapped[object] = mapped_column(Date, primary_key=True)
    meal: Mapped[str] = mapped_column(String(16), primary_key=True)
    location: Mapped[str] = mapped_column(String(16), primary_key=True)
    planned: Mapped[bool] = mapped_column(Boolean, default=True)
    actual: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    inclusion: Mapped[str] = mapped_column(String(16), default="unconfirmed")


class BillingSettings(Base):
    __tablename__ = "billing_settings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guest_meals: Mapped[dict] = mapped_column(JSONB, default=dict)
    second_extra_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)


class HotelChargeDay(Base):
    __tablename__ = "hotel_charge_days"
    day: Mapped[object] = mapped_column(Date, primary_key=True)


class BillSnapshot(Base):
    __tablename__ = "bill_snapshots"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class GuestPresence(Base):
    __tablename__ = "guest_presence"
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), primary_key=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FunctionEvent(Base):
    __tablename__ = "function_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    day: Mapped[object] = mapped_column(Date)
    side: Mapped[str | None] = mapped_column(String(8), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    venue: Mapped[str] = mapped_column(String(150), default="", server_default="")
    source_url: Mapped[str] = mapped_column(String(250), default="", server_default="")


class WeddingDetails(Base):
    __tablename__ = "wedding_details"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)


class EventAttendance(Base):
    __tablename__ = "event_attendance"
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("function_events.id"), primary_key=True)
    guest_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guests.id"), primary_key=True)
    planned: Mapped[bool] = mapped_column(Boolean, default=True)
    actual: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
