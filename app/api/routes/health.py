import time
from typing import Literal, Optional

from asyncpg.pool import Pool
from fastapi import APIRouter, Depends, Response
from loguru import logger
from pydantic import BaseModel
from starlette import status
from starlette.requests import Request

from app.core.config import get_app_settings

router = APIRouter()

_process_started_at = time.time()


class DatabaseHealth(BaseModel):
    status: Literal["connected", "disconnected"]
    latency_ms: float


class HealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    version: str
    environment: str
    uptime_seconds: float
    database: DatabaseHealth


def _pool_from_state(request: Request) -> Optional[Pool]:
    return getattr(request.app.state, "pool", None)


def _database_health(
    db_status: Literal["connected", "disconnected"],
    started_at: float,
) -> DatabaseHealth:
    elapsed_ms = (time.monotonic() - started_at) * 1000
    return DatabaseHealth(status=db_status, latency_ms=round(elapsed_ms, 2))


async def _probe_database(pool: Pool) -> DatabaseHealth:
    started_at = time.monotonic()
    try:
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
    except Exception:
        logger.exception("Database health check failed")
        return _database_health("disconnected", started_at)

    return _database_health("connected", started_at)


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
    name="health:get",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse},
    },
)
async def health_check(
    response: Response,
    pool: Optional[Pool] = Depends(_pool_from_state),
) -> HealthResponse:
    settings = get_app_settings()
    if pool is None:
        database = DatabaseHealth(status="disconnected", latency_ms=0)
    else:
        database = await _probe_database(pool)

    is_healthy = database.status == "connected"
    response.status_code = (
        status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return HealthResponse(
        status="healthy" if is_healthy else "unhealthy",
        version=settings.version,
        environment=settings.app_env.value,
        uptime_seconds=round(time.time() - _process_started_at, 2),
        database=database,
    )
