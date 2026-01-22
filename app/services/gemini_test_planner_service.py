"""
AI Planner Service with Gemini API (GEMINI TEST Version)

Gemini 3 Flash API를 사용하여 실제 AI 플래너 생성
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from google import genai

from app.models.planner_test import (
    PlannerGenerateRequestTest,
    PlannerGenerateResponseTest,
    PlannerScheduleResultTest,
    PlannerScheduleInputTest,
    ChildScheduleTest,
    TaskType,
    AssignedBy,
    AssignmentStatus,
    EstimatedTimeRange,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _hhmm_to_minutes(t: str) -> int:
    """HH:MM 형식 문자열을 분(minute) 단위 정수로 변환"""
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)


def _minutes_to_hhmm(minutes: int) -> str:
    """분 단위 정수를 HH:MM 형식 문자열로 변환"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


def _get_estimated_minutes(estimated_time_range: Optional[EstimatedTimeRange]) -> int:
    """EstimatedTimeRange Enum을 실제 분으로 변환 (중간값 사용)"""
    if not estimated_time_range:
        return 60  # 기본값 1시간

    mapping = {
        EstimatedTimeRange.MINUTE_UNDER_30: 20,
        EstimatedTimeRange.MINUTE_30_TO_60: 45,
        EstimatedTimeRange.HOUR_1_TO_2: 90,
        EstimatedTimeRange.HOUR_2_TO_4: 180,
        EstimatedTimeRange.HOUR_OVER_4: 300,
    }
    return mapping.get(estimated_time_range, 60)


def _create_gemini_prompt(request: PlannerGenerateRequestTest) -> str:
    """Gemini API에 전달할 프롬프트 생성"""

    # 사용자 컨텍스트 정보
    user_info = f"""
사용자 정보:
- 사용자 ID: {request.user.user_id}
- 몰입 시간대: {request.user.focus_time_zone.value}
- 하루 종료 시간: {request.user.day_end_time}
- 배치 시작 시각: {request.start_arrange}
"""

    # FIXED 작업 목록
    fixed_tasks = [s for s in request.schedules if s.type == TaskType.FIXED]
    fixed_info = "\n고정된 일정 (FIXED - 시간 변경 불가):\n"
    for task in fixed_tasks:
        fixed_info += f"- Task ID {task.task_id}, Day Plan ID {task.day_plan_id}: [{task.start_at} ~ {task.end_at}] {task.title}\n"

    # FLEX 작업 목록
    flex_tasks = [s for s in request.schedules if s.type == TaskType.FLEX]
    flex_info = "\n유동적인 할일 (FLEX - AI가 시간 배치 필요):\n"
    for task in flex_tasks:
        estimated_time = _get_estimated_minutes(task.estimated_time_range)
        focus = task.focus_level if task.focus_level else "미지정"
        urgent = "긴급" if task.is_urgent else "일반"
        flex_info += f"- Task ID {task.task_id}, Day Plan ID {task.day_plan_id}: {task.title} (예상소요: {estimated_time}분, 몰입도: {focus}, 우선순위: {urgent})\n"

    # 프롬프트 작성
    prompt = f"""
당신은 일정 관리 AI 플래너입니다. 사용자의 하루 일정을 최적으로 배치해주세요.

{user_info}

{fixed_info}

{flex_info}

**요구사항:**
1. FIXED 작업의 시간은 절대 변경하지 마세요.
2. FLEX 작업들을 FIXED 작업 사이의 빈 시간에 배치하세요.
3. 각 작업의 시간은 1분도 겹치지 않아야 합니다.
4. 배치 시작 시각({request.start_arrange}) 이후부터 배치하세요.
5. 하루 종료 시간({request.user.day_end_time}) 이전에 작업을 배치하세요.
6. **실제 사용자처럼 현실적으로 플래너를 작성하세요:**
   - 하루에 모든 작업을 다 할 수 없습니다.
   - 가능한 시간을 고려하여 우선순위가 낮거나, 몰입도가 낮거나, 긴급하지 않은 작업들은 EXCLUDED(제외)로 표시하세요.
   - **FLEX 작업 중 40-60% 정도는 EXCLUDED로 설정**하여 실제 사용자가 플래너를 짜는 것처럼 현실적으로 작성하세요.
   - 여유 시간도 고려하세요 (빡빡하게 배치하지 마세요).
7. 긴급(isUrgent=true)하고 몰입도(focusLevel)가 높은 작업을 우선 배치하세요.
8. 몰입 시간대({request.user.focus_time_zone.value})에는 몰입도가 높은 작업을 배치하세요.
9. 몰입도가 낮은 작업(focusLevel 1-3)이나 긴급하지 않은 작업은 EXCLUDED로 처리하는 것을 우선적으로 고려하세요.

**응답 형식 (JSON):**
당신은 각 작업에 대해 **아래 사항을** 결정하면 됩니다:
1. `taskId`: 작업 ID (위에서 제공한 Task ID 그대로 사용)
2. `assignmentStatus`: "ASSIGNED" (배치함) 또는 "EXCLUDED" (제외함)
3. `startAt`, `endAt`: 시간 배치 (분할 배치되는 경우 null)
4. `children`: **긴 작업(HOUR_1_TO_2 이상, 90분 이상)을 여러 시간대에 분할 배치하는 경우 필수**
      - 이때 예시 생성을 위하여 반드시 "estimatedTimeRange": "HOUR_1_TO_2"인 작업 중 하나는 children를 포함하세요.
      
```json
{{
  "schedules": [
    {{
      "taskId": 작업ID(숫자),
      "assignmentStatus": "ASSIGNED" 또는 "EXCLUDED",
      "startAt": "HH:MM" 또는 null,
      "endAt": "HH:MM" 또는 null,
      "children": null 또는 [
        {{"title": "작업제목 - 1", "startAt": "HH:MM", "endAt": "HH:MM"}},
        {{"title": "작업제목 - 2", "startAt": "HH:MM", "endAt": "HH:MM"}}
      ]
    }}
  ]
}}
```

**중요:**
- **FIXED 작업**: 모두 assignmentStatus="ASSIGNED", 원래 시간(startAt/endAt) 그대로 유지, children=null
- **FLEX 작업 (분할하지 않는 경우)**:
  - assignmentStatus="ASSIGNED"인 경우 → startAt/endAt을 배치한 시간으로 설정, children=null
  - assignmentStatus="EXCLUDED"인 경우 → startAt/endAt을 null로 설정, children=null
- **긴 작업 분할 배치 (HOUR_1_TO_2, HOUR_2_TO_4, HOUR_OVER_4인 FLEX 작업)**:
  - 긴 작업은 연속된 긴 시간 슬롯이 없을 경우, **여러 시간대로 분할하여 배치**하세요.
  - **분할 배치 시 부모 작업의 startAt/endAt은 반드시 null로 설정** (실제 시간은 children에만!)
  - 분할 시 `children` 배열에 각 분할된 작업을 포함하세요.
  - 예: "통계학 과제 (긴급)" (예상 2~4시간)을 분할 배치하면:
    - startAt: null, endAt: null (부모는 시간 없음!)
    - children: [{{"title": "통계학 과제 (긴급) - 1", "startAt": "09:30", "endAt": "10:00"}}, {{"title": "통계학 과제 (긴급) - 2", "startAt": "13:00", "endAt": "15:30"}}]
  - 분할하지 않는 경우 children=null
  - 이때 예시 생성을 위하여 반드시 "estimatedTimeRange": "HOUR_1_TO_2"인 작업 중 하나는 children를 포함하세요.
- **FLEX 작업 중 40-60% 정도는 EXCLUDED로 설정** (현실적인 플래너 작성)
- 우선순위: 긴급도 > 몰입도 > 예상 소요 시간을 고려하여 중요한 작업만 ASSIGNED로 배치

JSON만 응답하세요. 다른 설명은 필요 없습니다.
"""

    return prompt


def _validate_and_fix_time_range(
    results: List[PlannerScheduleResultTest],
    request: PlannerGenerateRequestTest
) -> List[PlannerScheduleResultTest]:
    """AI 생성 결과의 시간이 startArrange~dayEndTime 범위 내인지 검증하고 수정"""
    start_arrange_min = _hhmm_to_minutes(request.start_arrange)
    day_end_min = _hhmm_to_minutes(request.user.day_end_time)

    for result in results:
        if result.assignment_status == AssignmentStatus.ASSIGNED and result.start_at and result.end_at:
            task_start_min = _hhmm_to_minutes(result.start_at)
            task_end_min = _hhmm_to_minutes(result.end_at)

            # 시간 범위를 벗어나는 경우 EXCLUDED로 변경
            if task_start_min < start_arrange_min or task_end_min > day_end_min:
                logger.warning(
                    f"작업 {result.task_id}의 시간({result.start_at}~{result.end_at})이 "
                    f"허용 범위({request.start_arrange}~{request.user.day_end_time})를 벗어나 EXCLUDED로 변경합니다."
                )
                result.assignment_status = AssignmentStatus.EXCLUDED
                result.start_at = None
                result.end_at = None

    return results


def _parse_gemini_response(
    response_text: str,
    request: PlannerGenerateRequestTest
) -> PlannerGenerateResponseTest:
    """Gemini API 응답을 파싱하여 PlannerGenerateResponseTest로 변환"""

    try:
        # JSON 부분만 추출 (```json ``` 제거)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        # JSON 파싱
        response_data = json.loads(response_text)
        schedules_data = response_data.get("schedules", [])

        # 입력 데이터를 taskId 기준으로 매핑 (빠른 조회를 위해)
        input_task_map = {task.task_id: task for task in request.schedules}

        # PlannerScheduleResultTest 객체 생성
        results: List[PlannerScheduleResultTest] = []
        for schedule in schedules_data:
            task_id = schedule["taskId"]

            # 입력 데이터에서 원본 정보 가져오기
            input_task = input_task_map.get(task_id)
            if not input_task:
                logger.warning(f"Gemini가 존재하지 않는 taskId {task_id}를 반환했습니다. 스킵합니다.")
                continue

            # type과 assignedBy는 입력값 기반으로 자동 결정
            task_type = input_task.type
            assigned_by = AssignedBy.USER if task_type == TaskType.FIXED else AssignedBy.AI

            # dayPlanId, title은 입력값 그대로
            day_plan_id = input_task.day_plan_id
            title = input_task.title

            # Gemini가 제공한 값들
            assignment_status = AssignmentStatus(schedule["assignmentStatus"])
            start_at = schedule.get("startAt")
            end_at = schedule.get("endAt")

            # children 처리 (분할 배치된 작업)
            children_data = schedule.get("children")
            children = None
            if children_data and isinstance(children_data, list) and len(children_data) > 0:
                children = []
                for child in children_data:
                    child_schedule = ChildScheduleTest(
                        title=child.get("title", f"{title} - {len(children) + 1}"),
                        startAt=child.get("startAt"),
                        endAt=child.get("endAt"),
                    )
                    children.append(child_schedule)

            result = PlannerScheduleResultTest(
                taskId=task_id,
                dayPlanId=day_plan_id,
                title=title,
                type=task_type,
                assignedBy=assigned_by,
                assignmentStatus=assignment_status,
                startAt=start_at,
                endAt=end_at,
                children=children,
            )
            results.append(result)

        # 검증: EXCLUDED 작업 확인
        flex_count = sum(1 for r in results if r.type == TaskType.FLEX)
        excluded_count = sum(1 for r in results if r.assignment_status == AssignmentStatus.EXCLUDED)

        if excluded_count == 0:
            logger.warning("Gemini가 EXCLUDED 작업을 만들지 않았습니다. 우선순위가 낮은 FLEX 작업들을 강제로 EXCLUDED로 변경합니다.")
            # 우선순위가 낮은 FLEX 작업들을 EXCLUDED로 변경 (전체 FLEX의 40% 정도)
            target_excluded = max(1, int(flex_count * 0.4))
            changed = 0
            for i in range(len(results) - 1, -1, -1):
                if changed >= target_excluded:
                    break
                if results[i].type == TaskType.FLEX and results[i].assignment_status == AssignmentStatus.ASSIGNED:
                    results[i].assignment_status = AssignmentStatus.EXCLUDED
                    results[i].start_at = None
                    results[i].end_at = None
                    changed += 1
        elif excluded_count < flex_count * 0.3:
            logger.warning(f"EXCLUDED 작업이 적습니다 ({excluded_count}/{flex_count}). 현실적인 플래너를 위해 더 많은 작업을 제외하는 것을 권장합니다.")

        # 시간 범위 검증 및 수정 (startArrange~dayEndTime 범위 벗어나면 EXCLUDED로 변경)
        results = _validate_and_fix_time_range(results, request)

        # 시간 순서대로 오름차순 정렬 (ASSIGNED는 startAt 기준, EXCLUDED는 맨 뒤로)
        def sort_key(r: PlannerScheduleResultTest) -> tuple:
            if r.assignment_status == AssignmentStatus.EXCLUDED or r.start_at is None:
                return (1, 9999, r.task_id)  # EXCLUDED는 맨 뒤로, task_id로 2차 정렬
            return (0, _hhmm_to_minutes(r.start_at), r.task_id)

        results.sort(key=sort_key)

        return PlannerGenerateResponseTest(schedules=results)

    except Exception as e:
        logger.error(f"Gemini 응답 파싱 실패: {e}")
        logger.error(f"원본 응답: {response_text}")
        raise ValueError(f"Gemini API 응답 파싱 실패: {e}")


async def gemini_test_generate_planner(
    request: PlannerGenerateRequestTest
) -> PlannerGenerateResponseTest:
    """
    Gemini API를 사용한 플래너 생성 함수

    Args:
        request: PlannerGenerateRequestTest

    Returns:
        PlannerGenerateResponseTest
    """

    # Gemini API 설정
    api_key = settings.gemini_api_key
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    # Gemini 클라이언트 초기화
    client = genai.Client(api_key=api_key)

    # 프롬프트 생성
    prompt = _create_gemini_prompt(request)

    logger.info("=" * 80)
    logger.info("[GEMINI TEST] Gemini API 호출 시작")
    logger.info(f"[GEMINI TEST] 사용자 ID: {request.user.user_id}")
    logger.info(f"[GEMINI TEST] 전체 작업 수: {len(request.schedules)}")
    logger.info(f"[GEMINI TEST] FIXED 작업 수: {sum(1 for s in request.schedules if s.type == TaskType.FIXED)}")
    logger.info(f"[GEMINI TEST] FLEX 작업 수: {sum(1 for s in request.schedules if s.type == TaskType.FLEX)}")
    logger.info("=" * 80)

    try:
        # Gemini API 호출 (새로운 API 사용)
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        response_text = response.text

        logger.info("[GEMINI TEST] Gemini API 응답 수신 완료")
        logger.info(f"[GEMINI TEST] 응답 길이: {len(response_text)} characters")

        # 응답 파싱
        result = _parse_gemini_response(response_text, request)

        # 결과 로깅
        assigned_count = sum(1 for r in result.schedules if r.assignment_status == AssignmentStatus.ASSIGNED)
        excluded_count = sum(1 for r in result.schedules if r.assignment_status == AssignmentStatus.EXCLUDED)

        logger.info("=" * 80)
        logger.info("[GEMINI TEST] 플래너 생성 완료")
        logger.info(f"[GEMINI TEST] 배치된 작업(ASSIGNED): {assigned_count}")
        logger.info(f"[GEMINI TEST] 제외된 작업(EXCLUDED): {excluded_count}")
        logger.info("=" * 80)

        return result

    except Exception as e:
        logger.error(f"[GEMINI TEST] Gemini API 호출 실패: {e}")
        raise
