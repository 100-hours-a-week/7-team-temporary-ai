from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ingest_personalization_data():
    # Given
    payload = {
        "userIds": [1, 2, 3],
        "targetDate": "2026-02-08"
    }

    # When
    response = client.post("/ai/v1/personalizations/ingest", json=payload)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["userIds"] == [1, 2, 3]
    assert data["message"] == "Ingest triggered successfully"
    assert "processTime" in data

def test_ingest_personalization_data_invalid_request():
    # Given: Missing userIds
    payload = {
        "targetDate": "2026-02-08"
    }

    # When
    response = client.post("/ai/v1/personalizations/ingest", json=payload)

    # Then
    assert response.status_code == 422
