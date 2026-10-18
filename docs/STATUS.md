# Implementation status

Updated 19 October 2026, Asia/Kolkata. Implementation, automated verification, deployment and owner acceptance are separate states.

| Area | State | Evidence / limit |
| --- | --- | --- |
| Dedicated Docker host | Prepared and checked | Dedicated Debian VM, private persistent PostgreSQL, web-only LAN ingress |
| Owner login / viewer administration | Implemented; real owner setup completed | Existing sole owner preserved; family/reception remain viewers |
| Guest/family entry | Implemented | Stable unnamed slots, ages/categories/tags, resident/non-resident selection, private contacts/notes |
| Reservations and topology | Implemented | Four exact Premium reservations, schematic layout editing, confirmed corridor connections and restaurant flags |
| Manual assignments | Implemented | Individual/family drag/drop and tap, previews, compatibility highlights, locks, atomic swaps, assignment undo/redo |
| Automatic allocation | Implemented | Leased worker jobs, bounded CP-SAT proposals, whole-family units, honest unresolved diagnostics, owner-reviewed transactional apply |
| Attendance | Implemented | Planned/actual meals and functions; actual arrival/departure records; duplicate meal-location guard |
| Billing | Implemented estimates | Integer paise, per-night allowance, staff meals, explicit inclusion, provisional second-hotel days, unknown-price list and immutable snapshots |
| Excel and live views | Implemented | Owner guest import preview, stable-ID re-import, scoped multi-sheet exports, revision-only events, reconnect refresh and stale guards |
| Automated verification | Passed | 37 isolated PostgreSQL checks; GitHub Actions run 39167830399 passed for final application head `0a92f0b` |
| Browser verification | Passed within synthetic preview scope | Laptop 1440x900 and phone 390x844; first drag, tap, warning review, reviewed worker apply, guest/function entry and reception contact view; no browser errors captured |
| Current real deployment | Running and healthy | `0a92f0bbd45db1c3daa0b0c509bc2d2ad8ba04b0`, schema `0002_planning`; four healthy services; account/session/secret/volume preservation verified |
| HTTPS / backup / acceptance | Pending or deferred | Trusted HTTPS remains open; backups owner-deferred; no owner acceptance for event use yet |

The previous deployed foundation image was `7fee89fde677d594b2183c3e2cf6ec657467bf77`, schema `0001_foundation`; historical evidence is retained in verification/FOUNDATION.md and verification/LAN.md. The planning upgrade adds schema `0002_planning`. It does not rerun setup or replace credentials.

Read [Planning guide](PLANNING_GUIDE.md) for the workflow and [Open items](OPEN_ITEMS.md) for unresolved physical/pricing inputs. A successful technical check does not confirm those hotel policies or owner acceptance.

## Planning release

PR #4 merged as `e4e730a4429a042d6e3e5fef335cb687ae1da2c3`. The deployed images carry the tested application head `0a92f0bbd45db1c3daa0b0c509bc2d2ad8ba04b0`; the merge and this subsequent evidence update do not change application code. Deployment verified 18 October 2026 21:29 UTC (19 October in Asia/Kolkata). Existing owner credential rows, sessions, private secrets and the database volume were preserved; setup is no longer required.

The real LAN service serves the updated application; unauthenticated inventory, planning, billing and Excel requests return 401. Only web ingress is published. No synthetic test records were inserted into the real database. The separate temporary preview/database was removed after checks. The actual owner workflow has not yet received explicit event-use acceptance.


## Room visibility, provisional allocation and invitation update

Implementation in progress on the next release: all-room initial grid, adult/child-band drafts with pending exact ages, four-room unnamed Premium reserve across both nights, explicit source-hotel tags, accurate applied-job status, private invitation family directory, timed functions and invitation theme. The preceding 40-check working build passed before the invitation changes; final head-bound verification/deployment evidence will replace this work-in-progress note. No real guest data is committed to Git.
