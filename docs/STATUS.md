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
| Automated verification | Candidate passed | 37 isolated PostgreSQL checks passed; final source binding and CI tracked in verification/PLANNING.md |
| Browser verification | In progress | Synthetic isolated preview; canvas click handling corrected after inspection; final desktop/phone record pending |
| Current real deployment | Foundation until planning rollout | Existing owner login and original private database stay in place during verification |
| HTTPS / backup / acceptance | Pending or deferred | Trusted HTTPS remains open; backups owner-deferred; no owner acceptance for event use yet |

The previous deployed foundation image was `7fee89fde677d594b2183c3e2cf6ec657467bf77`, schema `0001_foundation`; historical evidence is retained in verification/FOUNDATION.md and verification/LAN.md. The planning upgrade adds schema `0002_planning`. It does not rerun setup or replace credentials.

Read [Planning guide](PLANNING_GUIDE.md) for the workflow and [Open items](OPEN_ITEMS.md) for unresolved physical/pricing inputs. A successful technical check does not confirm those hotel policies or owner acceptance.
