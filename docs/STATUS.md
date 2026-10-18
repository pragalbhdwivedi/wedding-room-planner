# Implementation status

Updated 19 October 2026, Asia/Kolkata.

| Area | State | Evidence / limit |
| --- | --- | --- |
| Requirements and decisions | Recorded | Latest owner rules and backup deferral are documented |
| Dedicated Docker host | Prepared and checked | See INFRASTRUCTURE.md; this is separate from application evidence |
| Docker application | Implemented; verification pending | Web/API/worker/database, one-off migration, pinned images and dependency locks |
| Authentication and access | Implemented; verification pending | Protected single-owner bootstrap, password sessions, CSRF, throttling, owner-only viewer management |
| Structural inventory | Implemented; verification pending | 44 Wyndham rooms, six second-hotel placeholders, 12 separate staff beds |
| Family reservations | Partially represented | Four-room holdback shown; actual Premium room selection and allocation blocking are not implemented |
| UI | Implemented; browser verification pending | Login/setup, room inventory/filter/details, users/access, responsive styles |
| Guest entry, topology editing, assignment | Planned | No guest entry, drag/drop, locks, swaps, undo or solver yet |
| Attendance and cost calculation | Planned | Owner sees policy baseline only; no bill or attendance calculation |
| Import/export and live views | Planned | No integration evidence |
| Worker | Heartbeat only | Not a solver or job-processing implementation |
| Automated verification | Pending execution | Isolated PostgreSQL integration checks and Docker CI added |
| Application deployment | Pending | Initial scope is an SSH-forwarded loopback preview; shared HTTPS ingress is not configured |
| Backups / restore | Owner-deferred | No backup schedule or recovery test claimed |
| Owner acceptance | Pending | Technical verification does not constitute acceptance |

## Foundation verification record

Results will be added after the application build, migration, integration checks and browser review. Tests use a separate temporary PostgreSQL instance and synthetic users. The real owner account must remain unconfigured until the owner chooses credentials privately.

## Next stages

After the foundation: owner-selected family reservations and topology, private guest/family entry, shared assignment rules and manual moves, automatic proposals, dated attendance/costs, Excel import/export and live scoped views. Confirm unresolved physical/cost policies before implementing affected behavior; see OPEN_ITEMS.md.
