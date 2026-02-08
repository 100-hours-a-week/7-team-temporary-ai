from __future__ import annotations

from datetime import date
from typing import List

from pydantic import BaseModel, ConfigDict, Field


# --- Request/Response Models ---

class PersonalizationIngestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_ids: List[int] = Field(..., alias="userIds", description="대상 사용자 ID 목록")
    target_date: date = Field(..., alias="targetDate", description="대상 날짜 (YYYY-MM-DD)")


class PersonalizationIngestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(..., description="성공 여부")
    user_ids: List[int] = Field(..., alias="userIds", description="처리 대상 사용자 ID 목록")
    message: str = Field(..., description="결과 메시지")
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)")

