from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ingest_personalization_data():
    """정상 요청 시 200 응답 및 결과 반환"""
    # 엔드포인트 모듈에서 이미 생성된 service 인스턴스의 repository를 패치
    with patch(
        "app.api.v1.endpoints.personalization.service.repository"
    ) as mock_repo:
        mock_repo.fetch_draft_final_pairs = AsyncMock(return_value=[])

        payload = {
            "userIds": [1, 2, 3],
            "targetDate": "2026-02-08"
        }

        response = client.post("/ai/v1/personalizations/ingest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["userIds"] == [1, 2, 3]
        assert "processTime" in data


def test_ingest_personalization_data_invalid_request():
    """필수 필드 누락 시 422 응답"""
    payload = {
        "targetDate": "2026-02-08"
    }

    response = client.post("/ai/v1/personalizations/ingest", json=payload)

    assert response.status_code == 422
