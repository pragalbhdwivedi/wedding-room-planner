"""Foundation worker: database heartbeat only; no allocation jobs are implemented."""
import signal
import time

from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import WorkerHeartbeat, now

running = True


def stop(*_):
    global running
    running = False


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
while running:
    with SessionLocal.begin() as db:
        db.execute(insert(WorkerHeartbeat).values(id="foundation", seen_at=now()).on_conflict_do_update(
            index_elements=[WorkerHeartbeat.id], set_={"seen_at": now()}))
    for _ in range(10):
        if not running:
            break
        time.sleep(1)
