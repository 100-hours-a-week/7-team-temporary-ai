"""
Pydantic Models for AI Planner API (TEST Version)

테스트용 모델:
- 모든 모델명에 'Test' 접미사 추가
- 단순 에코(echo) 응답 구조
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# Type Definitions
# ============================================================

TimeHHMM = Annotated[
    str,
    Field(
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="24시간제 HH:MM 형식",
        examples=["09:00", "18:30", "23:59"],
    ),
]

BigInt64 = Annotated[
    int,
    Field(
        ge=1,
        le=9_223_372_036_854_775_807,  # signed BIGINT max
        description="BIGINT(64-bit) 범위 정수",
        examples=[123456789],
    ),
]


def _hhmm_to_minutes(t: str) -> int:
    """HH:MM 형식 문자열을 분(minute) 단위 정수로 변환"""
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)


# ============================================================
# Enums
# ============================================================

class FocusTimeZone(str, Enum):
    """
    사용자 몰입 가능 시간대.

    - Backend가 Users.focusTimeZone 값을 그대로 전달.
    - AI는 몰입 시간대에 '집중/중요 작업'을 우선 배치하는 등 배치 전략에 활용.
    """
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"


class TaskType(str, Enum):
    """
    일정(Task)의 타입.

    - FIXED: 사용자가 startAt/endAt을 확정한 고정 일정(시간 변경 대상 아님)
    - FLEX : 시간이 미정이거나(또는 재배치가 필요한) 유동 일정(AI가 시간 배치)
    """
    FIXED = "FIXED"
    FLEX = "FLEX"


class EstimatedTimeRange(str, Enum):
    """
    FLEX 작업 배치에 사용하는 예상 소요 시간 구간(Enum).

    - 실제 분(minute) 숫자 대신 구간값으로 전달받아 배치 로직에 사용.
    """
    MINUTE_UNDER_30 = "MINUTE_UNDER_30"
    MINUTE_30_TO_60 = "MINUTE_30_TO_60"
    HOUR_1_TO_2 = "HOUR_1_TO_2"
    HOUR_2_TO_4 = "HOUR_2_TO_4"
    HOUR_OVER_4 = "HOUR_OVER_4"


class AssignedBy(str, Enum):
    """
    배치/수정 주체(기존 whoChange를 assignedBy로 변경).

    이 API의 출력 규칙(고정):
    - type=FIXED -> USER
    - type=FLEX  -> AI
    """
    USER = "USER"
    AI = "AI"


class AssignmentStatus(str, Enum):
    """
    배치 상태(기존 is_excluded_Task / is_Todolist를 통합).

    - NOT_ASSIGNED: 배치되지 않음(= Todo list에 존재)
    - ASSIGNED: 플래너에 배치됨
    - EXCLUDED: 제외 리스트에 배치됨
    """
    NOT_ASSIGNED = "NOT_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    EXCLUDED = "EXCLUDED"


# ============================================================
# Request Models (TEST)
# ============================================================

class PlannerUserContextTest(BaseModel):
    """
    [요청] 사용자 컨텍스트(Users 기반) — 요청 최상위에서 user 객체로 래핑됨.

    목적
    - 배치 로직에 필요한 사용자 설정값을 'user' 객체로 묶어 전달한다.

    필드
    - userId: Users.User_id (BIGINT)
    - focusTimeZone: Users.focusTimeZone
    - dayEndTime: Users.dayEndTime을 Backend가 HH:MM로 변환해 전달
    """
    model_config = ConfigDict(populate_by_name=True)

    user_id: BigInt64 = Field(..., alias="userId", description="Users.User_id(BIGINT)")
    focus_time_zone: FocusTimeZone = Field(..., alias="focusTimeZone", description="몰입 시간대")
    day_end_time: TimeHHMM = Field(..., alias="dayEndTime", description="하루 마무리 시간(HH:MM)")


class PlannerScheduleInputTest(BaseModel):
    """
    [요청] 배치 대상 작업(Schedule 기반, dayPlanId의 전체 작업).

    목적
    - Backend가 해당 dayPlanId의 모든 작업(FIXED + FLEX)을 AI로 전달한다.
    - AI는 FIXED는 유지하고, FLEX는 배치/제외를 결정한다.

    필드
    - taskId/dayPlanId: Schedule PK/그룹 키(BIGINT)
    - title: 작업 제목(배치/분류/우선순위 결정 등에서 사용할 수 있음)
    - type: FIXED / FLEX
    - startAt/endAt:
        * FIXED는 필수(HH:MM)
        * FLEX는 null 허용(배치 전 미정)
    - estimatedTimeRange/focusLevel/isUrgent:
        * 주로 FLEX 배치에 활용
        * FIXED는 null이어도 됨
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: BigInt64 = Field(..., alias="taskId", description="Schedule.Task_id(BIGINT)")

    parent_schedule_id: Optional[BigInt64] = Field(
        None,
        alias="parentScheduleId",
        description="상위 작업 ID(부모 Schedule ID). 없으면 null"
    )

    day_plan_id: BigInt64 = Field(..., alias="dayPlanId", description="Schedule.dayPlanId(BIGINT)")

    title: str = Field(..., max_length=60, description="작업 제목", examples=["통계학 실습 과제"])
    type: TaskType = Field(..., description="작업 타입(FIXED/FLEX)")

    start_at: Optional[TimeHHMM] = Field(None, alias="startAt", description="시작 시간(HH:MM)")
    end_at: Optional[TimeHHMM] = Field(None, alias="endAt", description="종료 시간(HH:MM)")

    estimated_time_range: Optional[EstimatedTimeRange] = Field(
        None, alias="estimatedTimeRange", description="예상 소요 시간 구간"
    )
    focus_level: Optional[int] = Field(
        None, alias="focusLevel", ge=1, le=10, description="몰입도(1~10)"
    )
    is_urgent: Optional[bool] = Field(None, alias="isUrgent", description="급해요 여부")

    @model_validator(mode="after")
    def _validate_time_rules(self) -> "PlannerScheduleInputTest":
        # FIXED는 startAt/endAt 필수
        if self.type == TaskType.FIXED:
            if self.start_at is None or self.end_at is None:
                raise ValueError("type=FIXED 인 경우 startAt/endAt은 필수입니다.")
            if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                raise ValueError("FIXED 작업은 endAt이 startAt보다 뒤여야 합니다.")

        # FLEX는 null 허용(배치 전)
        if self.type == TaskType.FLEX:
            # FLEX에 시간이 들어오는 경우(재배치 시나리오)도 허용할지 정책 선택 가능.
            # 현재는 들어오면 형식/순서만 검증하도록 처리.
            if (self.start_at is None) != (self.end_at is None):
                raise ValueError("FLEX 작업은 startAt/endAt이 둘 다 null이거나, 둘 다 값이 있어야 합니다.")
            if self.start_at and self.end_at:
                if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                    raise ValueError("FLEX 작업의 endAt은 startAt보다 뒤여야 합니다.")

        return self


class PlannerGenerateRequestTest(BaseModel):
    """
    [요청] POST /ai/v1/planners Request Body (TEST).

    변경사항(요구 반영)
    - userId/focusTimeZone/dayEndTime을 최상위에서 제거하고,
      user 객체로 래핑하여 전달한다.

    구성
    - user: 사용자 설정(Users 기반)
    - startArrange: '배치하기' 버튼 클릭 시각(HH:MM)
    - schedules: dayPlanId의 전체 작업 목록(Schedule 기반)
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "user": {
                    "userId": 12345,
                    "focusTimeZone": "MORNING",
                    "dayEndTime": "23:00"
                },
                "startArrange": "09:00",
                "schedules": [
                    {
                        "taskId": 1,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "아침 스트레칭",
                        "type": "FIXED",
                        "startAt": "09:00",
                        "endAt": "09:30",
                        "estimatedTimeRange": None,
                        "focusLevel": None,
                        "isUrgent": None
                    },
                    {
                        "taskId": 2,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "팀 회의",
                        "type": "FIXED",
                        "startAt": "10:00",
                        "endAt": "11:00",
                        "estimatedTimeRange": None,
                        "focusLevel": None,
                        "isUrgent": None
                    },
                    {
                        "taskId": 3,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "점심 약속",
                        "type": "FIXED",
                        "startAt": "12:00",
                        "endAt": "13:00",
                        "estimatedTimeRange": None,
                        "focusLevel": None,
                        "isUrgent": None
                    },
                    {
                        "taskId": 4,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "저녁 약속",
                        "type": "FIXED",
                        "startAt": "18:30",
                        "endAt": "20:00",
                        "estimatedTimeRange": None,
                        "focusLevel": None,
                        "isUrgent": None
                    },
                    {
                        "taskId": 5,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "통계학 과제 (긴급)",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "HOUR_2_TO_4",
                        "focusLevel": 9,
                        "isUrgent": True
                    },
                    {
                        "taskId": 6,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "영어 공부",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "HOUR_1_TO_2",
                        "focusLevel": 8,
                        "isUrgent": True
                    },
                    {
                        "taskId": 7,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "프로젝트 기획서 작성",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "HOUR_1_TO_2",
                        "focusLevel": 7,
                        "isUrgent": False
                    },
                    {
                        "taskId": 8,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "코딩 연습",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_30_TO_60",
                        "focusLevel": 6,
                        "isUrgent": False
                    },
                    {
                        "taskId": 9,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "책 읽기",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_30_TO_60",
                        "focusLevel": 4,
                        "isUrgent": False
                    },
                    {
                        "taskId": 10,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "블로그 글쓰기",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "HOUR_1_TO_2",
                        "focusLevel": 5,
                        "isUrgent": False
                    },
                    {
                        "taskId": 11,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "유튜브 강의 시청",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_30_TO_60",
                        "focusLevel": 3,
                        "isUrgent": False
                    },
                    {
                        "taskId": 12,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "이메일 정리",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_UNDER_30",
                        "focusLevel": 2,
                        "isUrgent": False
                    },
                    {
                        "taskId": 13,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "SNS 확인",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_UNDER_30",
                        "focusLevel": 1,
                        "isUrgent": False
                    },
                    {
                        "taskId": 14,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "방 청소",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_30_TO_60",
                        "focusLevel": 3,
                        "isUrgent": False
                    },
                    {
                        "taskId": 15,
                        "parentScheduleId": None,
                        "dayPlanId": 100,
                        "title": "친구와 전화",
                        "type": "FLEX",
                        "startAt": None,
                        "endAt": None,
                        "estimatedTimeRange": "MINUTE_30_TO_60",
                        "focusLevel": 2,
                        "isUrgent": False
                    }
                ]
            }
        }
    )

    user: PlannerUserContextTest = Field(..., description="사용자 컨텍스트(Users 기반)")
    start_arrange: TimeHHMM = Field(..., alias="startArrange", description="배치하기 버튼 클릭 시각(HH:MM)")
    schedules: List[PlannerScheduleInputTest] = Field(..., description="배치 대상 작업 목록(Schedule 기반)")

    @model_validator(mode="after")
    def _validate_fixed_time_range(self) -> "PlannerGenerateRequestTest":
        """FIXED 작업의 시간이 startArrange~dayEndTime 범위 내인지 검증"""
        start_arrange_min = _hhmm_to_minutes(self.start_arrange)
        day_end_min = _hhmm_to_minutes(self.user.day_end_time)

        for schedule in self.schedules:
            if schedule.type == TaskType.FIXED:
                if schedule.start_at and schedule.end_at:
                    task_start_min = _hhmm_to_minutes(schedule.start_at)
                    task_end_min = _hhmm_to_minutes(schedule.end_at)

                    if task_start_min < start_arrange_min:
                        raise ValueError(
                            f"FIXED 작업 '{schedule.title}'(taskId={schedule.task_id})의 "
                            f"시작 시간({schedule.start_at})이 배치 시작 시각({self.start_arrange}) 이전입니다."
                        )
                    if task_end_min > day_end_min:
                        raise ValueError(
                            f"FIXED 작업 '{schedule.title}'(taskId={schedule.task_id})의 "
                            f"종료 시간({schedule.end_at})이 하루 종료 시간({self.user.day_end_time}) 이후입니다."
                        )

        return self


# ============================================================
# Response Models (TEST)
# ============================================================

class PlannerScheduleResultTest(BaseModel):
    """
    [응답] 작업별 배치 결과 (TEST).

    TEST 규칙:
    - taskId, dayPlanId, type, startAt, endAt: 입력값 그대로 반환
    - assignedBy:
        * type=FIXED -> USER
        * type=FLEX  -> AI
    - assignmentStatus:
        * type=FIXED -> ASSIGNED
        * type=FLEX  -> EXCLUDED
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: BigInt64 = Field(..., alias="taskId", description="Schedule.Task_id(BIGINT)")
    day_plan_id: BigInt64 = Field(..., alias="dayPlanId", description="Schedule.dayPlanId(BIGINT)")
    title: str = Field(..., max_length=60, description="작업 제목", examples=["통계학 실습 과제"])

    type: TaskType = Field(..., description="작업 타입(FIXED/FLEX)")
    assigned_by: AssignedBy = Field(..., alias="assignedBy", description="배치/수정 주체(FIXED=USER, FLEX=AI)")
    assignment_status: AssignmentStatus = Field(..., alias="assignmentStatus", description="배치 상태")

    start_at: Optional[TimeHHMM] = Field(None, alias="startAt", description="시작 시간(HH:MM)")
    end_at: Optional[TimeHHMM] = Field(None, alias="endAt", description="종료 시간(HH:MM)")


class PlannerGenerateResponseTest(BaseModel):
    """
    [응답] POST /ai/v1/planners Response Body (TEST).

    구성
    - schedules: 배치 결과 작업 목록
    """
    model_config = ConfigDict(populate_by_name=True)

    schedules: List[PlannerScheduleResultTest] = Field(..., description="배치 결과 작업 목록")
