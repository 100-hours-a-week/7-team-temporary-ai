from datetime import date, timedelta, datetime, timezone
from typing import Any
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal

class ReportRepository:
    def __init__(self, session: AsyncSession | None = None):
        self.session = session

    async def _get_session(self) -> AsyncSession:
        if self.session:
            return self.session
        return AsyncSessionLocal()

    async def fetch_past_4_weeks_data(self, user_id: int, base_date: date) -> list[dict[str, Any]]:
        """
        주간 레포트 생성을 위해 base_date 기준 과거 4주간(28일)의 사용자 플래너 기록 데이터를 조회합니다.
        """
        start_date = base_date - timedelta(days=28)
        end_date = base_date - timedelta(days=1)
        
        try:
            async with AsyncSessionLocal() as session:
                # 1. planner_records 조회
                # SQL: SELECT * FROM planner_records WHERE user_id = :u AND record_type = 'USER_FINAL' AND planner_date BETWEEN :s AND :e
                query = text("""
                    SELECT * FROM planner_records 
                    WHERE user_id = :user_id 
                      AND record_type = 'USER_FINAL'
                      AND planner_date >= :start_date
                      AND planner_date <= :end_date
                """)
                result = await session.execute(query, {
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date
                })
                records = [dict(row._mapping) for row in result]
                
                if not records:
                    return []
                
                record_ids = [r["id"] for r in records]
                
                # 2. record_tasks 조회
                tasks_query = text("SELECT * FROM record_tasks WHERE record_id = ANY(:record_ids)")
                tasks_result = await session.execute(tasks_query, {"record_ids": record_ids})
                tasks = [dict(row._mapping) for row in tasks_result]
                
                # 3. schedule_histories 조회
                histories_query = text("SELECT * FROM schedule_histories WHERE record_id = ANY(:record_ids)")
                histories_result = await session.execute(histories_query, {"record_ids": record_ids})
                histories = [dict(row._mapping) for row in histories_result]
                
                # 4. 데이터 조립 (Nest tasks and histories into records)
                for record in records:
                    record["record_tasks"] = [t for t in tasks if t["record_id"] == record["id"]]
                    record["schedule_histories"] = [h for h in histories if h["record_id"] == record["id"]]
                
                return records
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch past 4 weeks data for user {user_id}: {e}")
            return []

    async def upsert_weekly_report(self, report_id: int, user_id: int, base_date: date, content: str) -> bool:
        """
        생성된 주간 레포트를 weekly_reports 테이블에 저장(또는 갱신)합니다.
        """
        try:
            async with AsyncSessionLocal() as session:
                now = datetime.now(timezone.utc)
                # PostgreSQL ON CONFLICT (upsert)
                query = text("""
                    INSERT INTO weekly_reports (report_id, user_id, base_date, content, updated_at, created_at)
                    VALUES (:report_id, :user_id, :base_date, :content, :updated_at, :now)
                    ON CONFLICT (report_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = EXCLUDED.updated_at
                    RETURNING id
                """)
                result = await session.execute(query, {
                    "report_id": report_id,
                    "user_id": user_id,
                    "base_date": base_date,
                    "content": content,
                    "updated_at": now,
                    "now": now
                })
                await session.commit()
                return result.scalar() is not None
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to upsert weekly report {report_id}: {e}")
            return False

    async def fetch_user_id_by_report_id(self, report_id: int) -> int | None:
        """
        특정 report_id를 가진 레포트의 user_id를 조회합니다.
        """
        try:
            async with AsyncSessionLocal() as session:
                query = text("SELECT user_id FROM weekly_reports WHERE report_id = :report_id LIMIT 1")
                result = await session.execute(query, {"report_id": report_id})
                row = result.fetchone()
                return row[0] if row else None
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch user_id for report_id {report_id}: {e}")
            return None

    async def fetch_reports_by_targets(self, targets: list[Any]) -> list[dict[str, Any]]:
        """
        주어진 WeeklyReportTarget 리스트의 report_id들을 기반으로 레포트를 조회합니다.
        """
        if not targets:
            return []
            
        report_ids = [t.report_id for t in targets]
        
        try:
            async with AsyncSessionLocal() as session:
                query = text("SELECT * FROM weekly_reports WHERE report_id = ANY(:report_ids)")
                result = await session.execute(query, {"report_ids": report_ids})
                return [dict(row._mapping) for row in result]
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch weekly reports by targets: {e}")
            return []
