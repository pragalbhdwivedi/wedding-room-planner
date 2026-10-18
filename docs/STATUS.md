# Implementation status

Updated 19 October 2026, Asia/Kolkata. Implementation, automated verification, deployment and owner acceptance are separate states.

| Area | State | Evidence / limit |
| --- | --- | --- |
| Dedicated Docker host | Prepared and checked | Dedicated Debian VM, private persistent PostgreSQL, web-only LAN ingress |
| Owner login / viewer administration | Implemented; real owner setup completed | Existing sole owner preserved; family/reception remain viewers |
| Guest/family entry | Implemented | Stable unnamed slots and adult/child bands, pending exact-age flags, private contacts/notes and resident selection |
| Reservations and topology | Implemented | All-room initial grid, optional four-room Premium reserve pool or four named reservations, editable schematic layout and confirmed corridor/restaurant flags |
| Manual assignments | Implemented | Individual/family drag/drop and tap, previews, compatibility highlights, locks, atomic swaps, assignment undo/redo |
| Automatic allocation | Implemented | Leased worker jobs, bounded CP-SAT proposals, whole-family units, honest unresolved diagnostics, owner-reviewed transactional apply |
| Attendance | Implemented | Private invitation family directory, dated/timed functions and attendance; separate arrivals/meals; no duplicate accommodation headcounts |
| Billing | Implemented estimates | Integer paise, per-night allowance, staff meals, explicit inclusion, provisional second-hotel days, unknown-price list and immutable snapshots |
| Excel and live views | Implemented | Owner guest import preview, stable-ID re-import, scoped multi-sheet exports, revision-only events, reconnect refresh and stale guards |
| Automated verification | Passed | 43 isolated PostgreSQL checks; GitHub Actions run 39171557577 passed for final application head `9ad7ff9` |
| Browser verification | Passed within synthetic preview scope | Laptop 1440x900 and phone 390x844; first drag, tap, warning review, reviewed worker apply, guest/function entry and reception contact view; no browser errors captured |
| Current real deployment | Running and healthy | `9ad7ff918897255761c76d5e0340b91f36713749`, schema `0004_wedding_details`; four healthy services; account/session/secret/volume preservation verified |
| HTTPS / backup / acceptance | Pending or deferred | Trusted HTTPS remains open; backups owner-deferred; no owner acceptance for event use yet |

The previous deployed foundation image was `7fee89fde677d594b2183c3e2cf6ec657467bf77`, schema `0001_foundation`; historical evidence is retained in verification/FOUNDATION.md and verification/LAN.md. The planning upgrade adds schema `0002_planning`. It does not rerun setup or replace credentials.

Read [Planning guide](PLANNING_GUIDE.md) for the workflow and [Open items](OPEN_ITEMS.md) for unresolved physical/pricing inputs. A successful technical check does not confirm those hotel policies or owner acceptance.

## Planning release

PR #4 merged as `e4e730a4429a042d6e3e5fef335cb687ae1da2c3`. The deployed images carry the tested application head `0a92f0bbd45db1c3daa0b0c509bc2d2ad8ba04b0`; the merge and this subsequent evidence update do not change application code. Deployment verified 18 October 2026 21:29 UTC (19 October in Asia/Kolkata). Existing owner credential rows, sessions, private secrets and the database volume were preserved; setup is no longer required.

The real LAN service serves the updated application; unauthenticated inventory, planning, billing and Excel requests return 401. Only web ingress is published. No synthetic test records were inserted into the real database. The separate temporary preview/database was removed after checks. The actual owner workflow has not yet received explicit event-use acceptance.


## Room visibility, provisional allocation and invitation update

The all-room grid, provisional adult/child-band drafts, four-room unnamed Premium reserve, explicit source-hotel tags, applied-job status, private invitation directory, timed functions and invitation theme are deployed. Valid Excel imports with omitted/stale cached dimensions are supported with streaming bounds.

PR #5 application head `0e841ce5b9b24f49f29b6736a1c7b3c1b967094d` passed 42 checks in [run 39170820221](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39170820221), merged as `c9e3e983ca1072ef4fd743b1ad14ae44326e8a12`. PR #6 import follow-up head `00294cad75f273bdd82ec0958c67e62e4e96ef1c` passed 43 checks in [run 39171190235](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39171190235), merged as `cb4eb4db99c0467f209ee35a78a07b464c7a48ae`. Matching Docker images were built from committed Git archives on the dedicated Debian host. Deployment verified 18 October 2026 22:14:45 UTC; schema 0004, four services healthy, credentials/sessions/secrets and the same database volume preserved.

Browser checks verified 44 initial room cards, topology switching, reviewed family drag/tap, provisional age-band placement, invitation directory save and 26 November 00:00 function entry. Phone layouts measured equal document/client widths of 375px. An owner-assisted private roster import, invitation context entry and reviewed allocation were applied and checked in the live service. Real names, ages, room assignments and screenshots remain outside Git. Exact ages, provisional arrivals and blank source headcounts remain flagged for owner review. No hotel policy, final bill, HTTPS/backup completion or owner event-use acceptance is implied.

PR #7 final application head `9ad7ff918897255761c76d5e0340b91f36713749` passed all 43 checks in [run 39171557577](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39171557577), merged as `7b2111690b46a1eacd8a48ea633e1dabcaa25bb6`. Matching images were deployed and verified 18 October 2026 22:19:44 UTC, schema 0004, all four services healthy. Existing credentials, sessions, private secrets, data and the persistent volume were retained. A live owner preview verified family/slot labels and was closed without applying another placement. Both-night assignment totals, mandatory-rule validation, protected reserve quantity, saved invitation context and applied-job state were checked privately after import. Temporary synthetic preview/database and its owned forward were removed.

This evidence-only update does not alter application code. Local and Proxmox handover records retain the verified host inventory; the current deployment section is refreshed without changing VM resources. Public Git contains no real guest data or actual placement exports. The draft still needs owner confirmation of exact ages/accessibility, arrival dates, complete source headcounts and unresolved hotel pricing; no event-use acceptance is claimed.

## Guest detail and Friends update

PR #8 application head `85fb960b982269e186e8512f0fa062f743f45252` passed 49 isolated PostgreSQL checks in [run 39173474122](https://github.com/pragalbhdwivedi/wedding-room-planner/actions/runs/39173474122), merged as `11f657f265d6ac6a6b07b29f978c37e23f936c21`, and was deployed to the dedicated planner VM on 18 October 2026 at 22:46 UTC. Schema 0005 and all four services are healthy. Existing owner credentials, sessions, secrets, guest identities, planning data and the database volume were preserved across the deployment.

The release adds tickable guest tags, a male/female/unspecified choice, and adult Friends sharing by selected gender within each bride/groom side. Age or tag edits that invalidate an upstairs placement now prepare a reviewed ground-floor move, preserving the draft until the owner applies the guest edit and room changes together. Room locks and the four-room Premium reserve remain enforced. An isolated browser preview verified tag selection, Friends entry, review cancellation, and atomic age-50 correction. A live owner edit then verified the age-50 correction and both-night ground-floor placement without changing the guest count, reserve quantity, or mandatory-rule validation. Private guest names, ages, assignments and screenshots remain outside Git. The remaining exact ages, provisional arrivals, headcount checks and unsettled rates still need owner review; no final event-use acceptance is claimed.
