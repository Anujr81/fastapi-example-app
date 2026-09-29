import time
from typing import Literal

from asyncpg.pool import Pool
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.database import _get_db_pool
from app.core.config import get_app_settings

router = APIRouter()

_start_time = time.time()


class DatabaseHealth(BaseModel):
    status: Literal["connected", "disconnected"]
    latency_ms: float


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    version: str
    environment: str
    uptime_seconds: float
    database: DatabaseHealth


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(
    pool: Pool = Depends(_get_db_pool),
) -> HealthResponse:
    settings = get_app_settings()

    t0 = time.monotonic()
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        latency_ms = (time.monotonic() - t0) * 1000
        db_health = DatabaseHealth(status="connected", latency_ms=round(latency_ms, 2))
    except Exception:
        latency_ms = (time.monotonic() - t0) * 1000
        db_health = DatabaseHealth(status="disconnected", latency_ms=round(latency_ms, 2))

    return HealthResponse(
        status="healthy" if db_health.status == "connected" else "unhealthy",
        version=settings.version,
        environment=settings.app_env.value,
        uptime_seconds=round(time.time() - _start_time, 2),
        database=db_health,
    )
