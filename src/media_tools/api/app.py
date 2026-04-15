from contextlib import asynccontextmanager
from fastapi import FastAPI
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
    yield
    # Shutdown
    scheduler.shutdown_scheduler()


app = FastAPI(title="Media Tools API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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