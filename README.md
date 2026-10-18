# Wedding Room Planner

Canonical source of truth for the wedding accommodation planner: requirements, decisions, architecture, implementation status and application code.

Canonical repository: [pragalbhdwivedi/wedding-room-planner](https://github.com/pragalbhdwivedi/wedding-room-planner), branch `main`.

**Implemented: private guest/family entry, family reservations, editable room topology, drag/drop and tap assignment, locks/swaps/history, automatic allocation proposals, arrivals/functions/meals, billing estimates, scoped Excel import/export and live views.** Verification and deployment evidence are recorded in [status](docs/STATUS.md).

The owner requested this public repository on 19 October 2026 (Asia/Kolkata) to prevent future ambiguity. The repository records the room-planning application separately from the existing invitation website.

## Start here

| Document | Purpose |
| --- | --- |
| [Requirements](docs/REQUIREMENTS.md) | Confirmed behaviour and business rules |
| [Decisions](docs/DECISIONS.md) | Changes, superseded values, and decision status |
| [Architecture](docs/ARCHITECTURE.md) | Proposed application and Docker design |
| [Database](docs/DATABASE.md) | Proposed logical data model and integrity controls |
| [Room inventory](docs/ROOM_INVENTORY.md) | Workbook-derived inventory and layout limits |
| [Open items](docs/OPEN_ITEMS.md) | Remaining inputs and unresolved policy edges |
| [Delivery plan](docs/ROADMAP.md) | Implementation order |
| [Acceptance checks](docs/ACCEPTANCE.md) | Behaviour that must be demonstrated |
| [Status](docs/STATUS.md) | What exists and what has been verified |
| [Infrastructure](docs/INFRASTRUCTURE.md) | Dedicated Debian Docker host and verification limits |
| [Planning guide](docs/PLANNING_GUIDE.md) | Guest entry, reservations, placement, attendance, estimates and Excel |
| [Operator guide](docs/RUNBOOK.md) | Installation, private owner setup, checks and upgrades |
| [Data policy](docs/DATA_POLICY.md) | Public source versus private runtime data |
| [Contributing](CONTRIBUTING.md) | How to keep this repository authoritative |

## Product

A phone- and laptop-friendly room planner with a hotel topology canvas, individual/family drag-and-drop, automatic initial assignment, rule validation, room locks, attendance, costs, Excel import/export, and live updates.

Only the owner's application login may change planning data or settings. Family and reception accounts are view-only, with separate visibility scopes. Reception must never receive cost data.

## Inventory and policies

- Wyndham: 44 rooms; 40 general guest rooms and four Premium rooms reserved for family.
- Separate hotel: six rooms, each accommodating up to four adults.
- Separate staff dormitory: 12 free beds; mandatory separation from guest accommodation.
- Wyndham package: 120 + 8 complimentary guests per night, including family-room occupants.
- Wyndham excess residents: INR 5,000 per chargeable person per night, including food and all taxes; no carryover assumed.
- Driver/staff/vendor meals: INR 150 per person per meal.
- Second-hotel estimate: INR 18,000 per day for all six rooms and 12 guests with breakfast; unsettled estimate, not a confirmed contract.

Full qualifications and unresolved cases are in the requirements and open-items documents. The source workbook and all personal guest data are excluded from this public repository.

## Application stack

The foundation uses React, TypeScript, Vite, Python/FastAPI, PostgreSQL, SQLAlchemy, Alembic, Caddy and Docker Compose. Dependency lockfiles and base-image digests are committed. React Flow provides the room canvas and OR-Tools CP-SAT produces reviewed allocation proposals. See [architecture](docs/ARCHITECTURE.md).

Follow the [operator guide](docs/RUNBOOK.md) to generate private runtime credentials, build, verify and start the application. Web access defaults to loopback; an explicit LAN preview can bind to the host's private address. There is no default login or public registration. Only the owner chooses the first real username/password using a private setup key.

## Source-of-truth rules

1. The latest explicit owner decision governs. Reconcile it into the repository in the same change that implements it.
2. `main` contains the recorded baseline. Open issues and pull requests are proposals until incorporated and marked accordingly.
3. Requirements, design, implementation, automated verification, deployment, and owner acceptance are separate states.
4. Never treat a missing rate as zero or an unknown age as a child.
5. Never publish guest records, room assignments, private relationship notes, credentials, database backups, or original reference attachments.

The owner has not selected a public software licence. Public visibility alone does not supply one.
