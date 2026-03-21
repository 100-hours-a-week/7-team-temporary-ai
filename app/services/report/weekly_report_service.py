import asyncio
import logging
import logfire
from datetime import date

from app.models.report import WeeklyReportGenerateRequest
from app.db.repositories.report_repository import ReportRepository
from app.llm.runpod_client import get_runpod_client
from app.llm.prompts.report_prompt import format_report_data_for_llm, WEEKLY_REPORT_SYSTEM_PROMPT
from app.models.planner.errors import map_exception_to_error_code, is_retryable_error

logger = logging.getLogger(__name__)

async def generate_batch_reports(request: WeeklyReportGenerateRequest) -> None:
    """
    여러 유저에 대한 주간 레포트를 배치로 생성합니다.
    (BackgroundTasks에 의해 호출 예정)
    """
    logger.info(f"Starting batch report generation for {len(request.users)} users. Base Date: {request.base_date}")
    
    # 10 RPS(초당 요청 수) 제한을 위해 10명씩 끊어서 처리
    tasks = []
    chunk_size = 10
    
    for i in range(0, len(request.users), chunk_size):
        chunk = request.users[i : i + chunk_size]
        logger.info(f"[BatchReport] Processing chunk {i//chunk_size + 1} ({len(chunk)} users)")
        
        for user_target in chunk:
            tasks.append(asyncio.create_task(_generate_single_report(
                user_id=user_target.user_id,
                report_id=user_target.report_id,
                base_date=request.base_date
            )))
            
        # 마지막 청크가 아니라면 1초 대기하여 RPS 제한 준수
        if i + chunk_size < len(request.users):
            await asyncio.sleep(1)
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    success_count = 0
    for idx, res in enumerate(results):
        trg = request.users[idx]
        if isinstance(res, Exception):
             logger.error(f"[BatchReport] Failed for user {trg.user_id} (Report {trg.report_id}): {res}")
        elif res is True:
             success_count += 1
             
    logger.info(f"Batch report generation completed. Success: {success_count}/{len(request.users)}")


@logfire.instrument
async def _generate_single_report(user_id: int, report_id: int, base_date: date) -> bool:
    """
    단일 사용자의 주간 레포트를 생성하고 DB에 저장합니다.
    (무한 재시도 로직 포함)
    """
    repo = ReportRepository()
    
    try:
        # 1. 과거 4주 데이터 Fetch
        raw_data = await repo.fetch_past_4_weeks_data(user_id, base_date)
        
        # 2. LLM 입력 데이터 포맷팅
        user_prompt = format_report_data_for_llm(base_date, raw_data)
        
        # 3. LLM 호출 (재시도 로직)
        client = get_runpod_client()
        generated_markdown = ""
        success = False

        max_retries = 4
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[Report] RunPod LLM Attempt {attempt} for User {user_id}")
                generated_markdown = await client.generate_text(
                    system=WEEKLY_REPORT_SYSTEM_PROMPT,
                    user=user_prompt,
                )
                if generated_markdown:
                    success = True
                    break
            except Exception as e:
                error_code = map_exception_to_error_code(e)
                is_retryable = is_retryable_error(error_code)

                if not is_retryable:
                    logger.error(f"[Report] Non-retryable error: {e}")
                    break

                if attempt < max_retries:
                    delay = min(1.0 * (2 ** (attempt - 1)), 16.0)
                    logger.info(f"[Report] Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                    
        # 4. DB 저장
        if success and generated_markdown:
            saved = await repo.upsert_weekly_report(
                report_id=report_id,
                user_id=user_id,
                base_date=base_date,
                content=generated_markdown
            )
            return saved
            
        return False
        
    except Exception as e:
        logger.error(f"[_generate_single_report] Error for user {user_id}: {e}")
        return False


async def fetch_weekly_reports(request: "WeeklyReportFetchRequest") -> "WeeklyReportFetchResponse":
    from app.models.report import WeeklyReportData, WeeklyReportFetchResponse
    repo = ReportRepository()
    
    # DB에서 보고서 데이터 조회
    raw_reports = await repo.fetch_reports_by_targets(request.targets)
    
    # report_id 기준으로 딕셔너리로 변환하여 매핑하기 쉽게 함
    report_map = {row["report_id"]: row for row in raw_reports}
    
    results = []
    
    for target in request.targets:
        report_id = target.report_id
        user_id = target.user_id
        
        if report_id not in report_map:
            # 보고서가 없는 경우
            results.append(WeeklyReportData(
                report_id=report_id,
                user_id=user_id,
                status="NOT_FOUND",
                content=None
            ))
        else:
            db_report = report_map[report_id]
            # 요청한 user_id와 DB의 user_id가 다른 경우 권한 없음 처리
            if db_report["user_id"] != user_id:
                results.append(WeeklyReportData(
                    report_id=report_id,
                    user_id=user_id,
                    status="FORBIDDEN",
                    content=None
                ))
            else:
                results.append(WeeklyReportData(
                    report_id=report_id,
                    user_id=user_id,
                    status="SUCCESS",
                    content=db_report.get("content")
                ))
                
    return WeeklyReportFetchResponse(
        success=True,
        results=results
    )
