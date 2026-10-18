# Planning guide

Only your owner login can change this plan. Family viewers see their own side; reception sees operational details and contact numbers, with no costs or private notes.

## 1. Enter people privately

Open **Guests & families → Add guests**. Make one slot for every person, including children, and choose the side, category and planned arrival. Blank names and ages are allowed for preparation; complete those same slots later rather than adding them again. For a provisional assignment, select Adult (>10) or Child (<=10) when the exact age is pending. Never enter an invented age. Confirm exact ages and age-50+ accessibility before finalising. Choose **Non-resident / event only** for people who attend without staying.

Entering an exact age sets the adult/child choice automatically. Changing that choice clears the exact age and leaves a provisional band. In an existing family, **Add guest slot** creates another person. If that family is already placed, saving opens a review of the proposed room placement or the reason the new person remains unassigned; apply the review to finish saving. **Delete member on save** removes an existing member from the draft, then Save opens a final review of affected rooms. Closing the form cancels the pending deletion. Deleted members lose active assignments, attendance and links; assignment undo/redo starts fresh. Unlock an occupied room before deleting its member.

Use **Couple with children** for the Superior-room rule and **Eligible for reserved family rooms** only for people allowed in the four family rooms. Built-in tags cover ground floor, restaurant proximity and the second hotel; extra text tags can target conditional rules. An age of 50 or above independently requires ground floor. Staff, drivers and vendors use the separate dormitory, never guest rooms.

## 2. Reserve family rooms and verify topology

In **Rooms & rules**, select exactly four Premium rooms. They are excluded from general placement. Alternatively keep the four-room Premium reserve pool until you choose the numbers; four Premium rooms must remain unused across both nights. The other 40 Wyndham rooms are general inventory.

The planner opens on all 44 Wyndham rooms in a scrollable grid. Switch to Topology for the schematic canvas, or filter by property/block/floor. The second hotel and 12 staff beds remain separate inventories. **Edit layout** moves room cards and saves their schematic coordinates. It does not establish real corridor proximity. Add confirmed neighbouring/opposite connections and mark a room near the restaurant only when you know those facts. The second hotel's six initial room labels are explicitly unnumbered placeholders.

## 3. Place and arrange

Select a family/person then tap a room, or drag them to a card. Green outlines identify eligible destinations; a blocked destination explains its conflict. Review the exact guest/night/from/to list before applying. Warnings need individual confirmation; mandatory capacity, staff separation, reservation and access rules cannot be overridden.

Room details provide per-night locks, unassignment and room swaps. **Undo/redo** applies to assignment changes, not every kind of edit. Locks and current rules are checked again when undoing. Split-family warnings can require confirmation during history actions too.

The right panel distinguishes actual heads, Wyndham's 44 rooms, the six secondary rooms, staff beds, side usage, extra bedding and the estimate. Family viewers do not receive other-side room usage. Included bedding has no extra hotel charge.

## 4. Suggest an initial plan

Choose **Suggest rooms** with either four named Premium reservations or the four-room unnamed reserve pool. The worker leaves your current plan in place. Review the resulting proposal, any unresolved people, exact proposed moves and the resulting known estimate, then apply it explicitly.

The initial solver keeps families together as units, preserves locks, enforces eligibility/compatibility, and searches for up to 10 seconds. It supports up to 300 resident people; guest entry/import supports 1,000 total slots. A large family may need a reviewed manual split. An explicit adult/child band allows a provisional draft without an exact age; completely unknown bands and child arrangements outside the supported examples remain unresolved. Pending ages/accessibility are shown for review. A feasible result is not a guarantee of a globally best plan; the result labels its search status.

Use typed conditional rules for allowed rooms by side/tag, a side room maximum, and side separation by room/block/floor. Add pair relationships for explicit sharing, must-share, cannot-share, nearby or same-building requests. Rule text is a label, not executable code.

## 5. Record attendance and reconcile costs

**Arrivals & functions** records actual arrivals/departures independently of the planned accommodation dates. Add dated functions and distinguish expected people from actual attendance. Function attendance does not automatically create meal charges.

In **Attendance & billing**, record meals by person, day and location, with separate planned/actual status. Mark package-covered food **Included**, separate food **Chargeable**, and unsettled coverage **Unconfirmed**. The same person/date/meal cannot count at two locations on the same basis. Unknown actual attendance is not assumed present or absent.

Wyndham excess uses chargeable residents above 128 for each night independently, at INR 5,000/person/night including food and taxes. Age 10 is a child; age 11 is adult-counted. Wyndham staff meals use INR 150/person/meal. Guest meal prices remain blank until supplied. The second hotel is a provisional whole-property INR 18,000/day, not six times that rate; select billable days explicitly and leave additional-person rates unpriced until known.

The displayed amount is a **known subtotal**, with unresolved items separately visible. It remains an estimate. Saving a snapshot preserves its rates and calculated amounts even after later rate edits; this is not a hotel invoice or payment operation.

## 6. Excel and simultaneous use

Download the owner template or export your current plan. Import only the **Guests** sheet through the preview. Preserve Guest ID and Family ID for updates; blank IDs create new slots. Duplicate names warn; duplicate IDs or invalid rows block application. Import does not delete guests or import assignments, room settings, rates or attendance. Exports include the scoped current assignments, arrivals, functions and meals, plus owner-only estimates.

Other sessions refresh live; stale writes/previews are rejected. Review again after another change. There is no offline-editing mode. All actual guest information stays in the private database and exports, outside the public repository.

Trusted HTTPS, backup/restore work and owner acceptance remain tracked separately in STATUS.md and OPEN_ITEMS.md.


## 7. Invitation context

**Arrivals & functions** also holds the couple and family directory. Only the owner edits it; family viewers receive their own side. These details never create guest slots or increase resident counts. Keep real guests in the accommodation roster separately and reuse stable IDs when completing names. Functions can include local Asia/Kolkata times (00:00 belongs to its selected date), venue and an https source link. Repeated function names on the same date/side are rejected. Invitation content does not mark anyone attending or charge meals.
