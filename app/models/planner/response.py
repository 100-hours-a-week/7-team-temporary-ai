from pydantic import BaseModel, Field
from typing import AsyncGenerator, Annotated, Literal

AssignmentStatus = Literal["ASSIGNED", "EXCLUDED"]
AssignedBy = Literal["AI", "USER"]

class SubTaskResult(BaseModel):
    title: str = Field(..., description="원본 제목 + ' - n'")
    startAt: str = Field(..., description="HH:MM")
    endAt: str = Field(..., description="HH:MM")

class AssignmentResult(BaseModel):
    userId: int
    taskId: int
    dayPlanId: int
    title: str = Field(..., description="원본 작업 제목")
    type: str = Field(..., description="'FIXED' | 'FLEX'")
    assignedBy: AssignedBy = "AI"
    assignmentStatus: str = Field(..., description="'ASSIGNED' | 'EXCLUDED' | 'NOT_ASSIGNED'")
    startAt: str | None = None
    endAt: str | None = None
    children: list[SubTaskResult] | None = None

class PlannerErrorDetail(BaseModel):
    field: str
    reason: str

class PlannerResponse(BaseModel):
    success: bool
    processTime: float
    results: list[AssignmentResult] | None = None
    message: str = "Planner generated successfully"
    errorCode: str | None = None
    details: list[PlannerErrorDetail] | None = None
    traceId: str | None = None
