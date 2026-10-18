# Open items

These remain open as of the 19 October 2026 baseline. Do not invent answers. Most are configurable inputs rather than reasons to delay building the basic application.

| ID | Item | Required handling until resolved |
| --- | --- | --- |
| O01 | Four family Premium room numbers | Hold back four Premium rooms from general inventory; owner chooses exact numbers. Solver must explain pending room selection if it needs physical locations. |
| O02 | Exact child physical ceiling and bedding quantity | Preserve allowed example of two adults plus two young children in Superior. Do not infer unlimited children or unlimited per-room adults from included bedding. Flag arrangements outside the known policy. |
| O03 | Adult child of a couple / family of three adult-counted people | Couple-with-children Superior rule is confirmed, but edge semantics and physical constraints for larger families need validation. Keep conflicts visible. |
| O04 | Corridor neighbours/opposite pairs, restaurant paths, stairs/lifts | Derive only defensible schematic positions; mark unverified relationships before relying on them as physical facts. |
| O05 | Second-hotel name, room numbers, bed arrangements, exact layout | Clearly labelled internal placeholders; no invented real numbers. |
| O06 | Non-resident guest meal rates | Attendance can be recorded; costs stay unpriced. INR 150 applies to assigned driver/staff/vendor categories, not automatically every non-resident. |
| O07 | Final second-hotel rate, included dates/day definition, extra guests above 12 | Keep INR 18,000/day whole-property estimate provisional. Show missing additional-person charges and unsettled billing periods. |
| O08 | Actual Wyndham carryover treatment | Owner-approved estimate uses no carryover; record as planning assumption, not hotel contract confirmation. |
| O09 | Which people are drivers/staff/vendors and applicable meals | Owner tags later; planned/actual meal status remains explicit. |
| O10 | Final side quotas/separation/mixed-room rules and solver weights | Configurable; do not silently impose equal halves or a universal split. Suggested scoring is proposed. |
| O11 | Password recovery and real viewer account details | Private-key single-owner bootstrap is implemented. No shared/default/public credentials or public self-signup. Recovery remains open; owner creates viewers privately. |
| O12 | Exact family-view cost/contact/note visibility, reception fields and export permissions | Reception costs forbidden; family own-side scope confirmed. Apply least disclosure pending owner choices. |
| O13 | Domain, ingress and HTTPS routing | Dedicated host selected and prepared under D23-D25. Foundation uses an SSH-forwarded loopback preview; shared phone/reception access and HTTPS remain pending. |
| O14 | Backup destination, retention, recovery targets, data retention after event | Owner explicitly deferred backup work under D26. No scheduled backup or recovery verification is claimed. |
| O15 | Guest names, ages, contacts, headcounts and relationship tags | Enter privately later. Never request or publish these in public issues. |
| O16 | Public software licence | None selected. Do not add an open-source licence automatically. |
| O17 | Named reservation rooms vs reservation-pool behaviour before selection | Logical holdback can preserve quantity, but exact physical assignment should wait for owner selection. |

## Explicitly deferred, not blocking the document baseline

The planner's integration with the invitation/RSVP system is not part of an approved implementation scope yet. The foundation implements the basic web/API/database stack; React Flow, solver jobs and the broader planning workflow remain later stages. See STATUS.md for exact verification and deployment evidence.
