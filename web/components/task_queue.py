"""
后台任务队列组件 - 基于状态文件的轮询机制

工作原理:
1. 用户提交任务 → 写入 task_state.json
2. 后台线程/子进程执行任务，定时更新状态文件
3. 前端页面每 2 秒读取状态文件，显示进度
"""

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable
from datetime import datetime

# 状态文件路径
_STATE_FILE = Path(".task_state.json")

# 线程锁，防止并发读写状态文件时的竞态条件
_state_lock = threading.Lock()


def _get_state_file() -> Path:
    """获取状态文件路径"""
    return Path(__file__).parent.parent / _STATE_FILE


def create_task(
    task_id: str,
    task_type: str,
    description: str = "",
) -> dict:
    """创建新任务状态"""
    return {
        "task_id": task_id,
        "task_type": task_type,
        "description": description,
        "status": "pending",  # pending/running/success/failed
        "progress": 0.0,  # 0.0 - 1.0
        "message": "等待执行",
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def save_task_state(task_state: dict) -> None:
    """保存任务状态到文件（线程安全）"""
    task_state["updated_at"] = datetime.now().isoformat()
    state_file = _get_state_file()
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(task_state, f, ensure_ascii=False, indent=2)


def load_task_state() -> dict | None:
    """读取当前任务状态（线程安全）"""
    state_file = _get_state_file()
    if not state_file.exists():
        return None
    try:
        with _state_lock:
            with open(state_file, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
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
    save_task_state(state)


def mark_task_failed(error: str) -> None:
    """标记任务失败"""
    state = load_task_state()
    if state is None:
        return
    state["status"] = "failed"
    state["message"] = f"错误: {error}"
    state["error"] = error
    save_task_state(state)


def clear_task_state() -> None:
    """清除任务状态"""
    state_file = _get_state_file()
    if state_file.exists():
        state_file.unlink()


def run_task_in_background(
    task_func: Callable,
    task_id: str,
    task_type: str,
    description: str = "",
    *args,
    **kwargs,
) -> None:
    """在后台线程中执行任务"""
    # 初始化任务状态
    initial_state = create_task(task_id, task_type, description)
    save_task_state(initial_state)

    def _worker():
        try:
            update_task_progress(0.0, "任务开始执行")
            result = task_func(*args, **kwargs)
            mark_task_success(result, "任务完成")
        except Exception as e:
            mark_task_failed(str(e))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
