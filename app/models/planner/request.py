from pydantic import BaseModel
from typing import AsyncGenerator, Annotated, Literal

TimeZone = Literal["MORNING", "AFTERNOON", "EVENING", "NIGHT"]
TaskType = Literal["FIXED", "FLEX"]
EstimatedTimeRange = Literal["MINUTE_UNDER_30", "MINUTE_30_TO_60", "HOUR_1_TO_2"]

class UserInfo(BaseModel):
    userId: int
    focusTimeZone: TimeZone  # MORNING | AFTERNOON | EVENING | NIGHT
    dayEndTime: str          # "HH:MM"

class ScheduleItem(BaseModel):
    taskId: int
    parentScheduleId: int | None = None
    dayPlanId: int
    title: str
    type: TaskType           # FIXED | FLEX
    startAt: str | None = None
    endAt: str | None = None
    estimatedTimeRange: EstimatedTimeRange | None = None
    focusLevel: int | None = None
    isUrgent: bool | None = None



class ArrangementState(BaseModel):
    user: UserInfo
    startArrange: str
    schedules: list[ScheduleItem]
