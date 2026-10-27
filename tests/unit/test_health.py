import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from doctorly.db.session import get_session
from doctorly.main import app


async def _request(method: str, path: str, headers: dict[str, str] | None = None):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, headers=headers)


def test_health_reports_liveness() -> None:
    response = asyncio.run(_request("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_allows_the_configured_frontend_origin() -> None:
    response = asyncio.run(
        _request(
            "OPTIONS",
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_readiness_checks_the_database() -> None:
    class SessionStub:
        def execute(self, statement):
            assert str(statement) == "SELECT 1"

    app.dependency_overrides[get_session] = SessionStub
    try:
        response = asyncio.run(_request("GET", "/health/ready"))
    finally:
        app.dependency_overrides.pop(get_session)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_database_failure() -> None:
    class SessionStub:
        def execute(self, statement):
            raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    app.dependency_overrides[get_session] = SessionStub
    try:
        response = asyncio.run(_request("GET", "/health/ready"))
    finally:
        app.dependency_overrides.pop(get_session)

    assert response.status_code == 503
    assert response.json() == {
        "detail": {"status": "unavailable", "dependency": "database"}
    }
