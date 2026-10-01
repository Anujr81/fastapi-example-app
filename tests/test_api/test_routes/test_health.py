import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from starlette import status

pytestmark = pytest.mark.asyncio


async def test_health_is_healthy_when_database_accepts_queries(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    response = await client.get(app.url_path_for("health:get"))

    assert app.url_path_for("health:get") == "/health"
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"]["status"] == "connected"
    assert body["database"]["latency_ms"] >= 0
    assert isinstance(body["version"], str)
    assert isinstance(body["environment"], str)
    assert body["uptime_seconds"] >= 0


async def test_health_is_unhealthy_when_database_check_fails(
    app: FastAPI,
    client: AsyncClient,
    initialized_app: FastAPI,
) -> None:
    class _BrokenConnection:
        async def fetchval(self, query: str) -> None:
            raise ConnectionError("database unavailable")

    class _FailingAcquire:
        async def __aenter__(self) -> "_BrokenConnection":
            return _BrokenConnection()

        async def __aexit__(self, *args: object) -> None:
            return None

    initialized_app.state.pool.acquire = lambda *args, **kwargs: _FailingAcquire()

    response = await client.get(app.url_path_for("health:get"))

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["database"]["status"] == "disconnected"
    assert "database unavailable" not in response.text


async def test_health_is_unhealthy_when_pool_is_missing(
    app: FastAPI,
    client: AsyncClient,
    initialized_app: FastAPI,
) -> None:
    pool = initialized_app.state.pool
    initialized_app.state.pool = None
    try:
        response = await client.get(app.url_path_for("health:get"))
    finally:
        initialized_app.state.pool = pool

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["database"]["status"] == "disconnected"
    assert body["database"]["latency_ms"] == 0
