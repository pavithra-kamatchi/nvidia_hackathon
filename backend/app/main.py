from fastapi import FastAPI

from app.db import close_database, ensure_indexes
from app.routers import assignments, handoff, images, incidents, ingest, logs, stations

app = FastAPI(title="Drone-Based Emergency Coordination System")

app.include_router(ingest.router)
app.include_router(images.router)
app.include_router(stations.router)
app.include_router(incidents.router)
app.include_router(assignments.router)
app.include_router(logs.router)
app.include_router(handoff.router)


@app.on_event("startup")
async def on_startup():
    await ensure_indexes()


@app.on_event("shutdown")
async def on_shutdown():
    close_database()


@app.get("/health")
async def health():
    return {"status": "ok"}
