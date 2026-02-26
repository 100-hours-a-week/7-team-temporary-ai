import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.mcp.server import search_schedules_by_date, search_tasks_by_similarity

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

@pytest.mark.asyncio
async def test_search_tasks_by_similarity_success():
    """정상적으로 RPC를 호출하여 유사한 태스크 데이터를 조회하고 마크다운을 생성하는지 테스트"""
    mock_rpc_data = [
        {
            "id": 101,
            "record_id": 166,
            "title": "운동 및 다이어트",
            "status": "DONE",
            "focus_level": 7,
            "is_urgent": False,
            "category": "운동",
            "start_at": "19:00",
            "end_at": "20:00",
            "plan_date": "2026-02-15",
            "focus_time_zone": "Evening",
            "similarity": 0.85
        }
    ]

    # 임의의 768차원 임베딩 벡터 생성
    mock_embedding = [0.1] * 768

    # Supabase 클라이언트 Mocking
    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # rpc 메서드 체이닝 Mocking
        mock_rpc_call = MagicMock()
        mock_client.rpc.return_value = mock_rpc_call
        mock_rpc_call.execute.return_value = MagicMock(data=mock_rpc_data)

        result = await search_tasks_by_similarity(user_id=777777, embedding_vector=mock_embedding, top_k=5)

        # 파라미터가 올바르게 전달되었는지 확인
        mock_client.rpc.assert_called_once()
        args, kwargs = mock_client.rpc.call_args
        assert args[0] == "match_record_tasks"
        assert args[1]["p_user_id"] == 777777
        assert args[1]["match_count"] == 5

        # 출력 내용 확인
        assert "의미 체계 기반(Semantic) 유사 스케줄 검색 결과" in result
        assert "운동 및 다이어트" in result
        assert "2026-02-15" in result
        assert "✅" in result  # DONE status emoji
        assert "0.850" in result  # 유사도 형식

@pytest.mark.asyncio
async def test_search_tasks_by_similarity_no_records():
    """유사한 태스크 기록이 없을 때 적절한 메시지를 반환하는지 테스트"""
    mock_embedding = [0.1] * 768

    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # RPC 실행이 빈 리스트 반환
        mock_rpc_call = MagicMock()
        mock_client.rpc.return_value = mock_rpc_call
        mock_rpc_call.execute.return_value = MagicMock(data=[])

        result = await search_tasks_by_similarity(user_id=777777, embedding_vector=mock_embedding)

        assert "유사한 태스크를 찾을 수 없습니다" in result

@pytest.mark.asyncio
async def test_search_tasks_by_similarity_db_error():
    """DB 오류 발생 시(RPC 에러 등) 에러 메시지를 반환하는지 테스트"""
    mock_embedding = [0.1] * 768

    with patch("app.mcp.server.get_supabase_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # rpc 호출 시 예외 발생
        mock_client.rpc.side_effect = Exception("RPC Execution Failed")

        result = await search_tasks_by_similarity(user_id=777777, embedding_vector=mock_embedding)

        assert "오류가 발생했습니다" in result
        assert "RPC Execution Failed" in result
