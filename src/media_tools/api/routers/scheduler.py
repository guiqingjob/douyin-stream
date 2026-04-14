import sqlite3
import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from media_tools.db.core import get_db_connection

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()

class ScheduleRequest(BaseModel):
    cron_expr: str  # e.g., "0 2 * * *" for 02:00 daily
    enabled: bool = True

class ToggleRequest(BaseModel):
    enabled: bool

def _run_scan_all_following():
    """The actual job executed by the scheduler"""
    logger.info("Running scheduled task: full sync all following")
    try:
        from media_tools.douyin.core.downloader import download_all
        download_all(auto_confirm=True)
        logger.info("Scheduled task 'full sync all following' completed successfully.")
    except Exception as e:
        logger.error(f"Scheduled task 'full sync all following' failed: {e}")

def _sync_scheduler():
    """Sync jobs in DB with APScheduler"""
    scheduler.remove_all_jobs()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, task_type, cron_expr, enabled FROM scheduled_tasks WHERE enabled=1")
        tasks = cursor.fetchall()

    for task in tasks:
        task_id, task_type, cron_expr, enabled = task
        if task_type == "scan_all_following":
            try:
                trigger = CronTrigger.from_crontab(cron_expr)
                scheduler.add_job(
                    _run_scan_all_following,
                    trigger=trigger,
                    id=task_id,
                    replace_existing=True
                )
            except Exception as e:
                logger.error(f"Failed to schedule task {task_id} with cron '{cron_expr}': {e}")

def startup_scheduler():
    """Called from app lifespan to sync scheduled tasks on startup."""
    _sync_scheduler()
    # Register periodic stale task cleanup (every 10 minutes)
    from media_tools.api.routers.tasks import cleanup_stale_tasks
    def _cleanup_job():
        try:
            with get_db_connection() as conn:
                cleanup_stale_tasks(conn)
        except Exception as e:
            logger.error(f"Stale task cleanup failed: {e}")
    scheduler.add_job(
        _cleanup_job,
        trigger="interval",
        minutes=10,
        id="__stale_task_cleanup__",
        replace_existing=True,
    )

def shutdown_scheduler():
    """Called from app lifespan to shut down APScheduler."""
    if scheduler.running:
        scheduler.shutdown()

@router.get("/")
def list_schedules():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, task_type, cron_expr, enabled, update_time FROM scheduled_tasks")
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "task_id": row[0],
                "task_type": row[1],
                "cron_expr": row[2],
                "enabled": bool(row[3]),
                "update_time": row[4]
            })
    return tasks

@router.post("/")
def add_schedule(req: ScheduleRequest):
    task_id = str(uuid.uuid4())
    with get_db_connection() as conn:
        try:
            conn.execute(
                "INSERT INTO scheduled_tasks (task_id, task_type, cron_expr, enabled) VALUES (?, ?, ?, ?)",
                (task_id, "scan_all_following", req.cron_expr, req.enabled)
            )
            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    _sync_scheduler()
    return {"status": "success", "task_id": task_id}

@router.put("/{task_id}/toggle")
def toggle_schedule(task_id: str, req: ToggleRequest):
    with get_db_connection() as conn:
        try:
            conn.execute(
                "UPDATE scheduled_tasks SET enabled = ?, update_time = CURRENT_TIMESTAMP WHERE task_id = ?",
                (req.enabled, task_id)
            )
            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    _sync_scheduler()
    return {"status": "success"}

@router.delete("/{task_id}")
def delete_schedule(task_id: str):
    with get_db_connection() as conn:
        try:
            conn.execute("DELETE FROM scheduled_tasks WHERE task_id = ?", (task_id,))
            conn.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    _sync_scheduler()
    return {"status": "success"}

@router.post("/run_now")
def run_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_scan_all_following)
    return {"status": "success", "message": "Task triggered in background"}
