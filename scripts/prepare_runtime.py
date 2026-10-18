"""Create private runtime secrets without replacing existing credentials.

Run with sudo on the dedicated Linux Docker host. No secrets are printed.
"""
import argparse
import os
import secrets
from pathlib import Path
from urllib.parse import urlparse

p = argparse.ArgumentParser()
p.add_argument("--revision", required=True)
p.add_argument("--mode", choices=["local", "production"], default="local")
p.add_argument("--origins", default="http://127.0.0.1:8769,http://localhost:8769,http://127.0.0.1:8080")
args = p.parse_args()
if os.name != "posix" or os.geteuid() != 0:
    raise SystemExit("Run with sudo on the dedicated Linux Docker host")
origins = [o.strip() for o in args.origins.split(",")]
if args.mode == "local" and any(urlparse(o).hostname not in {"localhost", "127.0.0.1", "::1"} for o in origins):
    raise SystemExit("Local mode requires loopback origins")
if args.mode == "production" and any(urlparse(o).scheme != "https" for o in origins):
    raise SystemExit("Production requires HTTPS origins")
if not args.revision.isalnum():
    raise SystemExit("Revision must be an alphanumeric source identifier")
root = Path(__file__).resolve().parent.parent
private = root / ".private"
private.mkdir(mode=0o700, exist_ok=True)
os.chown(private, 10001, 10001)
os.chmod(private, 0o700)
for name in ["db_admin_password", "db_app_password", "db_migration_password", "bootstrap_token", "test_bootstrap_token"]:
    path = private / name
    if not path.exists():
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(48) + "\n")
    if len(path.read_text().strip()) < 32:
        raise SystemExit("An existing secret is invalid; inspect it without resetting credentials")
    os.chown(path, 10001, 10001)
    # Compose file secrets are read-only bind mounts. The private parent remains
    # 0700; 0444 lets the API UID and PostgreSQL UID read only their mounted files.
    os.chmod(path, 0o444)
env = root / ".env"
if not env.exists():
    env.write_text(f"APP_MODE={args.mode}\nCOOKIE_SECURE={'false' if args.mode == 'local' else 'true'}\nALLOWED_ORIGINS={args.origins}\nAPP_REVISION={args.revision}\nWEB_PORT=8080\n")
    env.chmod(0o600)
print("Private runtime secrets prepared; existing values preserved. No credentials printed.")
