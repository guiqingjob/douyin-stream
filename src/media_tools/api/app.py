from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from media_tools.api.routers import creators, assets, tasks, settings, douyin, scheduler
from media_tools.core.exceptions import AppError
import uvicorn
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB schema is up to date (adds new columns to existing tables)
    from media_tools.common.paths import get_db_path
    from media_tools.db.core import init_db
    init_db(get_db_path())

    scheduler.startup_scheduler()

    # Kick off the transcript preview backfill in the background
    from media_tools.pipeline.preview_backfill import start_backfill_once
    start_backfill_once()

    # 启动时清理孤儿任务：服务重启后内存中的后台任务全部丢失，
    # 数据库里残留的 RUNNING/PENDING 任务实际上已经无人执行。
    from media_tools.db.core import get_db_connection
    import sqlite3
    from datetime import datetime
    try:
        with get_db_connection() as conn:
            now = datetime.now().isoformat()
            cursor = conn.execute(
                """UPDATE task_queue
                   SET status='FAILED',
                       error_msg='服务重启导致任务中断，请重新发起',
                       update_time=?
                   WHERE status IN ('PENDING', 'RUNNING')""",
                (now,),
            )
            orphaned = cursor.rowcount
            conn.commit()
            if orphaned > 0:
                print(f"[startup] 已清理 {orphaned} 个孤儿任务（服务重启残留）")
    except (sqlite3.Error, OSError) as e:
        print(f"[startup] 清理孤儿任务失败: {e}")

    yield
    # Shutdown
    scheduler.shutdown_scheduler()


app = FastAPI(title="Media Tools API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Optional API key authentication middleware."""
    from media_tools.core.config import get_runtime_setting

    api_key = get_runtime_setting("api_key", "")

    # Skip auth if no API key is configured
    if not api_key:
        return await call_next(request)

    # Skip auth for health check and WebSocket
    if request.url.path in ("/api/health", "/api/v1/tasks/ws") or request.url.path.startswith("/docs"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]  # Remove "Bearer " prefix
    if token != api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """处理应用自定义异常 - 返回结构化错误"""
    logger.warning(f"AppError: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理 HTTP 异常 - 统一格式"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {},
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """处理未捕获异常 - 不暴露内部信息"""
    logger.exception(f"Unhandled exception at {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "details": {},
        },
    )


app.include_router(creators.router)
app.include_router(assets.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(douyin.router)
app.include_router(scheduler.router)

import shutil

from media_tools.db.core import get_db_connection
from media_tools.repositories.task_repository import TaskRepository


@app.get("/api/health")
def health_check():
    result = {"status": "ok"}

    # DB 连接状态
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {e}"
        result["status"] = "degraded"

    # 磁盘空间
    try:
        stat = shutil.disk_usage(".")
        result["disk"] = {
            "total_gb": round(stat.total / (1024**3), 2),
            "free_gb": round(stat.free / (1024**3), 2),
            "used_percent": round((stat.used / stat.total) * 100, 1),
        }
    except OSError as e:
        result["disk"] = f"error: {e}"

    # 活跃任务数
    try:
        active = TaskRepository.find_active()
        result["active_tasks"] = len(active)
    except Exception as e:
        result["active_tasks"] = f"error: {e}"

    return result

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
