# Repository instructions

## Authority and scope

- This repository is the source of truth for the room-planning application. Read README.md, docs/REQUIREMENTS.md, docs/DECISIONS.md, docs/OPEN_ITEMS.md, and docs/STATUS.md before changes.
- Owner instructions take precedence. Record newly confirmed decisions; do not silently resolve an open question or promote a proposal to a requirement.
- The invitation website is a separate project. Do not inherit its mobile-only design or deploy this private planner into its public invitation flow.
- The owner and explicitly granted full-access editor accounts may edit planning data/settings/users. Family and reception accounts remain viewers. This does not prohibit users from authenticating or ending their own sessions.
- Do not assume any existing Docker host is allocated or healthy. Select and verify a target before deployment. No infrastructure changes are authorised solely by this file.

## Public-repository boundary

- Never commit guest/person/family contact records, actual room assignments, compatibility/conflict notes, ages or dates of birth linked to people, original attachments, private exports, database dumps, passwords, tokens, keys, or session information.
- Use synthetic people in examples and tests. Sanitise screenshots, logs, issue bodies, and CI artifacts.
- Runtime data belongs in the private database and controlled persistent storage. .gitignore is a safeguard, not a substitute for reviewing staged content.
- Do not copy the project's read-only synced sources or attachments into this checkout. The derived room-inventory documentation contains the reviewed structural facts needed for design.

## Implementation discipline

- Use one server-side rules module across manual moves, auto-assignment application, imports, and final validation.
- Enforce authorization and field visibility in API responses, event streams, and exports; hiding buttons is insufficient.
- Separate actual people, hotel-counted guests, bedding needs, and physical occupancy. A child aged 10 or under counts toward hotel headcount only when an editor explicitly assigns a separate bed for that night. Do not invent a child physical-capacity ceiling.
- Block overlapping assignments for one guest. Sharing a room is normal and must not be prohibited by a room-level one-guest constraint.
- Preserve locks and reserved inventory during solver runs. Apply proposals transactionally only after revalidating their input revision.
- For a manual room or bed move, show planning conflicts as advisory warnings and let an authorised owner/editor apply the move without extra acknowledgements. Audit the exact issue IDs. The solver remains rule-aware. Enforce authentication, known guest/resource/night, unique guest-night occupancy, revision checks and fixed hotel inventory.
- Database changes require migrations. Monetary calculations must use precise integer paise or an equivalent exact representation.
- Update affected requirements, decisions, open items, acceptance checks, and status with code changes.
- Report tests against the exact commit and environment. A successful image build is not functional acceptance or deployment.
- Do not add a licence, expose a live service, enrol infrastructure, or invent missing business rates without owner direction.
