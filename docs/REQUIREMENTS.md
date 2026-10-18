# Confirmed requirements

Baseline recorded: 19 October 2026, Asia/Kolkata. Source: direct owner answers in the planning discussion. For proposed design choices see ARCHITECTURE.md; for unresolved edges see OPEN_ITEMS.md.

## R01 - Application and devices

Build a private web-based room-allocation application inside Docker. Support phones and laptops, multiple simultaneous signed-in sessions, shared current data, Excel import, and Excel export. The accommodation planner is separate from the public invitation website. Wedding accommodation is for 24-26 November 2026; some guests arrive on the 25th for the main reception.

## R02 - Inventory and reservations

- Wyndham: 44 rooms, consisting of 20 Superior and 24 Premium rooms. Two-person base occupancy.
- Forty rooms are for general guests. Four Premium rooms are for family and must be blocked from general allocation. The owner will select their room numbers later; do not guess them.
- Extra bedding is included. Superior accommodates three adults/adult-counted occupants; Premium accommodates four, subject to the child-sharing policy below.
- Supply of extra bedding should not itself be treated as a fixed hotel-wide shortage. Unlimited supply does not authorise arbitrary adult occupancy in a room.
- Separate hotel: six rooms, three ground-floor and three first-floor, each accommodating up to four adults. Real room numbers and property name are not supplied.
- Separate dormitory: up to 12 driver/worker beds free. Guests cannot use it, and workers cannot use ordinary guest rooms. These restrictions are mandatory and cannot be overridden.

## R03 - Children, families, and sharing

- Age 10 and below is treated as a child for the owner's billing and bedding planning. Above age 10 counts as an adult. This supersedes the earlier age-12 suggestion.
- Couples with children receive Superior rooms with extra bedding rather than Premium rooms.
- The owner explicitly allowed two adults and two children aged 10 or below in a Superior room. Keep actual headcount separate from adult-counted occupancy.
- The maximum permitted number of young children physically occupying a room has not been supplied. Do not generalise the example into unlimited physical occupancy.
- Support named individuals, family headcounts, and later completion of names and ages. Do not double-count a family when its named members are entered.
- Couples and linked children should stay together. Splitting a family must produce a warning.
- Unrelated adults may share only when explicitly marked compatible.
- Support must-share, may-share, must-not-share, nearby-room, same-building, and separation relationships, with rule severity recorded explicitly.

## R04 - Placement and tags

- Use actual building/floor placement from the supplied structural inventory.
- Age 50 and above automatically requires ground floor. An individual tag may also require ground floor for a younger guest.
- Restaurant proximity is a preference. "Kitchen" in earlier discussion means restaurant.
- A room counts as nearby when directly neighbouring or opposite across a corridor. Actual adjacency needs confirmation; canvas proximity alone is not evidence.
- Bride/groom building/floor separation, quotas, mixed/shared groups, and other arrangements should be configurable through tags and rules, not fixed global assumptions.
- Both hotels are available during initial automatic assignment, but only guests explicitly tagged second-hotel eligible may be placed in that hotel.

## R05 - Dates and attendance

- Default check-in time: 2 PM on the guest's selected arrival date, either 24 or 25 November.
- All guests check out on 26 November 2026 at 11 AM.
- Record arrivals, departures, events, and individual meals separately. Reception-only attendance is not automatically an overnight stay.
- Show occupancy, availability, meal counts, and costs for the selected date/night. Preserve room availability over time rather than treating a room as used forever after one assignment.

## R06 - Wyndham allowance and excess charges

- The booked package covers 120 guests plus eight complimentary guests, giving an allowance of 128 per night.
- Family-room occupants are included in that allowance.
- Above age 10 is billed as adult; unknown ages must remain unresolved rather than being silently treated as free children.
- Excess charge applies only to Wyndham residents: max(0, chargeable resident count - 128) x INR 5,000 per night.
- INR 5,000 includes food and all taxes. Extra bedding is included.
- Calculate each night independently. No carryover is assumed; the owner accepted this planning assumption because actual hotel carryover was unknown.
- Non-resident guests attending Wyndham meals are charged separately per meal. Their meal rates are not supplied.
- Example: 132 chargeable residents on night one and 130 on night two produce (4 + 2) x INR 5,000 = INR 30,000.

## R07 - Other costs

- Driver/staff/vendor food: INR 150 per person per meal, replacing earlier INR 100. Track breakfast, lunch, and dinner separately, with planned and actual counts. The owner will assign applicable people later.
- Second hotel: provisional INR 18,000 per day for all six rooms and 12 guests with breakfast. The owner expects to negotiate a lower amount; this is not a confirmed contracted rate.
- Costs above 12 people at the second hotel are unpriced until a rate is entered. Do not assume they are zero or multiply the whole-property rate per room.
- Keep second-hotel accommodation, Wyndham excess-resident charges, non-resident meal charges, and staff meals distinct. Prevent unintentional double charging of included benefits.
- Display missing rates and provisional estimates explicitly. The known priced subtotal must not masquerade as a complete bill.

## R08 - Manual and automatic planning

- Automatically suggest assignments initially, then allow the owner to rearrange them.
- Drag individuals or whole families; support swapping rooms, moving occupants together, undo/redo, and highlighting compatible destinations.
- Allow room/placement locks. Automatic assignment must preserve locks and family-room reservations.
- When a social/preference rule would be violated, show the warning and obtain explicit owner confirmation before an allowed override. Record the exception.
- Mandatory dormitory separation, ownership permissions, and data-integrity restrictions are not bypassed by clicking a generic override.
- If not everyone can be assigned, keep unresolved people visible with a reason. Do not silently violate rules to produce a complete-looking result.

## R09 - Summary and colours

The selected date/night must show total rooms, used/free/reserved rooms, bride/groom usage, assigned and unassigned people, actual heads versus chargeable guests, bedding, dormitory usage, meals, rule conflicts, and estimated costs. Use colours plus labels/icons, with distinct representations for both sides, shared/mixed occupancy, unavailable/reserved rooms, and warnings.

## R10 - Access

- Only the owner's application login may edit any planning data, assignments, rooms, tags, rules, rates, imports, locks, overrides, or access settings.
- Family accounts are view-only and limited to their own side.
- Reception accounts are view-only and may receive relevant guest/contact/accommodation details, but must not receive cost data.
- Provide a users page where the owner assigns visibility/access settings. Do not provide a switch that grants a second application editor contrary to the sole-owner rule.
- Login uses username and password. Final account-bootstrap/recovery details are deferred.
- Visibility and mutation checks apply on the server, including live streams, exports, error messages, and direct API calls.

## R11 - Persistence and history

Shared state must persist in a private database. Record allocation changes, locks/unlocks, overrides, imports, rates, and access changes with actor and timestamp. Detect stale updates between the owner's sessions. Public source control must never contain runtime guest data.

## R12 - Canonical project record

The owner requested a new public repository on their GitHub profile as the source of truth. Maintain confirmed requirements, proposed architecture, database design, decisions, open items, implementation status, and code together. Reference attachments remain outside public Git history.

## R13 - Dedicated infrastructure

Owner instruction on 19 October 2026: download a fresh Debian cloud image, create template 9002 on Nageshwar, retain template 9001's cloud-init login/access details where present, and create a new dedicated VM on that node's local-lvm sized for this application. Later clarification: normal VLAN 1 and an owner-supplied static /23 address for the new VM. Actual connection details belong only in private handover records. Original template and existing guests must be preserved. Docker-host preparation does not itself constitute application implementation/deployment or backup acceptance.

Subsequent owner instruction: expose the preview on the local network so other LAN devices can open it without the owner's PC tunnel. Keep authentication and owner/viewer restrictions. LAN exposure does not authorize internet publishing or direct database exposure.

## Implementation qualification — core planning release

The supported child examples are retained; larger young-child arrangements remain unresolved under O02 rather than becoming an invented hotel policy. The first allocator uses whole-family units and bounded search. It may leave oversized families or unknown ages unassigned for manual review. Neither a solver proposal nor an estimate is applied/finalised automatically. Actual arrival/departure, function attendance and meal attendance are independent records. One person cannot be counted for the same meal at two locations on the same attendance basis.

General Premium allocation is blocked until the owner chooses the four reserved Premium rooms. Exact physical restaurant/neighbour relationships remain owner-confirmed inputs. The six secondary room numbers are internal placeholders until privately supplied.
