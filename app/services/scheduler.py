from datetime import datetime, timedelta, timezone
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

_scheduler = None

def _sync_db_url(url):
    return url.replace("+asyncpg", "+psycopg2") if "+asyncpg" in url else url

def init_scheduler(database_url):
    global _scheduler
    _scheduler = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=_sync_db_url(database_url))},
        timezone="UTC",
    )
    return _scheduler

def get_scheduler():
    if _scheduler is None: raise RuntimeError("Планировщик не инициализирован")
    return _scheduler

def schedule_nudge(job_id, delay_sec, func_path, *, user_id, step):
    run_at = datetime.now(timezone.utc) + timedelta(seconds=delay_sec)
    get_scheduler().add_job(func=func_path, trigger="date", run_date=run_at,
        id=job_id, kwargs={"user_id": user_id, "step": step},
        replace_existing=True, misfire_grace_time=24*3600)

def cancel_nudge(job_id):
    try: get_scheduler().remove_job(job_id)
    except: pass

def nudge_job_id(user_id, step): return f"nudge:{user_id}:{step}"
