# Delivery plan

Status: phases 1–6 are implemented, technically verified and deployed as the private LAN preview. The owner has completed their login setup. Core planning deployment, exact-revision checks and browser evidence are recorded in STATUS.md; owner acceptance remains separate. Phase 7 is partial (LAN preview and persistent private database; trusted HTTPS and owner-deferred backups remain open).

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

Foundation files include frontend/backend source, Dockerfiles, actual Compose configurations, lockfiles, a schema/inventory migration, synthetic verification fixtures, CI and operator instructions. No real guest seed data is included.
