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
