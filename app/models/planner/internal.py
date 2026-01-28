from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field
from app.models.planner.request import TimeZone, ArrangementState, ScheduleItem
from app.models.planner.weights import WeightParams
from app.models.planner.response import AssignmentResult

class FreeSession(BaseModel):
    start: int  # minutes from midnight
    end: int    # minutes from midnight
    duration: int
    timeZoneProfile: Dict[TimeZone, int]  # zone별 포함된 분

class TaskFeature(BaseModel):
    taskId: int
    dayPlanId: int
    title: str
    type: str # TaskType literal but str ok due to circular imports avoidance or reuse

    
    # Node1: Structure Analysis
    category: Optional[str] = None
    cognitiveLoad: Optional[Literal["LOW", "MED", "HIGH"]] = None
    groupId: Optional[str] = None
    groupLabel: Optional[str] = None
    orderInGroup: Optional[int] = None
    
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
    timeZoneQueues: Dict[TimeZone, List[int]]  # zone -> list of taskIds
    rationaleTags: List[str] = []

class PlannerGraphState(BaseModel):
    request: ArrangementState
    weights: WeightParams

    fixedTasks: List[ScheduleItem] = Field(default_factory=list)
    flexTasks: List[ScheduleItem] = Field(default_factory=list)

    freeSessions: List[FreeSession] = Field(default_factory=list)
    taskFeatures: Dict[int, TaskFeature] = Field(default_factory=dict)

    chainCandidates: List[ChainCandidate] = Field(default_factory=list)
    selectedChainId: Optional[str] = None

    finalResults: List[AssignmentResult] = Field(default_factory=list)

    # retries / diagnostics
    retry_node1: int = 0
    retry_node3: int = 0
    replan_loops: int = 0
    warnings: List[str] = Field(default_factory=list)
    fillRate: float = 1.0

