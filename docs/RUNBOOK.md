# Foundation operator guide

This release supplies owner login, viewer account management and a read-only room inventory. It does not yet assign guests, calculate bills, import files or run an allocator.

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

Open the forwarded page and enter the setup key, display name, chosen username and password of at least 14 characters. There are no default credentials. Owner creation is transactional and single-use; concurrent attempts cannot create a second owner. Keep the chosen password privately. Account recovery is not implemented in this foundation release; do not improvise a public reset endpoint.

After setup, only the owner can create and manage family/reception viewer accounts. Family accounts require a bride/groom side. Reception accounts have no side and do not receive cost policy fields. All viewers are read-only. Updating access, suspending an account or resetting its password revokes that viewer's sessions. Existing guest records and operational contact fields do not exist yet; their side/field scoping must be verified when introduced.

## Restart, persistence and upgrades

PostgreSQL data uses a named volume at the PostgreSQL 18 data parent directory. Recreating application containers preserves it. The migration service must finish successfully before API/worker startup. The worker currently records a health heartbeat only; it does not allocate rooms or process files.

For an upgrade, select and review the intended source commit, preserve `.private/` and `.env`, and update only `APP_REVISION` in `.env` to that commit. Build and run the isolated checks before starting changed services. Schema rollback and password rotation are not automated. Do not replace secrets against an existing database or assume a previous container image can reverse a schema migration.

## Transport and remaining operations

The initial preview is reachable through authenticated SSH forwarding. Local mode deliberately accepts loopback origins only and uses a non-Secure cookie over that loopback HTTP connection. Before a shared phone/reception rollout, configure trusted HTTPS ingress, explicit HTTPS origins, `APP_MODE=production` and `COOKIE_SECURE=true`. Production mode refuses insecure cookie/origin settings. PostgreSQL has no host-published port.

Backup work was explicitly deferred by the owner on 19 October 2026. No scheduled backup or restore test is claimed. Add off-host database/config backup and verified restore as a separate operational step; container persistence is not a backup.
