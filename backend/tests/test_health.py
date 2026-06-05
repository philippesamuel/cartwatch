import httpx
from fastapi.testclient import TestClient
from pytest import fixture

from main import app

client = TestClient(app)


@fixture
def health_response() -> httpx.Response:
    return client.get("/health")


def test_health_returns_ok(health_response: httpx.Response) -> None:
    response = health_response
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_returns_version(health_response: httpx.Response) -> None:
    response = health_response
    assert "version" in response.json()
