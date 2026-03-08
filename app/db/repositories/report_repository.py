import asyncio
from datetime import date, timedelta, datetime, timezone
from typing import AsyncGenerator, Annotated, Any
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

class ReportRepository:
    def __init__(self):
        pass

    async def fetch_past_4_weeks_data(self, user_id: int, base_date: date) -> list[dict[str, Any]]:
        """
        주간 레포트 생성을 위해 base_date 기준 과거 4주간(28일)의 사용자 플래너 기록 데이터를 조회합니다.
        """
        start_date = base_date - timedelta(days=28)
        end_date = base_date - timedelta(days=1)
        
        try:
            # Query with joins or multiple queries to match the "record_tasks(*), schedule_histories(*)" behavior
            # In Supabase SDK, it nest them. In raw SQL, we might need to perform nested queries or map the join results.
            # To minimize change, let's fetch them separately and group them.
            
            async with AsyncSessionLocal() as session:
                # 1. Fetch records
                stmt = text("""
                    SELECT * FROM planner_records 
                    WHERE user_id = :user_id 
                    AND record_type = 'USER_FINAL'
                    AND plan_date >= :start_date 
                    AND plan_date <= :end_date
                """)
                res = await session.execute(stmt, {
                    "user_id": user_id,
                    "start_date": start_date,
                    "end_date": end_date
                })
                # Convert ResultProxy rows to dicts
                records = [dict(r._mapping) for r in res.fetchall()]
                
                if not records:
                    return []
                
                record_ids = [r["id"] for r in records]
                
                # 2. Fetch tasks
                task_stmt = text("SELECT * FROM record_tasks WHERE record_id = ANY(:ids)")
                task_res = await session.execute(task_stmt, {"ids": record_ids})
                tasks = [dict(r._mapping) for r in task_res.fetchall()]
                
                # 3. Fetch histories
                hist_stmt = text("SELECT * FROM schedule_histories WHERE record_id = ANY(:ids)")
                hist_res = await session.execute(hist_stmt, {"ids": record_ids})
                histories = [dict(r._mapping) for r in hist_res.fetchall()]
                
                # 4. Nest them
                tasks_by_record = {}
                for t in tasks:
                    tasks_by_record.setdefault(t["record_id"], []).append(t)
                    
                hists_by_record = {}
                for h in histories:
                    hists_by_record.setdefault(h["record_id"], []).append(h)
                    
                for r in records:
                    r["record_tasks"] = tasks_by_record.get(r["id"], [])
                    r["schedule_histories"] = hists_by_record.get(r["id"], [])
                    
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
                # PostgreSQL ON CONFLICT (upsert)
                stmt = text("""
                    INSERT INTO weekly_reports (report_id, user_id, base_date, content, updated_at)
                    VALUES (:report_id, :user_id, :base_date, :content, :updated_at)
                    ON CONFLICT (report_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        updated_at = EXCLUDED.updated_at
                    RETURNING report_id
                """)
                res = await session.execute(stmt, {
                    "report_id": report_id,
                    "user_id": user_id,
                    "base_date": base_date,
                    "content": content,
                    "updated_at": datetime.now(timezone.utc)
                })
                await session.commit()
                return res.scalar() is not None
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
                stmt = text("SELECT user_id FROM weekly_reports WHERE report_id = :id")
                res = await session.execute(stmt, {"id": report_id})
                return res.scalar()
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
                stmt = text("SELECT * FROM weekly_reports WHERE report_id = ANY(:ids)")
                res = await session.execute(stmt, {"ids": report_ids})
                return [dict(r._mapping) for r in res.fetchall()]
        except Exception as e:
            import logging
            logging.error(f"[ReportRepository] Failed to fetch weekly reports by targets: {e}")
            return []
