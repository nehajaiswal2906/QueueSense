
import pytest

from backend.app import app
from backend.intelligence import (
    calculate_waiting_time,
    get_queue_status,
    format_queue_result,
)


@pytest.fixture
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_mock_endpoint(client):
    response = client.get("/mock")
    data = response.get_json()

    assert response.status_code == 200
    assert data["queue_count"] == 8
    assert data["service_rate"] == 2.0
    assert data["estimated_wait"] == 4.0
    assert data["status"] == "high"
    assert "message" in data


def test_analyze_valid_input(client):
    response = client.post(
        "/analyze",
        json={"queue_count": 8, "service_rate": 2.0},
    )

    data = response.get_json()

    assert response.status_code == 200
    assert data["estimated_wait"] == 4.0
    assert data["status"] == "high"


def test_analyze_negative_queue(client):
    response = client.post(
        "/analyze",
        json={"queue_count": -1, "service_rate": 2.0},
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_analyze_zero_service_rate(client):
    response = client.post(
        "/analyze",
        json={"queue_count": 8, "service_rate": 0},
    )

    assert response.status_code == 400


def test_analyze_missing_field(client):
    response = client.post(
        "/analyze",
        json={"queue_count": 8},
    )

    assert response.status_code == 400


def test_analyze_rejects_boolean_queue_count(client):
    response = client.post(
        "/analyze",
        json={"queue_count": True, "service_rate": 2.0},
    )

    assert response.status_code == 400


def test_upload_rejects_unsupported_file(client):
    response = client.post(
        "/upload",
        data={"file": (b"not a video", "notes.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_waiting_time_calculation():
    assert calculate_waiting_time(8, 2.0) == 4.0
    assert calculate_waiting_time(8, None) is None
    assert calculate_waiting_time(8, 0) is None
    assert calculate_waiting_time(-1, 2.0) is None


def test_queue_status():
    assert get_queue_status(2) == "low"
    assert get_queue_status(5) == "moderate"
    assert get_queue_status(8) == "high"
    assert get_queue_status(-1) == "unknown"


def test_readable_result():
    result = format_queue_result(8, 2.0)

    assert result["estimated_wait"] == 4.0
    assert result["status"] == "high"
    assert "4.0 minutes" in result["message"]