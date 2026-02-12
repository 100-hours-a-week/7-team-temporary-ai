from __future__ import annotations

from datetime import date
from typing import List
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

class WeeklyReportTarget(BaseModel):
    """
    [요청] 주간 레포트 생성 대상 (사용자별)
    """
    model_config = ConfigDict(populate_by_name=True)

    report_id: int = Field(..., alias="reportId", description="레포트 ID(BIGINT)")
    user_id: int = Field(..., alias="userId", description="Users.User_id(BIGINT)")



def load_example(filename: str) -> dict:
    try:
        # 프로젝트 루트 기준 (app/main.py 실행 위치 가정)
        path = Path(f"tests/data/{filename}")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

class WeeklyReportGenerateRequest(BaseModel):
    """
    [요청] POST /ai/v2/reports/weekly
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": load_example("weekly_report_request.json")
        }
    )

    base_date: date = Field(..., alias="baseDate", description="기준 날짜(Monday, YYYY-MM-DD)")
    users: List[WeeklyReportTarget] = Field(..., description="생성 대상 목록", min_length=1)


class WeeklyReportGenerateResponse(BaseModel):
    """
    [응답] POST /ai/v2/reports/weekly
    """
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": load_example("weekly_report_response.json")
        }
    )

    success: bool = Field(..., description="배치 작업 성공 여부")
    process_time: float = Field(..., alias="processTime", description="서버 처리 시간(초)")

    count: int = Field(..., description="처리 대상 수")
    message: str = Field(..., description="결과 메시지")
