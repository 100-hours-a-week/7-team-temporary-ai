import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, ANY
from datetime import date
from app.models.report import WeeklyReportGenerateRequest, WeeklyReportTarget
from app.services.report.weekly_report_service import generate_batch_reports

@pytest.fixture
def sample_request():
    return WeeklyReportGenerateRequest(
        baseDate=date(2026, 1, 12),
        users=[
            WeeklyReportTarget(reportId=1, userId=100)
        ]
    )

@pytest.mark.asyncio
@patch("app.services.report.weekly_report_service.ReportRepository")
@patch("app.services.report.weekly_report_service.get_gemini_client")
async def test_generate_batch_reports_success_v3(mock_get_gemini_client, mock_repo_class, sample_request):
    """
    정상 시나리오: gemini-3-flash-preview 모델이 첫 시도에 성공적으로 레포트를 생성하고 저장함.
    """
    # 1. Mock 설정
    mock_repo = mock_repo_class.return_value
    mock_repo.fetch_past_4_weeks_data = AsyncMock(return_value=[{"fill_rate": 0.5}])
    mock_repo.upsert_weekly_report = AsyncMock(return_value=True)
    
    mock_client = AsyncMock()
    mock_client.generate_text.return_value = "# 이번 주 요약\n정말 잘 하셨습니다!"
    mock_get_gemini_client.return_value = mock_client
    
    # 2. 실행
    await generate_batch_reports(sample_request)
    
    # 3. 검증
    mock_repo.fetch_past_4_weeks_data.assert_called_once()
    mock_client.generate_text.assert_called_once_with(
        system=ANY,
        user=ANY,
        model_name="gemini-3-flash-preview"
    )
    mock_repo.upsert_weekly_report.assert_called_once()

@pytest.mark.asyncio
@patch("app.services.report.weekly_report_service.ReportRepository")
@patch("app.services.report.weekly_report_service.get_gemini_client")
async def test_generate_batch_reports_fallback_v2(mock_get_gemini_client, mock_repo_class, sample_request):
    """
    무한 재시도 시나리오: gemini-3-flash-preview 가 4번 연속 실패 후, gemini-2.5-flash 가 2번째 시도(총 6번째)에서 성공함.
    """
    mock_repo = mock_repo_class.return_value
    mock_repo.fetch_past_4_weeks_data = AsyncMock(return_value=[])
    mock_repo.upsert_weekly_report = AsyncMock(return_value=True)
    
    mock_client = AsyncMock()
    
    # 4번 실패 (v3) -> 1번 실패 (v2) -> 1번 성공 (v2) 의 사이드 이펙트 
    class APIError(Exception):
        pass
        
    mock_client.generate_text.side_effect = [
        APIError("503 v3 Error 1"),
        APIError("503 v3 Error 2"),
        APIError("503 v3 Error 3"),
        APIError("503 v3 Error 4"),
        APIError("503 v2 Error 1"),
        "# 최종 성공된 마크다운 레포트"
    ]
    mock_get_gemini_client.return_value = mock_client
    
    # Time 가속을 원하면 asyncio.sleep을 패치해야 하므로 여기서 수동으로 sleep 속도 단축 패치
    with patch("app.services.report.weekly_report_service.asyncio.sleep", new_callable=AsyncMock):
        await generate_batch_reports(sample_request)
        
    # 총 generate_text는 6번 호출됨 (4번 v3 + 2번 v2)
    assert mock_client.generate_text.call_count == 6
    
    # 마지막 호출이 gemini-2.5-flash 인지 확인
    last_call_kwargs = mock_client.generate_text.call_args.kwargs
    assert last_call_kwargs["model_name"] == "gemini-2.5-flash"
    
    mock_repo.upsert_weekly_report.assert_called_once_with(
        report_id=1,
        user_id=100,
        base_date=sample_request.base_date,
        content="# 최종 성공된 마크다운 레포트"
    )

from app.models.report import WeeklyReportFetchRequest, WeeklyReportFetchResponse
from app.services.report.weekly_report_service import fetch_weekly_reports

@pytest.fixture
def sample_fetch_request():
    return WeeklyReportFetchRequest(
        targets=[
            WeeklyReportTarget(reportId=1, userId=100),
            WeeklyReportTarget(reportId=2, userId=200),
            WeeklyReportTarget(reportId=3, userId=100) # Invalid case: User 100 requesting Report 3 which belongs to 300
        ]
    )

@pytest.mark.asyncio
@patch("app.services.report.weekly_report_service.ReportRepository")
async def test_fetch_weekly_reports(mock_repo_class, sample_fetch_request):
    mock_repo = mock_repo_class.return_value
    # Report 1: Exists, matches user 100
    # Report 3: Exists, matches user 300
    # Report 2: Does not exist
    mock_repo.fetch_reports_by_targets = AsyncMock(return_value=[
        {"report_id": 1, "user_id": 100, "content": "Report 1 content"},
        {"report_id": 3, "user_id": 300, "content": "Report 3 content"},
    ])
    
    response = await fetch_weekly_reports(sample_fetch_request)
    
    assert response.success is True
    assert len(response.results) == 3
    
    # Validation
    res_1 = next(r for r in response.results if r.report_id == 1)
    assert res_1.status == "SUCCESS"
    assert res_1.content == "Report 1 content"
    
    res_2 = next(r for r in response.results if r.report_id == 2)
    assert res_2.status == "NOT_FOUND"
    assert res_2.content is None
    
    res_3 = next(r for r in response.results if r.report_id == 3)
    assert res_3.status == "FORBIDDEN"
    assert res_3.content is None
