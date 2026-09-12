from fastapi import FastAPI

from app.db import ensure_indexes
from app.routers import assignments, images, incidents, ingest, logs, stations

app = FastAPI(title="Drone-Based Emergency Coordination System")

app.include_router(ingest.router)
app.include_router(images.router)
app.include_router(stations.router)
app.include_router(incidents.router)
app.include_router(assignments.router)
app.include_router(logs.router)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()


@app.get("/health")
async def health():
    return {"status": "ok"}
