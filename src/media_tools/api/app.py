from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from media_tools.api.routers import creators, assets, tasks, settings, douyin
import uvicorn

app = FastAPI(title="Media Tools API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(creators.router)
app.include_router(assets.router)
app.include_router(tasks.router)
app.include_router(settings.router)
app.include_router(douyin.router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)