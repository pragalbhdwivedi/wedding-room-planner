# Planning verification

This record covers the core planning implementation on 19 October 2026. Final source/CI/deployment binding is appended after verification; no final deployment is implied by this candidate record.

## Automated checks

The dedicated VM builds frontend/backend/test images inside Docker. A separately named Compose project uses temporary PostgreSQL storage, synthetic identities and no database host port. Tests refuse to run against the live database host/mode.

The current 37 checks cover authentication/inventory; stable placeholder completion; competing writes; owner-only edits and viewer scope across API/Excel; age/capacity/bedding boundaries; family reservations; staff separation; second-hotel eligibility; warning-bound previews; locks/swap/undo/redo; typed rules/verified proximity; worker lease recovery, revision staleness and shared validation; exact paise calculations; append-only snapshots/history; safe Excel preview/re-import; migration downgrade/upgrade preserving synthetic owner/session records; revision-only events/session expiry; actual arrivals/functions and duplicate meal-location rejection.

The suite passed on the implementation candidate. One upstream Starlette test-client deprecation warning remains; it is not a failed assertion. Final checks must be bound to the committed source before rollout.

## Browser checks

The preview database and accounts are synthetic and separate from the real owner database. Checks include laptop/phone layouts, guest/non-resident form entry, reviewed tap and native drag placement, disabled apply until warning acknowledgements, worker proposals, attendance and role-scoped views. A non-interactive React Flow wrapper was found and corrected by registering node clicks explicitly. A stable selection area prevents the drag target grid moving as its source is selected.

## Release limits

No real guest data or original attachments belong in this repository or CI artifacts. All billing remains an estimate; missing meal/extra-person rates and unsettled second-hotel billable days stay visible. Larger child arrangements remain unresolved. HTTPS, backups/recovery and owner event-use acceptance remain separate operational items.
