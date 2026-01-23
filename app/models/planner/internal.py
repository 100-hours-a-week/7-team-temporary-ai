from pydantic import BaseModel
from typing import List, Optional, Dict, Literal
from app.models.planner.request import TimeZone

class FreeSession(BaseModel):
    start: int  # minutes from midnight
    end: int    # minutes from midnight
    duration: int
    timeZoneProfile: Dict[TimeZone, int]  # zone별 포함된 분

class TaskFeature(BaseModel):
    taskId: int
    
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

class ChainCandidate(BaseModel):
    chainId: str
    timeZoneQueues: Dict[TimeZone, List[int]]  # zone -> list of taskIds
    rationaleTags: List[str] = []
