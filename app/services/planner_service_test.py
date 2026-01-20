"""
AI Planner Service (TEST Version)

백엔드 연동 확인을 위한 단순 에코(echo) 응답 로직
"""

from typing import List

from app.models.planner_test import (
    PlannerGenerateRequestTest,
    PlannerGenerateResponseTest,
    PlannerScheduleResultTest,
    TaskType,
    AssignedBy,
    AssignmentStatus,
)


def generate_planner_test(request: PlannerGenerateRequestTest) -> PlannerGenerateResponseTest:
    """
    TEST 플래너 생성 함수

    입력받은 데이터를 기반으로 단순 에코 응답 생성:
    1. taskId, dayPlanId, type, startAt, endAt: 입력값 그대로 반환
    2. assignedBy: type이 FIXED면 "USER", FLEX면 "AI"
    3. assignmentStatus: type이 FIXED면 "ASSIGNED", FLEX면 "EXCLUDED"

    Args:
        request: PlannerGenerateRequestTest

    Returns:
        PlannerGenerateResponseTest
    """

    results: List[PlannerScheduleResultTest] = []

    for schedule in request.schedules:
        # assignedBy 결정
        assigned_by = AssignedBy.USER if schedule.type == TaskType.FIXED else AssignedBy.AI

        # assignmentStatus 결정
        assignment_status = (
            AssignmentStatus.ASSIGNED if schedule.type == TaskType.FIXED
            else AssignmentStatus.EXCLUDED
        )

        # 결과 생성 (입력값 그대로 + 조건부 생성 필드)
        result = PlannerScheduleResultTest(
            taskId=schedule.task_id,
            dayPlanId=schedule.day_plan_id,
            type=schedule.type,
            assignedBy=assigned_by,
            assignmentStatus=assignment_status,
            startAt=schedule.start_at,
            endAt=schedule.end_at,
        )

        results.append(result)

    return PlannerGenerateResponseTest(schedules=results)
