"""
AI Planner API Router (TEST Version)

POST /ai/v1/planners 엔드포인트
"""

import logging
from fastapi import APIRouter, status

from app.models.planner_test import (
    PlannerGenerateRequestTest,
    PlannerGenerateResponseTest,
)
from app.services.planner_service_test import generate_planner_test

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/ai/v1",
    tags=["AI Planner (TEST)"]
)


@router.post(
    "/planners",
    response_model=PlannerGenerateResponseTest,
    status_code=status.HTTP_200_OK,
    summary="AI 플래너 생성 (TEST)",
    description="""
    백엔드 연동 테스트용 AI 플래너 생성 API

    **TEST 로직**:
    - taskId, dayPlanId, type, startAt, endAt: 입력값 그대로 반환
    - assignedBy: FIXED → "USER", FLEX → "AI"
    - assignmentStatus: FIXED → "ASSIGNED", FLEX → "EXCLUDED"
    """,
)
async def create_planner_test(
    request: PlannerGenerateRequestTest
) -> PlannerGenerateResponseTest:
    """
    AI 플래너 생성 (TEST)

    Args:
        request: PlannerGenerateRequestTest - 사용자 정보 + 작업 목록

    Returns:
        PlannerGenerateResponseTest - 배치 결과
    """
    logger.info(f"[TEST] Planner generation request received for user: {request.user.user_id}")
    logger.info(f"[TEST] Number of schedules: {len(request.schedules)}")

    # TEST 서비스 호출
    response = generate_planner_test(request)

    logger.info(f"[TEST] Planner generation completed. Results: {len(response.schedules)}")

    return response
