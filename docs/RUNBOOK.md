# Operator guide

This release includes the private planning workflows described in [Planning guide](PLANNING_GUIDE.md). PostgreSQL migration `0002_planning` adds these tables without replacing owner credentials, sessions or the foundation inventory.

## First installation

Run on the dedicated Linux Docker host from a checkout of the intended Git commit. Builds happen inside Docker. Do not run a second checkout against the same Compose project or database volume.

```sh
sudo python3 scripts/prepare_runtime.py --revision "$(git rev-parse HEAD)"
sudo docker compose build api web
sudo docker compose -f compose.test.yaml build test
sudo docker compose -f compose.test.yaml up -d --wait testdb
sudo docker compose -f compose.test.yaml run --rm --no-deps migrate-test
sudo docker compose -f compose.test.yaml run --rm --no-deps test
sudo docker compose -f compose.test.yaml down --volumes
sudo docker compose up -d --wait
sudo docker compose ps
```

Stop on a failed command. The test database is a separate Compose project, uses temporary storage, and contains synthetic users only. Never use `down --volumes` with the main `compose.yaml`: it deletes the application database.

The provisioner creates private random database passwords and bootstrap keys once. It preserves existing credentials and `.env` on subsequent runs. Runtime files stay in `.private/` and `.env`, outside Git and Docker build contexts. Only root and the application UID can traverse the private directory; Compose mounts each service's required secret files read-only. A migration role owns the schema; the API uses a separate non-superuser role without schema creation or audit-history modification rights.

## Private owner setup

Web access initially binds only to the host loopback port 8080. Use an SSH forward to a local browser port, such as 8769; both loopback origins are configured by the provisioner. The operator supplies the private contents of `.private/bootstrap_token` directly to the owner. Never paste it into GitHub, logs or chat.

Open the forwarded page and enter the setup key, display name, chosen username and password of at least 14 characters. There are no default credentials. Owner creation is transactional and single-use; concurrent attempts cannot create a second owner. Keep the chosen password privately. Account recovery is not implemented; do not improvise a public reset endpoint.

After setup, only the owner can create and manage family/reception viewer accounts. Family accounts require a bride/groom side. Reception accounts have no side and do not receive cost policy fields. All viewers are read-only. Updating access, suspending an account or resetting its password revokes that viewer's sessions. Guest, assignment, attendance, event and Excel responses enforce the same side/field restrictions. Family viewers do not receive contacts or private notes; reception receives operational contacts but no cost data.

## Restart, persistence and upgrades

PostgreSQL data uses a named volume at the PostgreSQL 18 data parent directory. Recreating application containers preserves it. The migration service must finish successfully before API/worker startup. The worker records a health heartbeat and claims allocation jobs with a bounded lease, two recovery attempts and a bounded solver time. It produces proposals, never applied room changes.

For an upgrade, select and review the intended source commit, preserve `.private/` and `.env`, and update only `APP_REVISION` in `.env` to that commit. Build and run the isolated checks before starting changed services. Schema rollback and password rotation are not automated. Do not replace secrets against an existing database or assume a previous container image can reverse a schema migration.

## Transport and remaining operations

Web access defaults to authenticated SSH forwarding. Local mode accepts loopback origins only. The owner subsequently requested LAN access (D29). An explicit `lan` preview mode supports private IPv4 addresses and loopback origins; public addresses and arbitrary hostnames are rejected. This is an HTTP preview on the trusted LAN: credentials and sessions are not encrypted in transit. Production mode still requires HTTPS origins and Secure cookies. PostgreSQL has no host-published port.

To enable LAN access on an existing deployment, preserve credentials and database volumes, set `WEB_BIND_ADDRESS` to the VM's private address, `APP_MODE=lan`, `COOKIE_SECURE=false`, and `ALLOWED_ORIGINS` to the exact browser origin including port. Keep actual operational addresses only in private `.env` and handover records. Build/check the selected source revision, then recreate application services with `sudo docker compose up -d --wait`. Verify the health/setup endpoints from a different LAN machine, origin rejection and unauthenticated data protection. Do not publish database/API ports or configure internet forwarding as part of LAN exposure.

For a fresh LAN installation, the provisioner accepts `--mode lan --bind-address <private-ip> --origins http://<private-ip>:8080`. It preserves an existing `.env`, so it does not silently change an existing transport policy. For shared HTTPS, configure a trusted domain/proxy, `APP_MODE=production`, `COOKIE_SECURE=true` and one exact `ALLOWED_ORIGINS=https://<hostname>` value. Configure the public proxy to redirect HTTP to HTTPS before displaying the sign-in form; verify an HTTP request gets a redirect with an HTTPS Location, and check that HTTPS does not loop. Preserve the existing private `.env`, secrets and PostgreSQL volume; change only those transport fields, validate Compose, then recreate the services with `sudo docker compose up -d --no-build --wait`. Use the HTTPS address for sign-in afterward: Secure cookies are not sent to the earlier HTTP LAN address. Check public health, signed-out API denial, same-origin sign-in handling, foreign-origin rejection and a real authenticated session on the owner's device. Do not add a wildcard origin or publish the API/database ports.

Backup work was explicitly deferred by the owner on 19 October 2026. No scheduled backup or restore test is claimed. Add off-host database/config backup and verified restore as a separate operational step; container persistence is not a backup.

## Planning upgrades and rollback

Migration `0002_planning` is additive; it preserves foundation users, password hashes and sessions. Runtime cannot update/delete audit, assignment-history or saved-estimate rows. Test downgrade/upgrade is exercised only against disposable synthetic data. Never downgrade the live planning database: it would remove planning tables and their data. A compatible forward fix is the preferred recovery after real entries; retain the previous images and preserve the private volume. The prior foundation app expects schema 0001 and cannot serve a 0002 database without a compatible health/version change.

Solver jobs accept at most 300 resident guests, run for up to 10 seconds by default (15-second code ceiling), and keep a family together as an initial allocation unit. Oversized or unresolved units remain unassigned with reasons; review a manual split explicitly. Imports support at most 1,000 guest slots, 5 MiB compressed workbook content, 20 MiB expanded content, and no formulas/macros/external workbook links. Import and move previews expire and must be repeated after any newer plan revision.

The server sends revision-only events and rechecks session expiry; clients reload the scoped state and fall back to a 15-second refresh. A connection is not an offline-editing guarantee. Changing a rate does not overwrite saved estimate snapshots. Actual arrival timestamps and meal/event attendance are separate from planned accommodation nights.
