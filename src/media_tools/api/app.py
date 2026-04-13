from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from media_tools.api.routers import creators, assets

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

@app.get("/api/health")
def health_check():
    return {"status": "ok"}