from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import uuid
import sqlite3
from datetime import datetime
from media_tools.pipeline.worker import run_pipeline_for_user
from media_tools.douyin.core.config_mgr import get_config

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

class PipelineRequest(BaseModel):
    url: str
    max_counts: int = 5
    auto_delete: bool = True

def get_db_connection():
    return sqlite3.connect(get_config().get_db_path())

def update_task_progress(task_id: str, progress: float, msg: str):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO task_queue (task_id, task_type, status, progress, payload, update_time) VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, "pipeline", "RUNNING", progress, f'{{"msg": "{msg}"}}', datetime.now().isoformat())
            )
    except Exception as e:
        print(f"Error updating task: {e}")

def _background_pipeline_worker(task_id: str, req: PipelineRequest):
    try:
        result = run_pipeline_for_user(
            url=req.url, 
            max_counts=req.max_counts, 
            update_progress_fn=lambda p, m: update_task_progress(task_id, p, m),
            delete_after=req.auto_delete
        )
        msg = "成功转写完成"
        if result:
            s_count = result.get("success_count", 0)
            f_count = result.get("failed_count", 0)
            if s_count == 0 and f_count == 0:
                msg = "未找到新视频或链接无效"
            else:
                msg = f"成功转写 {s_count} 个视频，失败 {f_count} 个"
                
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (f'{{"msg": "{msg}"}}', task_id))
    except Exception as e:
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))

@router.post("/pipeline")
def trigger_pipeline(req: PipelineRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    update_task_progress(task_id, 0.0, "Initializing pipeline...")
    background_tasks.add_task(_background_pipeline_worker, task_id, req)
    return {"task_id": task_id, "status": "started"}

@router.get("/active")
def get_active_tasks():
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM task_queue WHERE status IN ('PENDING', 'RUNNING')")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []

@router.get("/{task_id}")
def get_task_status(task_id: str):
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM task_queue WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"status": "NOT_FOUND"}
    except Exception:
        return {"status": "ERROR"}