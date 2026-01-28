from pydantic import BaseModel, Field
from typing import List, Optional, Literal

AssignmentStatus = Literal["ASSIGNED", "EXCLUDED"]
AssignedBy = Literal["AI", "USER"]

class SubTaskResult(BaseModel):
    title: str = Field(..., description="원본 제목 + ' - n'")
    startAt: str = Field(..., description="HH:MM")
    endAt: str = Field(..., description="HH:MM")

class AssignmentResult(BaseModel):
    taskId: int
    dayPlanId: int
    title: str = Field(..., description="원본 작업 제목")
    type: str = Field(..., description="'FIXED' | 'FLEX'")
    assignedBy: AssignedBy = "AI"
    assignmentStatus: str = Field(..., description="'ASSIGNED' | 'EXCLUDED' | 'NOT_ASSIGNED'")
    startAt: Optional[str] = None
    endAt: Optional[str] = None
    children: Optional[List[SubTaskResult]] = None

class PlannerResponse(BaseModel):
    success: bool
    processTime: float
    results: List[AssignmentResult]
    message: str = "Planner generated successfully"
