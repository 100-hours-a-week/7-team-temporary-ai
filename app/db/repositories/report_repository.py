import asyncio
from datetime import date, timedelta, datetime, timezone
from typing import AsyncGenerator, Annotated, Any

from app.db.supabase_client import get_supabase_client

class ReportRepository:
    def __init__(self):
        self.client = get_supabase_client()

    async def fetch_past_4_weeks_data(self, user_id: int, base_date: date) -> list[dict[str, Any]]:
        """
        주간 레포트 생성을 위해 base_date 기준 과거 4주간(28일)의 사용자 플래너 기록 데이터를 조회합니다.
        (planner_records 및 하위 record_tasks 포함, USER_FINAL 타입만 조회 여부 고려)
        """
        start_date = base_date - timedelta(days=28)
        end_date = base_date - timedelta(days=1)
        
        try:
            # planner_records 와 그에 딸린 record_tasks, schedule_histories 를 함께 가져옴
            query = (
                self.client.table("planner_records")
                .select("*, record_tasks(*), schedule_histories(*)")
                .eq("user_id", user_id)
                .eq("record_type", "USER_FINAL")
                .gte("plan_date", start_date.isoformat())
                .lte("plan_date", end_date.isoformat())
            )
            # Sync I/O를 비동기로 위임시켜 메인 이벤트 루프 차단 방지
            response = await asyncio.to_thread(query.execute)
            
            return response.data if response.data else []
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch past 4 weeks data for user {user_id}: {e}")
            return []

    async def upsert_weekly_report(self, report_id: int, user_id: int, base_date: date, content: str) -> bool:
        """
        생성된 주간 레포트를 weekly_reports 테이블에 저장(또는 갱신)합니다.
        """
        payload = {
            "report_id": report_id,
            "user_id": user_id,
            "base_date": base_date.isoformat(),
            "content": content,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # report_id가 Unique Key 이므로 upsert 사용
            query = self.client.table("weekly_reports").upsert(payload, on_conflict="report_id")
            # Sync I/O를 비동기로 위임시켜 메인 이벤트 루프 차단 방지
            response = await asyncio.to_thread(query.execute)
            
            if response.data:
                return True
            return False
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to upsert weekly report {report_id}: {e}")
            return False

    async def fetch_reports_by_targets(self, targets: list[Any]) -> list[dict[str, Any]]:
        """
        주어진 WeeklyReportTarget 리스트의 report_id들을 기반으로 레포트를 조회합니다.
        """
        if not targets:
            return []
            
        report_ids = [t.report_id for t in targets]
        
        try:
            query = (
                self.client.table("weekly_reports")
                .select("*")
                .in_("report_id", report_ids)
            )
            response = await asyncio.to_thread(query.execute)
            return response.data if response.data else []
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch weekly reports by targets: {e}")
            return []
