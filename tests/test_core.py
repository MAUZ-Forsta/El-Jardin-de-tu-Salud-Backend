from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health():
    settings = Settings(
        _env_file=None,
        app_env="test",
    )

    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allowed_origin():
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=["http://localhost:5173"],
    )

    client = TestClient(create_app(settings))

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )


def test_cors_disallowed_origin():
    settings = Settings(
        _env_file=None,
        app_env="test",
        cors_origins=["http://localhost:5173"],
    )

    client = TestClient(create_app(settings))

    response = client.options(
        "/health",
        headers={
            "Origin": "https://not-allowed.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_not_found_error():
    settings = Settings(
        _env_file=None,
        app_env="test",
    )

    client = TestClient(create_app(settings))

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"