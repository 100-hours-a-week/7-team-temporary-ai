from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# --- Request/Response Models ---

class PersonalizationIngestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_ids: list[int] = Field(..., alias="userIds", description="대상 사용자 ID 목록")
    target_date: date = Field(..., alias="targetDate", description="대상 날짜 (YYYY-MM-DD)")


class PersonalizationIngestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="성공 여부")
    user_ids: list[int] = Field(..., alias="userIds", description="처리 대상 사용자 ID 목록")
    message: str = Field(..., description="결과 메시지")
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)")


# --- 학습용 내부 모델 ---

class DraftFinalComparison(BaseModel):
    """태스크별 AI_DRAFT vs USER_FINAL 비교"""
    task_id: int
    category: str | None = None
    focus_level: int | None = None
    is_urgent: bool | None = None
    ai_assignment_status: str
    ai_start_at: str | None = None
    ai_end_at: str | None = None
    ai_importance_score: float | None = None
    user_assignment_status: str
    user_start_at: str | None = None
    user_end_at: str | None = None


class ComparisonResult(BaseModel):
    """한 user의 하루치 비교 결과"""
    user_id: int
    day_plan_id: int
    ai_fill_rate: float
    user_fill_rate: float
    focus_time_zone: str
    task_comparisons: list[DraftFinalComparison]


class WeightSignals(BaseModel):
    """가중치 업데이트용 신호값 (주간 누적 후 EMA 적용)"""
    s_focus: float = 0.0
    s_urgent: float = 0.0
    s_category: dict[str, float] = {}
    s_alpha_duration: float = 0.0
    s_included: float = 0.0
    s_excluded: float = 0.0
    s_overflow: float = 0.0
    s_focus_align: float = 0.0
    s_fatigue_risk: float = 0.0
    n_tasks_compared: int = 0

