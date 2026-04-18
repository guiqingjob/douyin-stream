from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from media_tools.api.routers import creators, assets, tasks, settings, douyin, scheduler
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure DB schema is up to date (adds new columns to existing tables)
    from media_tools.douyin.core.config_mgr import get_config
    from media_tools.db.core import init_db
    init_db(get_config().get_db_path())

    scheduler.startup_scheduler()

    # Kick off the transcript preview backfill in the background
    from media_tools.pipeline.preview_backfill import start_backfill_once
    start_backfill_once()

    yield
    # Shutdown
    scheduler.shutdown_scheduler()


app = FastAPI(title="Media Tools API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Optional API key authentication middleware."""
    from media_tools.douyin.core.config_mgr import get_config

    config = get_config()
    api_key = config.get_api_key()

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

app.include_router(creators.router)
app.include_router(assets.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(douyin.router)
app.include_router(scheduler.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
