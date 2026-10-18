# Public source and private runtime data

The owner explicitly requested a public repository. It contains the application specification, architectural proposals, generic business rules and rates discussed for this planner, derived structural room inventory, code when implemented, and synthetic test fixtures.

## Excluded from public GitHub

- Guest names linked to wedding attendance, ages/dates of birth, family records, mobile numbers, contacts, travel details, actual room assignments, and meal attendance.
- Private compatibility, separation, guardian, accessibility, or conflict notes about identifiable people.
- The source room-layout workbook, invitation brief, photographs, and other original synced/attached files.
- Runtime database contents, dumps/backups, guest spreadsheets, exported lists, private screenshots, logs containing personal information.
- Passwords, credential hashes, tokens, session cookies, private keys, secret files, and sensitive deployment connection details.

## Runtime storage

Use the private database for records and persistent restricted storage for necessary uploads. Apply access control before returning data to viewers, live updates, or exports. Reception never receives cost fields. Families see their own side under the owner's configured visibility scope.

Keep operational backups protected and off-host. Retention and post-event deletion require an owner decision. Do not treat a gitignore rule as protection for an already-tracked file or for CI artifacts.

## Fixtures and diagnostics

Only synthetic people and contacts may appear in tests/examples. Use redacted diagnostics; never attach a real production database to a public issue or CI artifact. Avoid private paths, host details, and identity information in public documentation.

## Publication discipline

Review exactly what is being committed. Do not copy or recursively push the ChatGPT project's source/attachment directories. If sensitive data is accidentally published, stop further publication, notify the owner, revoke affected credentials if applicable, and follow a removal/recovery plan; deleting it from the latest commit alone does not remove Git history.
