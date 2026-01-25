from pydantic import BaseModel, Field
from typing import List, Optional, Literal

AssignmentStatus = Literal["ASSIGNED", "EXCLUDED"]
AssignedBy = Literal["AI", "USER"]

class SubTaskResult(BaseModel):
    startAt: str
    endAt: str
    durationMin: int

class AssignmentResult(BaseModel):
    taskId: int
    title: str
    assignmentStatus: AssignmentStatus
    assignedBy: AssignedBy = "AI"
    startAt: Optional[str] = None
    endAt: Optional[str] = None
    dayPlanId: int
    children: Optional[List[SubTaskResult]] = None

class PlannerResponse(BaseModel):
    results: List[AssignmentResult]
    message: str = "Planner generated successfully"
