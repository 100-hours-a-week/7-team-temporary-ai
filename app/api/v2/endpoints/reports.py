import time
from fastapi import APIRouter, BackgroundTasks
from app.models.report import WeeklyReportGenerateRequest, WeeklyReportGenerateResponse
from app.services.report.weekly_report_service import generate_batch_reports

router = APIRouter()

@router.post("/weekly", response_model=WeeklyReportGenerateResponse)
async def generate_weekly_report(request: WeeklyReportGenerateRequest, background_tasks: BackgroundTasks):
    """
    주간 레포트 생성 (Batch)
    
    - baseDate 기준 과거 4주 데이터를 조회하여 레포트 생성
    - 생성된 레포트는 DB(weekly_reports)에 저장
    """
    start_time = time.time()
    
    # BackgroundTasks를 통해 응답은 즉시 내보내고 레포트 생성은 백그라운드에서 진행
    background_tasks.add_task(generate_batch_reports, request)
    
    process_time = time.time() - start_time
    
    return WeeklyReportGenerateResponse(
        success=True,
        process_time=process_time,
        count=len(request.users),
        message=f"Batch report generation started for {len(request.users)} users in the background."
    )


from app.models.report import WeeklyReportFetchRequest, WeeklyReportFetchResponse
from app.services.report.weekly_report_service import fetch_weekly_reports

@router.post("/weekly/fetch", response_model=WeeklyReportFetchResponse)
async def fetch_weekly_report_data(request: WeeklyReportFetchRequest):
    """
    주간 레포트 데이터 조회 (배치)
    
    - 요청한 (userId, reportId) 리스트에 대해 저장된 레포트 반환
    - 데이터가 없거나 권한이 맞지 않는 경우 개별 요소로 상태(NOT_FOUND, FORBIDDEN 등) 반환
    """
    return await fetch_weekly_reports(request)
