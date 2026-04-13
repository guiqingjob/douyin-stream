"""
后台任务队列组件 - 基于 SQLite 的多任务队列机制

当前能力：
1. 页面提交任务 → 写入 media_tools.db (task_queue)
2. 后台线程执行任务，更新数据库状态
3. 前端页面轮询数据库，显示当前任务与历史记录
"""

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Callable

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger

logger = get_logger('web')

# 任务取消标志（暂保留用于简单的全局单任务取消，若要细化需按 task_id）
_cancel_flag = threading.Event()

def _get_db_path():
    return get_config().get_db_path()

def create_task(
    task_id: str,
    task_type: str,
    description: str = "",
) -> dict:
    """创建新任务状态"""
    now = datetime.now().isoformat()
    return {
        "task_id": task_id,
        "task_type": task_type,
        "description": description,
        "status": "pending",
        "progress": 0.0,
        "message": "等待执行",
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }

def save_task_state(task_state: dict) -> None:
    """保存任务状态到数据库"""
    task_state["updated_at"] = datetime.now().isoformat()
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            
            # 由于 payload 可能是任意复杂结构，提取需要存入 json 字段的数据
            payload = {
                "description": task_state.get("description", ""),
                "message": task_state.get("message", ""),
                "result": task_state.get("result"),
                "error": task_state.get("error"),
                "completed_at": task_state.get("completed_at")
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO task_queue 
                (task_id, task_type, payload, status, progress, error_msg, create_time, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_state["task_id"],
                task_state["task_type"],
                json.dumps(payload, ensure_ascii=False),
                task_state["status"].upper(),
                task_state.get("progress", 0.0),
                task_state.get("error", ""),
                task_state.get("created_at"),
                task_state["updated_at"]
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"保存任务状态失败: {e}")

def load_task_state() -> dict | None:
    """读取当前（最新）任务状态"""
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            # 优先获取正在运行或等待的任务，如果没有，取最新的一个
            cursor.execute('''
                SELECT task_id, task_type, payload, status, progress, error_msg, create_time, update_time
                FROM task_queue
                ORDER BY 
                    CASE WHEN status IN ('PENDING', 'RUNNING') THEN 0 ELSE 1 END,
                    update_time DESC
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if not row:
                return None
                
            payload = {}
            if row[2]:
                try:
                    payload = json.loads(row[2])
                except:
                    pass
                    
            return {
                "task_id": row[0],
                "task_type": row[1],
                "description": payload.get("description", ""),
                "status": row[3].lower(),
                "progress": row[4],
                "message": payload.get("message", ""),
                "result": payload.get("result"),
                "error": row[5] or payload.get("error"),
                "created_at": row[6],
                "updated_at": row[7],
                "completed_at": payload.get("completed_at")
            }
    except Exception as e:
        logger.error(f"读取任务状态失败: {e}")
        return None

def update_task_progress(
    progress: float,
    message: str = "",
    status: str = "running",
) -> None:
    """更新任务进度"""
    state = load_task_state()
    if state is None:
        return
    state["progress"] = min(max(progress, 0.0), 1.0)
    state["status"] = status
    if message:
        state["message"] = message
    save_task_state(state)

def mark_task_success(result: Any = None, message: str = "任务完成") -> None:
    """标记任务成功"""
    state = load_task_state()
    if state is None:
        return
    state["status"] = "success"
    state["progress"] = 1.0
    state["message"] = message
    state["result"] = result
    state["completed_at"] = datetime.now().isoformat()
    save_task_state(state)

def mark_task_failed(error: str) -> None:
    """标记任务失败"""
    state = load_task_state()
    if state is None:
        return
    state["status"] = "failed"
    state["message"] = f"错误: {error}"
    state["error"] = error
    state["completed_at"] = datetime.now().isoformat()
    save_task_state(state)

def clear_task_state() -> None:
    """清除当前活动任务状态（在 DB 中，可以将其标记为 CANCELLED）"""
    state = load_task_state()
    if state and state["status"] in ("pending", "running"):
        state["status"] = "cancelled"
        save_task_state(state)

def cancel_task() -> None:
    """取消当前任务"""
    _cancel_flag.set()
    clear_task_state()

def is_task_cancelled() -> bool:
    """检查是否取消"""
    return _cancel_flag.is_set()

def reset_cancel_flag() -> None:
    """重置取消标志"""
    _cancel_flag.clear()

def run_task_in_background(
    task_func: Callable,
    task_id: str,
    task_type: str,
    description: str = "",
    success_message: str = "任务完成",
    *args,
    **kwargs,
) -> None:
    """在后台线程中执行任务"""
    reset_cancel_flag()
    initial_state = create_task(task_id, task_type, description)
    save_task_state(initial_state)

    def _worker():
        try:
            update_task_progress(0.0, "任务开始执行")

            if is_task_cancelled():
                mark_task_failed("任务已取消")
                return

            result = task_func(*args, **kwargs)

            current_state = load_task_state()
            if current_state and current_state.get("status") in {"success", "failed", "cancelled"}:
                return

            if is_task_cancelled():
                mark_task_failed("任务已取消")
                return

            mark_task_success(result, success_message)
        except Exception as e:
            logger.exception('发生异常')
            current_state = load_task_state()
            if current_state and current_state.get("status") in {"success", "failed", "cancelled"}:
                return

            if is_task_cancelled():
                mark_task_failed("任务已取消")
            else:
                mark_task_failed(str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

def load_task_history(limit: int = 10) -> list[dict]:
    """加载任务历史记录"""
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_id, task_type, payload, status, progress, error_msg, create_time, update_time
                FROM task_queue
                ORDER BY update_time DESC
                LIMIT ?
            ''', (limit,))
            
            history = []
            for row in cursor.fetchall():
                payload = {}
                if row[2]:
                    try:
                        payload = json.loads(row[2])
                    except:
                        pass
                history.append({
                    "task_id": row[0],
                    "task_type": row[1],
                    "description": payload.get("description", ""),
                    "status": row[3].lower(),
                    "progress": row[4],
                    "message": payload.get("message", ""),
                    "result": payload.get("result"),
                    "error": row[5] or payload.get("error"),
                    "created_at": row[6],
                    "updated_at": row[7],
                    "completed_at": payload.get("completed_at")
                })
            return history
    except Exception as e:
        logger.error(f"读取任务历史失败: {e}")
        return []
