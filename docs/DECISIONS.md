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

## Future decisions

Append a dated decision for each owner policy change. Mark superseded decisions explicitly and update the canonical requirement and relevant acceptance checks in the same commit. Do not rewrite a proposed design as a confirmed owner decision merely because it appeared in an assistant explanation.
