# Acceptance checks

Status: acceptance plan; actual results are recorded separately in STATUS.md. Use synthetic records only. Bind evidence to the exact source revision and environment; automated results, deployment, and owner acceptance are distinct. The automated suite now includes guest workflows, scope/privacy, allocation jobs, exact money, import/export and additive migration preservation. Browser checks supplement these; neither replaces owner acceptance.

| ID | Scenario | Expected result |
| --- | --- | --- |
| A01 | Import the structural inventory | Exactly 44 Wyndham rooms: 20 Superior/24 Premium, 20 ground/24 first, 40 king/4 twin; six second-hotel rooms and 12 dorm beds remain separate. |
| A02 | Reserve four Premium rooms | General Wyndham availability becomes 40 rooms; those four are excluded from general solver/manual placement and can later hold family. Pending room numbers are not guessed. |
| A03 | Family headcount five, names entered later | Five guest slots throughout; named member completion does not increase total to ten. |
| A03a | Add and delete a family member | Exact age updates the adult/child display; an added member in an assigned family receives a reviewed placement when valid, or a clear unassigned warning. Deleting an existing member requires review, removes their assignments/attendance/links and resets assignment undo/redo. A locked room or deleting the last slot is rejected. |
| A04 | Ages 10 and 11 | Age 10 receives child treatment; age 11 adult treatment for billing/bedding. Missing exact age with a supplied adult/child band permits a labelled provisional draft; a wholly unknown band remains unresolved. |
| A05 | Couple plus two children <=10 | Allowed in a Superior room with bedding under owner policy. Actual heads show four; adult-counted occupancy stays separate. Premium allocation raises the applicable family-placement issue. |
| A06 | Superior with four adult-counted people | Capacity conflict visible; included bedding does not silently remove the adult-counted limit. Larger young-child arrangements outside known policy are flagged unresolved. |
| A07 | Age 49, age 50, younger guest tagged ground floor | Default age 49 is not automatically forced to ground; age 50 and tagged younger guest require ground. Ground-floor shortage is explained. |
| A07a | Enter age 50 for a provisionally assigned upstairs guest | Owner sees the exact guest detail and proposed ground-floor room changes; cancelling keeps the form; applying saves both atomically. Locked or unavailable rooms are explained without losing entered details. |
| A07b | Tick tags, choose gender, assign Friends | Owner can tick existing/add custom tags and select male, female or unspecified. Automatic allocation combines only same-gender adult Friends on the same side; unspecified genders stay separate, couples/linked children stay together, and mandatory exclusions win. |
| A08 | Neighbouring and opposite-room request | Only verified room relationships fulfil the request; nearby canvas coordinates alone do not. |
| A09 | Second-hotel eligible and ineligible people | Only tagged eligible guests may be auto-assigned there, including on first run. |
| A10 | Guest in dorm / worker in regular room | Both changes blocked, even with override confirmation. Thirteenth dorm occupant produces a capacity conflict. |
| A11 | 128 then 129 chargeable Wyndham residents | Excess cost is INR 0 then INR 5,000 for that night. Family occupants included; other-hotel residents excluded. |
| A12 | Night counts 132 and 130 | INR 30,000 excess total; unused allowance is not carried across nights. |
| A13 | Second-hotel pricing | INR 18,000/day for six rooms/12 guests, not multiplied by six; provisional status visible; extra-person costs unpriced. |
| A14 | Five assigned staff attend two meals | INR 1,500 for those meals. Planned versus actual attendance and breakfast inclusion are not double-counted. |
| A15 | Reception-only guest, no stay | Counts toward selected attendance, not overnight resident occupancy. Missing meal rate stays unpriced. |
| A16 | Lock a room/placement, run solver | Existing locked arrangement remains intact; impossible results report why. |
| A17 | Unrelated adults / family split | Explicit compatibility required; split warning shown; permitted owner override applies only to the exact reviewed change and is audited. |
| A17a | Pick two of four family members from a room | Room card and room details offer a people picker. The owner ticks any subset, sees existing placements, and reviews exactly those people on the selected night. The two unselected members stay where they were; a new family-split warning requires explicit acknowledgement. Room occupants already there remain. Mandatory capacity, lock, sharing and staff rules still block invalid placement. |
| A18 | Same guest assigned to overlapping stays | Rejected. Multiple compatible guests sharing one room remain allowed within rules. |
| A19 | Move/swap fails mid-transaction | No half-move, lost occupant, or mismatched summary/history. |
| A20 | Owner tabs A and B edit stale data | Stale write rejected with current-state recovery; no silent overwrite. Old solver proposals cannot overwrite newer locks/data. |
| A21 | Family viewer uses UI/API/event stream/export | Cannot mutate anything or read another side's restricted data. |
| A22 | Reception directly requests costs/API/export | Cost fields never returned; viewing operational contact/stay details works. |
| A23 | Viewer invokes import/user/rate/override endpoint | Server rejects it regardless of hidden or altered buttons. Only owner changes access. |
| A24 | Import duplicate IDs/names, unknown ages, invalid rows | Preview exposes issues before application; stable-ID re-import does not duplicate people; failures leave current plan intact. |
| A25 | Export user text beginning with formula syntax | Text safely represented; scoped fields only. |
| A26 | Phone and laptop interactions | Owner can assign by touch or drag; viewers have clear read-only layout; labels accompany colours. |
| A27 | Restart/recreate application containers | Database, private files and assignments persist. |
| A28 | Restore protected backups to isolated environment | Usable data restored and checked; evidence excludes secrets/real private data. |
| A29 | Change a rate / missing price | Date and rate provenance remain traceable; missing is not zero; historical/estimate status not silently overwritten. |
| A30 | New image and schema upgrade | Migrations complete before readiness, failure blocks rollout, and rollback/restore path is documented and tested appropriately. |
| A31 | Owner setup without private key / two simultaneous valid attempts | Missing/wrong key rejected; exactly one owner is created. No default credentials. |
| A32 | Viewer password/access reset, suspension and stale access edit | Previous viewer sessions revoked; stale version rejected; owner cannot be demoted or removed. |
| A33 | Forged cross-site request, missing CSRF token, repeated failed login | Origin/CSRF guards reject mutation; database-backed throttling limits attempts across requests. |
| A34 | API database credential used for schema/audit changes | Non-superuser runtime role cannot create schema objects or update/delete audit history. |
| A35 | LAN preview enabled on private VM address | Another LAN machine can load the app and health/setup endpoints; unauthenticated inventory remains blocked, untrusted origins rejected, and database/API ports remain unpublished. Production still rejects insecure settings. |

| A36 | Actual arrivals and function attendance | Arrival/departure timestamps stay separate from planned nights; non-residents can attend functions. Family exports expose only their own side. |
| A37 | One meal at two locations | Reject duplicate planned or actual attendance for the same person/date/meal; an atomic transfer between locations remains possible. |

| A38 | No named family rooms yet | At most 20 of 24 Premium rooms used across the union of both nights; four remain unused. Named reservations still enforce eligibility. |
| A39 | Initial room view | All 44 Wyndham cards visible by scrolling, count shown; topology and filters available on laptop/phone. |
| A40 | Invitation family directory and function times | No duplicate accommodation guests, owner-only writes, family-side scope, source links, midnight date preserved, scoped Excel function details. |
| A41 | HTTPS reverse-proxy sign-in | Public HTTP redirects to the HTTPS sign-in page without a loop; the exact HTTPS origin reaches sign-in validation, a foreign origin remains rejected, a valid sign-in receives a Secure session cookie, and authenticated owner/viewer access retains its existing scopes. Check on the owner's device; a health check alone does not satisfy this. |
| A42 | Room upgrade/downgrade | Owner can switch a Wyndham room between Superior (three adult-counted occupants) and Premium (four) from room details, and both room views and allocation use the new type. A current four-person placement, a named Premium family reservation, or the unnamed four-room reserve blocks an unsafe downgrade. A viewer cannot change it; revision and audit update only on success. |
| A43 | Change room number | Owner can rename a Wyndham or second-hotel room from either room view; assignments and stable room ID remain intact. A duplicate number within the hotel is refused without a revision change; family/reception viewers cannot rename rooms. |

## Owner acceptance

Demonstrate a representative family entry, dated allocation, lock, warning override, solver proposal, cost reconciliation, reception view, phone operation, and export with the owner. Record explicit approval before describing the planner as accepted for event use.
