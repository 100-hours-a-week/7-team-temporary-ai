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

# 시간 형식 강제 정규식 패턴
TimeHHMM = Annotated[ # 기본 타입에 추가적인 메타데이터를 덧붙임
    str, # 기본 타입
    Field( # 메타데이터 - 형식 정보
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$", # 정규식 패턴
        description="24시간제 HH:MM 형식", # 설명
        examples=["09:00", "18:30", "23:59"], # 예시
    ),
]

# BIGINT(64-bit) 범위 정수
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
    model_config = ConfigDict(populate_by_name=True) # 파이썬 변수명과 alias 모두 동일하게 입력할 수 있게 함

    # alias는 API 명세서의 변수명을 사용함
    user_id: BigInt64 = Field(..., alias="userId", description="Users.User_id(BIGINT)") # ...은 필수라는 의미
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

    title: str = Field(..., description="작업 제목", examples=["통계학 실습 과제"])
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

    # 입력 데이터 검증기
    ## type에 따른 startAt/endAt 검증
    @model_validator(mode="after") #after : 데이터 타입 확인 후 해당 함수 실행
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
        populate_by_name=True,# 파이썬 변수명과 alias 모두 동일하게 입력할 수 있게 함
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


# ============================================================
# Response Models (TEST)
# ============================================================

class ChildScheduleTest(BaseModel):
    """
    [응답] 분할된 하위 작업 (긴 작업을 여러 시간대로 나눈 경우).

    예: "통계학 과제 (긴급)"이 2시간 이상이면
        - "통계학 과제 (긴급) - 1" (09:30~10:00)
        - "통계학 과제 (긴급) - 2" (11:00~12:00)
    """
    model_config = ConfigDict(populate_by_name=True)

    title: str = Field(..., max_length=60, description="분할된 작업 제목", examples=["통계학 과제 (긴급) - 1"])
    start_at: TimeHHMM = Field(..., alias="startAt", description="시작 시간(HH:MM)")
    end_at: TimeHHMM = Field(..., alias="endAt", description="종료 시간(HH:MM)")


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
    - children: 긴 작업(HOUR_1_TO_2 이상)이 분할 배치된 경우 하위 작업 목록
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

    children: Optional[List["ChildScheduleTest"]] = Field(
        None,
        description="분할 배치된 하위 작업 목록 (긴 작업이 여러 시간대로 나뉜 경우)"
    )


class PlannerErrorDetail(BaseModel):
    """[응답] 에러 상세 정보"""
    field: str = Field(..., description="에러 발생 필드명")
    reason: str = Field(..., description="에러 원인")


class PlannerGenerateResponseTest(BaseModel):
    """
    [응답] POST /ai/v1/planners Response Body (TEST).

    구성:
    - success: 성공 여부
    - processTime: 처리 시간 (초)
    - results: 성공 시 결과 목록 (실패 시 null)
    - errorCode/message/details/traceId: 실패 시 에러 정보 (성공 시 null)
    """
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="요청 처리 성공 여부")
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)")
    
    # 성공 시 필드
    results: Optional[List[PlannerScheduleResultTest]] = Field(None, description="배치 결과 목록")

    # 실패 시 필드
    error_code: Optional[str] = Field(None, alias="errorCode", description="에러 코드")
    message: Optional[str] = Field(None, description="에러 메시지")
    details: Optional[List[PlannerErrorDetail]] = Field(None, description="상세 에러 내역")
    trace_id: Optional[str] = Field(None, alias="traceId", description="트랜잭션/에러 추적 ID")
