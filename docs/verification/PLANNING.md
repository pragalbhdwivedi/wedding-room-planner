# Planning verification

This record covers the core planning implementation on 19 October 2026. Final source/CI/deployment binding is recorded below. Owner acceptance remains separate.

## Automated checks

The dedicated VM builds frontend/backend/test images inside Docker. A separately named Compose project uses temporary PostgreSQL storage, synthetic identities and no database host port. Tests refuse to run against the live database host/mode.

The current 37 checks cover authentication/inventory; stable placeholder completion; competing writes; owner-only edits and viewer scope across API/Excel; age/capacity/bedding boundaries; family reservations; staff separation; second-hotel eligibility; warning-bound previews; locks/swap/undo/redo; typed rules/verified proximity; worker lease recovery, revision staleness and shared validation; exact paise calculations; append-only snapshots/history; safe Excel preview/re-import; migration downgrade/upgrade preserving synthetic owner/session records; revision-only events/session expiry; actual arrivals/functions and duplicate meal-location rejection.

The suite passed on the dedicated VM and in the final GitHub check run. One upstream Starlette test-client deprecation warning remains; it is not a failed assertion.

## Browser checks

The preview database and accounts are synthetic and separate from the real owner database. Checks include laptop/phone layouts, guest/non-resident form entry, reviewed tap and mouse drag placement, disabled apply until warning acknowledgements, worker proposals, attendance and role-scoped views. A non-interactive React Flow wrapper was found and corrected by registering node clicks explicitly. A stable selection area and a pointer movement threshold preserve both first-drag review and click/tap behavior.

## Release limits

No real guest data or original attachments belong in this repository or CI artifacts. All billing remains an estimate; missing meal/extra-person rates and unsettled second-hotel billable days stay visible. Larger child arrangements remain unresolved. HTTPS, backups/recovery and owner event-use acceptance remain separate operational items.

## Final source and deployment binding

- Final application head: `0a92f0bbd45db1c3daa0b0c509bc2d2ad8ba04b0` (PR #4, merged as `e4e730a4429a042d6e3e5fef335cb687ae1da2c3`).
- [GitHub Actions run 39167830399](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39167830399): success, including Docker builds, clean 0001-to-0002 migration and all 37 tests.
- VM suite: 37 passed in 39.85 seconds on matching backend/test source; later changes affect frontend pointer handling only. Final frontend compiled and built inside Docker; the final GitHub run tested the full committed tree. The backend candidate's 70 release files matched normalized Git content; final application images were built from a Git archive of the final source head.
- Browser: Edge, laptop 1440x900 and phone 390x844. Mouse drag opened exact guest/night/from/to review on its first attempt after the correction. Phone family selection switched to the room panel; mandatory warning checkboxes blocked apply until acknowledged; saved counts updated. Phone document/client width both measured 375px, with no page overflow. Viewport override was reset after testing.
- Worker: a synthetic 15-person example returned an optimal 30 person-night proposal. Owner reviewed exact moves/warnings and applied it; both nights then showed 15 assigned, zero unassigned, with staff in dorm beds. Optimal refers to the bounded model, not unrestricted hotel policy.
- Guest/function forms: non-resident guest entry preserved the accommodation count; function creation and expected/actual attendance saved independently. Reception UI displayed operational synthetic contacts and exposed no editing, user-management or billing navigation. API/Excel tests enforce the actual authorization boundaries.
- Deployment: 18 October 2026 21:29 UTC. Web/API/worker images use the final application head above, migration is `0002_planning`, all four services healthy. Before/after private fingerprints confirmed unchanged existing user credentials, sessions and secrets; the same PostgreSQL volume remains mounted. Setup reports false. No real password or personal records were printed or published.
- LAN: real page and health are reachable from the owner PC; unauthenticated inventory/planning/billing/export requests return 401. API and database remain unpublished. VM configuration retained; local non-secret handover and Proxmox Notes were read back and matched.
- Temporary synthetic preview/database and its owned SSH forward were removed after verification. Original real data and owner login were never replaced with fixtures.

No backup, trusted HTTPS, hotel contract confirmation, password recovery or owner acceptance is claimed by these receipts.
