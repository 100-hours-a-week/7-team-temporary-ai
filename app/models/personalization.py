from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.planner.errors import PersonalizationErrorCode

# --- Enums ---


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class FocusTimeZone(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"
    NIGHT = "NIGHT"

class ScheduleStatus(str, Enum):
    TODO = "TODO"
    DONE = "DONE"

class TaskType(str, Enum):
    FIXED = "FIXED"
    FLEX = "FLEX"

class AssignedBy(str, Enum):
    USER = "USER"
    AI = "AI"

class AssignmentStatus(str, Enum):
    NOT_ASSIGNED = "NOT_ASSIGNED"
    ASSIGNED = "ASSIGNED"
    EXCLUDED = "EXCLUDED"

class EstimatedTimeRange(str, Enum):
    MINUTE_UNDER_30 = "MINUTE_UNDER_30"
    MINUTE_30_TO_60 = "MINUTE_30_TO_60"
    HOUR_1_TO_2 = "HOUR_1_TO_2"
    HOUR_2_TO_4 = "HOUR_2_TO_4"
    HOUR_OVER_4 = "HOUR_OVER_4"

class ScheduleHistoryEventType(str, Enum):
    ASSIGN_TIME = "ASSIGN_TIME"
    MOVE_TIME = "MOVE_TIME"
    CHANGE_DURATION = "CHANGE_DURATION"

# --- Type Aliases ---

TimeHHMM = Annotated[
    str,
    Field(
        pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$",
        description="24시간제 HH:MM 형식",
        examples=["09:30", "18:00", "23:59"],
    ),
]

def _hhmm_to_minutes(t: str) -> int:
    hh, mm = t.split(":")
    return int(hh) * 60 + int(mm)

# --- Sub Models ---

class PersonalizationUserInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: int = Field(..., alias="userId", description="Users.User_id")
    gender: Optional[Gender] = Field(None, description="Users.gender")
    age: Optional[int] = Field(None, ge=0, le=130, description="나이(정수, 백엔드 가공)")
    focus_time_zone: FocusTimeZone = Field(..., alias="focusTimeZone", description="몰입 시간대")
    day_end_time: TimeHHMM = Field(..., alias="dayEndTime", description="하루 마무리 시간(HH:MM)")


class ScheduleIngestItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_id: int = Field(..., alias="taskId", description="Schedule.Task_id")
    day_plan_id: int = Field(..., alias="dayPlanId", description="Schedule.dayPlanId")

    title: str = Field(..., max_length=60, description="작업 제목")
    status: Optional[ScheduleStatus] = Field(None, description="완료 상태")
    type: TaskType = Field(..., description="작업 타입")

    assigned_by: AssignedBy = Field(..., alias="assignedBy", description="배치 주체")
    assignment_status: AssignmentStatus = Field(..., alias="assignmentStatus", description="배치 상태")

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
    def _validate_rules(self) -> "ScheduleIngestItem":
        if self.assignment_status == AssignmentStatus.ASSIGNED:
            if self.start_at is None or self.end_at is None:
                raise ValueError("ASSIGNED 상태인 경우 startAt/endAt은 필수입니다.")
            if _hhmm_to_minutes(self.end_at) <= _hhmm_to_minutes(self.start_at):
                raise ValueError("endAt은 startAt보다 뒤여야 합니다.")
        return self


class ScheduleHistoryIngestItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schedule_id: int = Field(..., alias="scheduleId", description="ScheduleHistory.scheduleId (= taskId)")
    event_type: ScheduleHistoryEventType = Field(..., alias="eventType", description="이벤트 타입")

    prev_start_at: Optional[TimeHHMM] = Field(None, alias="prevStartAt", description="변경 전 시작(HH:MM)")
    prev_end_at: Optional[TimeHHMM] = Field(None, alias="prevEndAt", description="변경 전 종료(HH:MM)")

    new_start_at: Optional[TimeHHMM] = Field(None, alias="newStartAt", description="변경 후 시작(HH:MM)")
    new_end_at: Optional[TimeHHMM] = Field(None, alias="newEndAt", description="변경 후 종료(HH:MM)")

    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="이벤트 발생 시각(ISO 8601)",
    )


# --- Request/Response Models ---

class PersonalizationIngestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user: PersonalizationUserInput = Field(..., description="Users 기반 사용자 정보")
    schedules: List[ScheduleIngestItem] = Field(default_factory=list, description="Schedule 기반 작업 목록")
    schedule_histories: List[ScheduleHistoryIngestItem] = Field(
        default_factory=list,
        alias="scheduleHistories",
        description="ScheduleHistory 기반 변경 이력 목록",
    )


class PersonalizationIngestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="저장 성공 여부")
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)")
    message: str = Field(..., description="결과 메시지")
    error_code: Optional[PersonalizationErrorCode] = Field(None, alias="errorCode", description="에러 코드(실패 시)")

