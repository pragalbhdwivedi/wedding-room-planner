from datetime import timedelta
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from .allocator import allocate
from .db import SessionLocal
from .models import AllocationRun, WorkerHeartbeat, now


def process_one():
    job_id=None
    with SessionLocal.begin() as db:
        db.execute(insert(WorkerHeartbeat).values(id="foundation",seen_at=now()).on_conflict_do_update(index_elements=[WorkerHeartbeat.id],set_={"seen_at":now()}))
        job=db.scalar(select(AllocationRun).where(or_(AllocationRun.status=="queued",(AllocationRun.status=="running") & (AllocationRun.lease_until<now()))).order_by(AllocationRun.created_at).with_for_update(skip_locked=True).limit(1))
        if job:
            if job.attempts>=2:
                job.status="failed";job.result={"diagnostics":["The job could not finish after worker recovery. Try a fresh run."]}
            else:
                job.status="running";job.attempts+=1;job.lease_until=now()+timedelta(seconds=60)
                job_id,inputs,attempt=job.id,job.snapshot,job.attempts
    if not job_id:return False
    try:result=allocate(inputs);status="completed"
    except Exception:result={"diagnostics":["Allocation failed safely; existing assignments were not changed."]};status="failed"
    with SessionLocal.begin() as db:
        job=db.scalar(select(AllocationRun).where(AllocationRun.id==job_id).with_for_update())
        if job and job.status=="running" and job.attempts==attempt:
            job.status=status;job.result=result;job.lease_until=None
    return True
