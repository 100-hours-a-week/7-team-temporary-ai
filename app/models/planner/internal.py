from typing import AsyncGenerator, Annotated, Literal
from pydantic import BaseModel, Field
from app.models.planner.request import TimeZone, ArrangementState, ScheduleItem
from app.models.planner.weights import WeightParams
from app.models.planner.response import AssignmentResult

class FreeSession(BaseModel):
    start: int  # minutes from midnight
    end: int    # minutes from midnight
    duration: int
    timeZoneProfile: dict[TimeZone, int]  # zone별 포함된 분

class TaskFeature(BaseModel):
    taskId: int
    dayPlanId: int
    title: str
    type: str # TaskType literal but str ok due to circular imports avoidance or reuse

    
    # Node1: Structure Analysis
    category: str | None = None
    cognitiveLoad: Literal["LOW", "MED", "HIGH"] | None = None
    groupId: str | None = None
    groupLabel: str | None = None
    orderInGroup: int | None = None
    
    # Node2: Importance
    importanceScore: float = 0.0
    fatigueCost: float = 0.0
    durationAvgMin: int = 0
    durationPlanMin: int = 0
    durationMinChunk: int = 0
    durationMaxChunk: int = 0
    combined_embedding_text: str = ""

class ChainCandidate(BaseModel):
    chainId: str
    timeZoneQueues: dict[TimeZone, list[int]]  # zone -> list of taskIds
    rationaleTags: list[str] = []

class PlannerGraphState(BaseModel):
    request: ArrangementState
    weights: WeightParams

    fixedTasks: list[ScheduleItem] = Field(default_factory=list)
    flexTasks: list[ScheduleItem] = Field(default_factory=list)

    freeSessions: list[FreeSession] = Field(default_factory=list)
    taskFeatures: dict[int, TaskFeature] = Field(default_factory=dict)

    chainCandidates: list[ChainCandidate] = Field(default_factory=list)
    selectedChainId: str | None = None

    finalResults: list[AssignmentResult] = Field(default_factory=list)

    # retries / diagnostics
    retry_node1: int = 0
    retry_node3: int = 0
    replan_loops: int = 0
    warnings: list[str] = Field(default_factory=list)
    fillRate: float = 1.0

