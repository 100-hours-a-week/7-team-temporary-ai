import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.mcp.server import search_schedules_by_date

@pytest.mark.asyncio
async def test_search_schedules_by_date_success():
    """정상적으로 데이터를 조회하고 마크다운을 생성하는지 테스트"""
    mock_planner_data = [
        {
            "id": 166,
            "start_arrange": "07:00",
            "day_end_time": "23:30",
            "focus_time_zone": "Morning",
            "plan_date": "2026-02-15"
        }
    ]
    mock_tasks_data = [
        {
            "record_id": 166,
            "title": "재무회계 인강",
            "status": "DONE",
            "is_urgent": False,
            "focus_level": 8,
            "start_at": "08:00",
            "end_at": "11:00"
        }
    ]

    # Supabase 클라이언트 Mocking
    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # 1. planner_records Mocking
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = \
            MagicMock(data=mock_planner_data)
        
        # 2. record_tasks Mocking
        mock_client.table.return_value.select.return_value.in_.return_value.eq.return_value.execute.return_value = \
            MagicMock(data=mock_tasks_data)

        result = await search_schedules_by_date(user_id=777777, start_date="2026-02-15")

        assert "일정 검색 결과" in result
        assert "2026-02-15" in result
        assert "재무회계 인강" in result
        assert "✅" in result  # DONE status emoji

@pytest.mark.asyncio
async def test_search_schedules_by_date_no_records():
    """기록이 없을 때 적절한 메시지를 반환하는지 테스트"""
    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # planner_records 빈 리스트 반환
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.gte.return_value.lte.return_value.execute.return_value = \
            MagicMock(data=[])

        result = await search_schedules_by_date(user_id=777777, start_date="2026-02-15")

        assert "플래너 기록이 없습니다" in result

@pytest.mark.asyncio
async def test_search_schedules_by_date_db_error():
    """DB 오류 발생 시 에러 메시지를 반환하는지 테스트"""
    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # 예외 발생
        mock_client.table.return_value.select.side_effect = Exception("Connection error")

        result = await search_schedules_by_date(user_id=777777, start_date="2026-02-15")

        assert "오류가 발생했습니다" in result
        assert "Connection error" in result
