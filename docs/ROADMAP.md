# Delivery plan

Status: application phases remain planned. Repository documentation and a dedicated Debian Docker host are prepared; see INFRASTRUCTURE.md. Host readiness does not complete phase 1's application/login/database deliverables. Subsequent implementation should be reviewed against REQUIREMENTS.md and ACCEPTANCE.md.

| Phase | Deliverables | Evidence before claiming completion |
| --- | --- | --- |
| 1 - Foundation | Docker builds/Compose, database migrations, owner bootstrap, username/password sessions, users/access page | Clean setup, restart persistence, owner/viewer authorization checks |
| 2 - Inventory and topology | Wyndham inventory/layout, family-room reservations, second hotel, dormitory, phone/laptop navigation | Counts reconcile; physical unknowns marked; owner can select reserved rooms |
| 3 - Guests and manual planning | Families/individuals, placeholder completion, ages/tags, stays, drag/drop/tap assignment, swaps/locks/undo/history | No duplicate counts; atomic moves; child/age/compatibility rules demonstrated |
| 4 - Automatic assignment | Shared constraints, worker jobs, proposals/diagnostics, revision-safe apply | Locks/eligibility/reservations respected; infeasible cases remain explicit |
| 5 - Attendance and costs | Meals/events, dated summaries, precise rates, known subtotal/unpriced items | Exact boundary and reconciliation checks for allowances, ages, staff meals, second hotel |
| 6 - Import/export and live views | Owner import preview, scoped Excel export, server-pushed updates, stale-write detection | Duplicate/re-import, scope leakage, reconnect and competing-session checks |
| 7 - Operational delivery | Selected host, HTTPS, protected storage, scheduled off-host backups, restore, upgrade/rollback notes | Exact deployed image/revision; isolated restore succeeds; phone/laptop workflows checked |
| 8 - Owner acceptance | Owner uses real private workflow and confirms readiness | Explicit acceptance recorded separately from automated tests and deployment |

## Initial implementation deliverables

Expected files include frontend/backend source, Dockerfiles, actual Compose configurations, lockfiles, schema migrations, synthetic seed data, verification code, and operator instructions. These will be added when implemented; this documentation baseline deliberately does not pretend those files are runnable now.
