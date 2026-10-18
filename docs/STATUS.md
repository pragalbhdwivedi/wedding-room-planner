# Implementation status

Updated 19 October 2026, Asia/Kolkata.

| Area | State | Evidence / limit |
| --- | --- | --- |
| Requirements and decisions | Recorded | Latest owner rules and backup deferral documented |
| Dedicated Docker host | Prepared and checked | INFRASTRUCTURE.md; private local/Proxmox handovers match |
| Docker application | Built and running as a private preview | Web/API/heartbeat worker/PostgreSQL healthy; one-off migration completed |
| Authentication and access | Implemented and synthetically verified | Protected single-owner setup, Argon2id passwords, hashed sessions, CSRF, throttling and owner-only viewer administration |
| Structural inventory | Implemented and verified | 44 Wyndham rooms (20 Superior/24 Premium), six second-hotel placeholders, 12 separate staff beds |
| Family reservations | Partially represented | Four-room holdback shown; actual Premium-room selection and allocation blocking remain next-stage work |
| UI | Implemented and browser checked | Setup/login, inventory/filter/details, users/access; laptop and phone viewport checks |
| Guest entry, topology editing, assignment | Planned | No guest entry, drag/drop, locks, swaps, undo or solver yet |
| Attendance and cost calculation | Planned | Owner sees rate baseline only; no bill or attendance calculation |
| Import/export and live views | Planned | No integration evidence |
| Worker | Heartbeat only | Not a solver or job-processing implementation |
| Automated verification | Passed for foundation code | 16 PostgreSQL integration checks on dedicated VM; GitHub Docker checks passed; see verification receipt |
| Persistence | Verified within foundation scope | Controlled marker and inventory survived database-container replacement |
| LAN preview / HTTPS | LAN implementation under verification | Explicit private-address binding and LAN origin policy added under D29; trusted HTTPS remains pending |
| Backups / restore | Owner-deferred | No scheduled backup or recovery test claimed |
| Real owner setup / acceptance | Pending | Owner chooses credentials privately; no real user or guest records entered during verification |

## Foundation verification record

Application code and deployed image tags: `0f826038da2248c4044dc2178bc743f77e68fafb`. This status update changes documentation only. See [the verification receipt](verification/FOUNDATION.md) for exact revisions, image IDs, checks and limits.

The initial test-container import-path failure was fixed, then the application was verified. A phone access-table overflow found during browser review was corrected and rechecked. Tests and browser fixtures used a separate temporary PostgreSQL instance with synthetic accounts. That test environment was removed after review. The real database still requires owner setup.

## Next stages

Owner-selected family reservations and topology, private guest/family entry, shared assignment rules and manual moves, automatic proposals, dated attendance/costs, Excel import/export and live scoped views. Confirm unresolved physical/cost policies before implementing affected behavior; see OPEN_ITEMS.md.
