from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_get_sensors_empty():
    r = client.get("/api/sensors")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_anomalies_empty():
    r = client.get("/api/anomalies")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
