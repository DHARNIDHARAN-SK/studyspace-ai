import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.errors import AppError


@pytest.mark.asyncio
async def test_root_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "environment" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_v1_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "environment" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_app_error_structure():
    # Dynamically mount a temporary test route to verify AppError handling
    @app.get("/test-error")
    async def trigger_app_error():
        raise AppError(
            code="TEST_ERROR",
            message="A test error occurred.",
            status_code=400,
            action="Fix test input.",
            details={"field": "test"}
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/test-error")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "TEST_ERROR"
        assert data["error"]["message"] == "A test error occurred."
        assert data["error"]["action"] == "Fix test input."
        assert data["error"]["details"] == {"field": "test"}
