# Database design

The foundation implements PostgreSQL with SQLAlchemy and Alembic. Migration `0001_foundation` creates users, sessions, login_throttle, change_history, hotels, rooms, staff_beds, event_policy and worker_heartbeat. User role/side checks, one-owner uniqueness/protection and separate migration/runtime privileges are enforced in the database. The broader planning model below remains a design until its migrations and features are introduced.

## Model

| Tables | Main fields and relationships |
| --- | --- |
| users | UUID, username, password_hash, owner/viewer role, enabled, timestamps; exactly one designated owner |
| sessions | User, hashed session token, expiry/revocation, authentication metadata |
| access_scopes | User, bride/groom/operational visibility, allowed fields and export permission; never grants another editor |
| wedding_settings | Event dates/timezone, current revision, sole owner reference |
| hotels | Stable ID, name, guest/staff category, rate-plan link |
| blocks, floors | Property hierarchy, actual floor designation and access notes |
| rooms | Hotel/block/floor, real room number nullable until supplied, category, bed type, adult-counted capacity, reservation status |
| layout_nodes | Room/facility reference, schematic coordinates, size; facility nodes are not assignable rooms |
| room_connections | Room pair, neighbouring/opposite/same-building relationship, provenance/verification state |
| families | Stable group ID, display label, side, declared headcount reconciliation state |
| guests | Family, optional name/contact, supplied age or birth date if provided, age certainty, side, guest/driver/staff/vendor category |
| guest_relationships | Guest pair, couple/guardian/sharing relationship, explicit compatibility and visibility |
| tags, guest_tags | Typed tags and membership, including ground-floor requirement and second-hotel eligibility |
| stays | Guest, arrival/check-in, departure/check-out, attendance-only versus resident status |
| room_assignments | Guest/stay, room or staff bed, occupied interval, bedding, lock, plan/revision |
| staff_beds | Dormitory bed IDs and availability; no fabricated physical location |
| events, meal_services | Local date/time, event/meal identity, property, inclusion/rate link |
| attendance | Person + service/event, planned/actual attendance, count status; unique per person/service |
| allocation_rules | Known rule type, typed validated parameters, scope, mandatory/warning/preference severity, enabled state |
| rule_overrides | Exact assignment change, affected rules/revision, owner confirmation, actor/time/reason |
| rate_plans, rate_items | Property, item, precise paise amount or missing, billing unit, included quantity, effective dates, confirmed/provisional status |
| allocation_runs | Input revision, bounded solver parameters, result status, proposal, diagnostics, acceptance/application state |
| import_batches | Private uploaded source reference, mapping, staged rows, duplicate/error summary, accepted changes |
| jobs | Kind, private input reference, state, attempt, lease, result/error; worker claims atomically |
| change_history | Actor, action, entity, before/after or reversible change reference, source revision, UTC timestamp |
| update_outbox | Committed change notifications; filter per recipient before sending |

Most fields remain ordinary relational columns and foreign keys. JSONB is appropriate for validated rule parameters, layout metadata, solver proposals, and audit differences, not a substitute for the core relational model. Never execute arbitrary rule text as Python/SQL.

## Guest counts and placeholders

The canonical count is the set of guest slots, not family.declared_headcount plus all linked guests. A five-person unnamed family can create five stable unnamed slots; adding names completes those slots. Imports reconcile missing/extra members before applying. Unknown age/identity must remain visible.

## Occupancy and money

Store actual heads, adult-counted occupancy, child-sharing eligibility, extra-bed requests, and billing eligibility as distinct concepts. Calculate applicable policies from the guest's known age at the event. Rules can be versioned; do not overwrite a historical bill by silently changing a live rate.

Use integer paise for amounts, explicit units such as whole-property/day, person/night, or person/meal, and nullable amounts for unpriced items. INR 18,000 for six rooms must not become INR 18,000 per room. Derived totals are traceable to date, guests/services, and rate version. Keep proposed/estimated and actual/confirmed figures distinguishable.

## Integrity and transactions

- Foreign keys preserve room/property, assignment/stay, family/guest, and relationship references.
- A room number is unique within its property when known. Placeholder IDs are not real room numbers.
- A guest cannot have overlapping applied assignments. PostgreSQL range exclusions can enforce this per guest; do not exclude all overlaps per room because rooms have multiple occupants.
- Use half-open intervals [check-in, check-out) so sequential stays can reuse a room. Local billing-night mapping is explicit and separate from timestamps.
- Capacity, reserved inventory, dormitory category, locks, and relationship rules are checked under a transaction with affected records/revision protected against concurrent changes.
- Store a sole-owner invariant in addition to application guards. Migration/bootstrap credentials are separate from normal runtime privileges.
- Moves, swaps, accepted solver proposals, import application, history, and update-outbox changes commit atomically.
- Soft deletion/inactivation preserves referenced historical records where necessary; retention/purge policy requires a separate decision.

## Authorization

Filter permitted rows and fields at the server before serialization, event delivery, or export. Ordinary database application credentials do not make every logged-in viewer a database administrator. Costs and sensitive relationship notes are never included in reception schemas. Side scope must also apply to errors/counts that could reveal another side's private records.

## Indexes and lifecycle

Index foreign keys used in lookups; room/property identifiers; guest side/family; assignment room/time and guest/time; attendance service; audit entity/time; job state/lease; and session token hash/expiry. Add indexes based on actual query plans rather than indexing every field.

Every schema change uses a reviewed migration, including a clean-database upgrade test and an upgrade from the prior schema when relevant. Separate app data, private files, and logs from the disposable image/container filesystem. Backup and isolated restore are required before production use.

## Implemented planning design (schema 0002)

The earlier logical model is a design map. The deployed implementation uses `plan_state` for the transaction revision/history cursor; `families` and stable `guests` slots; `planning_resources` for room/bed flags and schematic positions; and `assignments` keyed by guest plus one of the two event nights. This fixed event does not implement arbitrary date-range stays. `room_locks`, `guest_links`, verified `room_connections`, and typed `planning_rules` feed the same validator used for manual previews, imports, history and solver application.

`pending_changes` hold short-lived owner/revision-bound import or assignment previews. `plan_changes` and `bill_snapshots` are append-only to the runtime role. `allocation_runs` holds the private snapshot, lease/attempt state and reviewable result. `meal_attendance`, `guest_presence`, `function_events` and `event_attendance` distinguish planned meals/functions from actual attendance and actual arrival timestamps. `billing_settings` and explicit `hotel_charge_days` hold missing/provisional price inputs alongside the foundation `event_policy`. Source does not contain real runtime records.

The allocator uses CP-SAT in the separate worker, with whole-family units, hard domain/capacity/compatibility/lock constraints, and bounded preference scoring. Every returned proposal is validated again by the shared rules and accepted through the same revision-safe preview/apply path. SSE emits only a revision and session-expiry signal; entity data is fetched again through scoped endpoints. This release does not implement a transactional event outbox or arbitrary FET rule execution.
