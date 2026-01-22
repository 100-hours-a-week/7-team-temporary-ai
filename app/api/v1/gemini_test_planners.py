"""
AI Planner API Router with Gemini (GEMINI TEST Version)

POST /ai/v1/gemini-test/planners 엔드포인트
"""

import logging
from fastapi import APIRouter, status, HTTPException

from app.models.planner_test import (
    PlannerGenerateRequestTest,
    PlannerGenerateResponseTest,
)
from app.services.gemini_test_planner_service import gemini_test_generate_planner

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/ai/v1",
    tags=["AI Planner (GEMINI TEST)"]
)


@router.post(
    "/planners",
    response_model=PlannerGenerateResponseTest,
    status_code=status.HTTP_200_OK,
    summary="AI 플래너 생성 with Gemini (GEMINI TEST)",
    description="""
    Gemini 3 Flash API를 사용한 실제 AI 플래너 생성 API

    **Gemini AI가 수행하는 작업**:
    1. FIXED 작업의 시간은 절대 변경하지 않음
    2. FLEX 작업들을 최적의 시간에 배치
    3. 각 작업의 시간은 1분도 겹치지 않도록 배치
    4. 최소 하나 이상의 FLEX 작업을 EXCLUDED로 설정
    5. 긴급도와 몰입도를 고려한 우선순위 배치
    6. 사용자의 몰입 시간대에 집중 작업 배치

    **응답 규칙**:
    - FIXED 작업: assignedBy="USER", assignmentStatus="ASSIGNED"
    - FLEX 작업 (배치됨): assignedBy="AI", assignmentStatus="ASSIGNED", startAt/endAt 필수
    - FLEX 작업 (제외됨): assignedBy="AI", assignmentStatus="EXCLUDED", startAt/endAt=null
    """,
)
async def gemini_test_create_planner(
    request: PlannerGenerateRequestTest
) -> PlannerGenerateResponseTest:
    """
    AI 플래너 생성 with Gemini (GEMINI TEST)

    Args:
        request: PlannerGenerateRequestTest - 사용자 정보 + 작업 목록

    Returns:
        PlannerGenerateResponseTest - Gemini AI가 생성한 배치 결과
    """
    logger.info("=" * 80)
    logger.info(f"[GEMINI TEST API] 요청 수신: 사용자 {request.user.user_id}")
    logger.info(f"[GEMINI TEST API] 전체 작업 수: {len(request.schedules)}")
    logger.info("=" * 80)

    try:
        # Gemini API 서비스 호출
        response = await gemini_test_generate_planner(request)

        logger.info("=" * 80)
        logger.info(f"[GEMINI TEST API] 응답 완료: {len(response.schedules)} 작업")
        logger.info("=" * 80)

        return response

    except ValueError as e:
        logger.error(f"[GEMINI TEST API] Validation 에러: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"[GEMINI TEST API] 서버 에러: {e}")
        raise HTTPException(status_code=500, detail="플래너 생성 중 오류가 발생했습니다.")
