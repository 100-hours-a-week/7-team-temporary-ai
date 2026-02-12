import time
from fastapi import APIRouter
from app.models.report import WeeklyReportGenerateRequest, WeeklyReportGenerateResponse

router = APIRouter()

@router.post("/weekly", response_model=WeeklyReportGenerateResponse)
async def generate_weekly_report(request: WeeklyReportGenerateRequest):
    """
    주간 레포트 생성 (Batch)
    
    - baseDate 기준 과거 4주 데이터를 조회하여 레포트 생성
    - 생성된 레포트는 DB(weekly_reports)에 저장
    """
    start_time = time.time()
    
    # TODO: Implement actual logic (fetch data -> generate report -> save to DB)
    
    process_time = time.time() - start_time
    
    return WeeklyReportGenerateResponse(
        success=True,
        process_time=process_time,
        count=len(request.users),
        message=f"Batch report generation started for {len(request.users)} users."
    )
