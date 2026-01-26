"""
AI Planner API Router with Gemini (GEMINI TEST Version)

POST /ai/v1/gemini-test/planners 엔드포인트
"""

import logging
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from google.api_core import exceptions as google_exceptions

from app.models.planner_test import (
    PlannerGenerateRequestTest,
    PlannerGenerateResponseTest,
)
from app.services.gemini_test_planner_service import gemini_test_generate_planner
from app.models.planner.errors import PlannerErrorCode

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 생성
## __init__.py로 라우터 통합 관리
router = APIRouter(
    tags=["AI Planner (GEMINI TEST)"]
)


import time
import uuid

# API 엔드포인트
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
    response_model_exclude_unset=True,
)

# 플래너 생성 함수 (비동기))
async def gemini_test_create_planner(
    request: PlannerGenerateRequestTest # 입력할 JSON 데이터 형식
) -> PlannerGenerateResponseTest: # 출력할 JSON 데이터 형식
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

    start_time = time.time()
    trace_id = str(uuid.uuid4())

    try:
        # Gemini API 서비스 호출
        results = await gemini_test_generate_planner(request)
        
        end_time = time.time()
        process_time = round(end_time - start_time, 2)

        logger.info("=" * 80)
        logger.info(f"[GEMINI TEST API] 응답 완료: {len(results)} 작업")
        logger.info(f"[GEMINI TEST API] 처리 시간: {process_time}초")
        logger.info("=" * 80)

        return PlannerGenerateResponseTest(
            success=True,
            processTime=process_time,
            results=results
        )

    except ValueError as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] Validation 에러: {e}")
        
        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_BAD_REQUEST,
            message=str(e),
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    # Google API 예외 처리
    except google_exceptions.ServiceUnavailable as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 서비스 사용 불가 (503): {e}")
        
        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_SERVICE_UNAVAILABLE,
            message="AI 서비스가 일시적으로 불가능합니다. 잠시 후 다시 시도해주세요.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.ResourceExhausted as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 리소스 소진 (429): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_RESOURCE_EXHAUSTED,
            message="요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.InvalidArgument as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 잘못된 인자 (400): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_INVALID_ARGUMENT,
            message="AI 모델에 전달된 데이터가 올바르지 않습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.FailedPrecondition as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 전제 조건 실패 (400): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_FAILED_PRECONDITION,
            message="요청을 처리하기 위한 전제 조건이 충족되지 않았습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.OutOfRange as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 범위 초과 (400): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_OUT_OF_RANGE,
            message="요청 데이터가 허용 범위를 벗어났습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.Unauthenticated as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 인증 실패 (401): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_UNAUTHENTICATED,
            message="AI 서비스 인증에 실패했습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.PermissionDenied as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 권한 거부 (403): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_PERMISSION_DENIED,
            message="AI 서비스 접근 권한이 없습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.NotFound as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 찾을 수 없음 (404): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_NOT_FOUND,
            message="요청한 리소스(AI 모델 등)를 찾을 수 없습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except google_exceptions.DeadlineExceeded as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 시간 초과 (504): {e}")

        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_TIMEOUT,
            message="AI 서비스 응답 시간이 초과되었습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )

    except Exception as e:
        end_time = time.time()
        process_time = round(end_time - start_time, 2)
        logger.error(f"[GEMINI TEST API] 서버 에러: {e}")
        
        # 500 Internal Server Error에 해당하는 에러 응답 반환
        error_response = PlannerGenerateResponseTest(
            success=False,
            processTime=process_time,
            errorCode=PlannerErrorCode.PLANNER_SERVER_ERROR,
            message="플래너 생성 중 오류가 발생했습니다.",
            traceId=trace_id
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(error_response, exclude_unset=True)
        )
