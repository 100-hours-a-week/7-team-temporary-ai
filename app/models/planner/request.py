from pydantic import BaseModel
from typing import List, Optional, Literal

TimeZone = Literal["MORNING", "AFTERNOON", "EVENING", "NIGHT"]
TaskType = Literal["FIXED", "FLEX"]
EstimatedTimeRange = Literal["MINUTE_UNDER_30", "MINUTE_30_TO_60", "HOUR_1_TO_2"]

class UserInfo(BaseModel):
    userId: int
    focusTimeZone: TimeZone  # MORNING | AFTERNOON | EVENING | NIGHT
    dayEndTime: str          # "HH:MM"

class ScheduleItem(BaseModel):
    taskId: int
    parentScheduleId: Optional[int] = None
    dayPlanId: int
    title: str
    type: TaskType           # FIXED | FLEX
    startAt: Optional[str] = None
    endAt: Optional[str] = None
    estimatedTimeRange: Optional[EstimatedTimeRange] = None
    focusLevel: Optional[int] = None
    isUrgent: Optional[bool] = None



class ArrangementState(BaseModel):
    user: UserInfo
    startArrange: str
    schedules: List[ScheduleItem]
