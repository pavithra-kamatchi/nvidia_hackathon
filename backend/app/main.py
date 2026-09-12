import asyncio
import json
import urllib.request

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import close_database, ensure_indexes, get_database
from app.routers import assignments, handoff, images, incidents, ingest, logs, stations
from app.seed import seed_default_stations

app = FastAPI(title="Drone-Based Emergency Coordination System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-Operator-ID"],
)

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
    await seed_default_stations()


@app.on_event("shutdown")
async def on_shutdown():
    close_database()


@app.get("/health")
async def health():
    return {"status": "ok"}


def _nemotron_ready() -> bool:
    models_url = settings.nemotron_url.rsplit("/chat/completions", 1)[0] + "/models"
    with urllib.request.urlopen(models_url, timeout=3) as response:
        payload = json.load(response)
    return any(model.get("id") == settings.nemotron_model for model in payload.get("data", []))


@app.get("/readiness")
async def readiness():
    services = {"mongodb": False, "nemotron": False}
    try:
        await get_database().command("ping")
        services["mongodb"] = True
    except Exception:
        pass
    try:
        services["nemotron"] = await asyncio.to_thread(_nemotron_ready)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        pass
    return {
        "status": "ready" if all(services.values()) else "degraded",
        "services": services,
    }
