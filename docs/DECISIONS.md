# Decision record

Dates use Asia/Kolkata. The baseline was reconciled on 19 October 2026. "Confirmed" means an explicit owner instruction; it does not mean implemented or tested.

| ID | Date | Status | Decision |
| --- | --- | --- | --- |
| D01 | 2026-10-18 | Confirmed | Visual web room planner with guest/family drag-and-drop, rules, automatic assignment, and live summaries. |
| D02 | 2026-10-18 | Confirmed | 44 Wyndham rooms: 40 general guest rooms and four blocked Premium family rooms, selected later by owner. |
| D03 | 2026-10-18 | Confirmed | 120 + 8 complimentary guests per night, including family-room occupants; INR 5,000 per excess Wyndham resident/night including food/taxes. |
| D04 | 2026-10-18 | Confirmed | Bedding is included. Adult-counted capacity is three in Superior and four in Premium; young-child physical ceiling remains open. |
| D05 | 2026-10-19 | Confirmed | Age 10 and below is child treatment for owner's billing/bedding. Above 10 counts as adult. Supersedes age-12 discussion. |
| D06 | 2026-10-19 | Confirmed | Couples with children use Superior rooms with extra bedding; two adults plus two children aged <=10 is allowed. |
| D07 | 2026-10-18 | Confirmed | Dormitory has 12 free staff/driver/worker beds; guests and workers cannot cross accommodation categories. |
| D08 | 2026-10-18 | Superseded | INR 100 staff meal rate replaced by D09. |
| D09 | 2026-10-18 | Confirmed | INR 150 per driver/staff/vendor per meal; planned and actual meal counts. |
| D10 | 2026-10-19 | Confirmed | Second hotel has six rooms, three per floor, each up to four adults. Allocate only explicitly eligible tagged guests; available from first solver run. |
| D11 | 2026-10-19 | Provisional business estimate | INR 18,000/day for all six second-hotel rooms and 12 guests with breakfast; negotiated final amount and extra-person costs not settled. |
| D12 | 2026-10-19 | Confirmed | Ground floor required at age 50+ or through individual accessibility tag; restaurant proximity preferred. |
| D13 | 2026-10-18 | Confirmed | Direct neighbours and opposite-across-corridor rooms count as nearby. |
| D14 | 2026-10-19 | Confirmed | All check out 26 November at 11 AM; arrivals 24/25 November at default 2 PM; meals/events separate from stay. |
| D15 | 2026-10-19 | Confirmed planning assumption | Compute each night independently; no carryover assumed. Actual hotel carryover remains unknown. |
| D16 | 2026-10-19 | Confirmed; latest access instruction | Only owner login edits anything. Families see own side; reception views operational details without costs. Supersedes family-editor possibilities. |
| D17 | 2026-10-19 | Confirmed | Username/password login; bootstrap/recovery design deferred. |
| D18 | 2026-10-19 | Confirmed | Build and run application inside Docker. |
| D19 | 2026-10-19 | Proposed technical design | React/TypeScript/Vite/React Flow, FastAPI/Python, OR-Tools CP-SAT, PostgreSQL/SQLAlchemy/Alembic, Caddy, Docker Compose. |
| D20 | 2026-10-19 | Proposed technical design | Separate web/API/worker/database containers; persistent volumes; one-off migrations; off-host backups and restore test. |
| D21 | 2026-10-19 | Proposed technical design | Shared server rules, revision checks, owner-accepted solver proposals, safe imports, per-field visibility, audit history. |
| D22 | 2026-10-19 | Confirmed | Public GitHub repository on owner's profile becomes project source of truth. |
| D23 | 2026-10-19 | Confirmed | Fresh Debian template 9002 and a new dedicated application VM on Nageshwar local-lvm; preserve source template 9001. |
| D24 | 2026-10-19 | Confirmed; latest network instruction | Normal/native VLAN 1, not the source template's AADI VLAN. Owner supplies static /23 address for the application VM; template remains DHCP. Connection details stay private. |
| D25 | 2026-10-19 | Implemented infrastructure choice | Template 9002 and full clone 9601; application VM 4 vCPU, 4 GiB RAM, 40 GiB disk. Docker Engine 29.9.1 / Compose 5.6.0 installed and host reboot verified; application not built. |
| D26 | 2026-10-19 | Confirmed | Owner explicitly deferred backup work and instructed implementation to start. No backup/restore completion is implied. |
| D27 | 2026-10-19 | Implemented foundation choice | Private setup key creates one owner; Argon2id passwords, server sessions, CSRF, persistent throttling and owner-only viewer management. Recovery remains open. |
| D28 | 2026-10-19 | Implemented foundation choice | Initial app binds to loopback for SSH-forwarded preview. Shared phone/reception access requires the later HTTPS ingress step. |
| D29 | 2026-10-19 | Confirmed | Owner requested network exposure of the preview. Add explicit private-address LAN access, retaining authentication and private database/API services. Supersedes loopback-only access in D28; trusted HTTPS ingress remains separate work. |

| D30 | 2026-10-19 | Confirmed implementation instruction | Owner completed setup and instructed implementation of guest entry, reservations, drag/drop assignment, automatic allocation, billing and the remaining core workflow. Existing owner account must be preserved. |
| D31 | 2026-10-19 | Implemented technical choice | Shared pure validation, revision-locked transactions, expiring owner-bound previews, exact warning acknowledgements and append-only assignment/estimate history. No arbitrary executable rule language. |
| D32 | 2026-10-19 | Implemented technical limit; business policy remains open | Initial allocator keeps families as units; larger groups require manual split review. Unknown ages and child arrangements beyond the known supported examples remain unresolved, not assumed safe. This does not set a newly confirmed hotel child ceiling. |
| D33 | 2026-10-19 | Implemented least-disclosure choice | Family viewers see their own guests/placements/attendance without contacts/private notes/costs; reception sees operational contacts/attendance without private notes or costs. Owner alone changes any planning data. |

| D34 | 2026-10-19 | Confirmed | Draft initial placements using supplied adult/child counts; keep missing exact ages and age-50+ accessibility checks explicitly pending. Unknown bands remain unresolved. |
| D35 | 2026-10-19 | Confirmed | Until four Premium family-room numbers are selected, preserve an unnamed four-room reserve pool unused across both nights. Supersedes D32's exact-age prerequisite and the initial exact-reservation prerequisite. |
| D36 | 2026-10-19 | Confirmed | Show all Wyndham rooms initially; retain block/floor filters and editable topology. |
| D37 | 2026-10-19 | Confirmed | Add invitation function/family context privately and use its visual theme. Directory people do not automatically add accommodation headcounts; RSVP integration remains separate. |
| D38 | 2026-10-19 | Confirmed | Give each guest tickable tags and a male/female selection; keep unspecified until the owner chooses. |
| D39 | 2026-10-19 | Confirmed | Automatically combine Friends with the same selected gender only within their own bride/groom side. Keep couples and linked children together. |
| D40 | 2026-10-19 | Implementation choice | An edit that newly requires ground floor is reviewed with a valid room move before the guest detail and assignment are saved together. The mandatory age-50 rule and locks remain enforced. |
| D41 | 2026-10-19 | Confirmed request and implementation choice | Owner can delete a guest member. A review shows affected placements before application; linked live records are removed, and assignment undo/redo resets so a deleted identity cannot be restored accidentally. |
| D42 | 2026-10-19 | Confirmed request; superseded in part by D43 | Owner can open a room and manually tick any number of individual people, including only part of a four-person family, to place together for the chosen night. Preview and explicit split-family acknowledgement still apply. Its separate-link requirement was replaced by D43. |
| D43 | 2026-10-19 | Implemented after owner confirmation | The owner may confirm each eligible roommate pair within the placement review; the compatibility links and move save together. Hard exclusions, Friends rules, locks and capacity remain enforced. |
| D44 | 2026-10-20 | Confirmed operational change | The owner established an HTTPS reverse proxy for the planner. The application trusts that exact HTTPS origin in production mode with Secure cookies, and the proxy redirects public HTTP to HTTPS; private database/API ports and owner-only editing remain unchanged. The owner confirmed phone sign-in reached the planner. |

## Future decisions

Append a dated decision for each owner policy change. Mark superseded decisions explicitly and update the canonical requirement and relevant acceptance checks in the same commit. Do not rewrite a proposed design as a confirmed owner decision merely because it appeared in an assistant explanation.
