from sqlalchemy import text
from datetime import datetime, date
from app.db.session import AsyncSessionLocal
from app.models.personalization import PersonalizationIngestRequest
import json


class PersonalizationRepository:
    def __init__(self):
        pass

    async def fetch_draft_final_pairs(
        self, user_id: int, start_date: date, end_date: date
    ) -> list[dict]:
        """
        해당 기간의 AI_DRAFT + USER_FINAL 쌍을 day_plan_id로 매칭하여 반환.
        같은 day_plan_id에 두 타입이 모두 있는 경우만 반환한다.
        """
        async with AsyncSessionLocal() as session:
            stmt = text("""
                WITH paired AS (
                    SELECT day_plan_id
                    FROM planner_records
                    WHERE user_id = :user_id
                      AND planner_date >= :start_date
                      AND planner_date <= :end_date
                    GROUP BY day_plan_id
                    HAVING COUNT(DISTINCT record_type) FILTER (
                        WHERE record_type IN ('AI_DRAFT', 'USER_FINAL')
                    ) = 2
                )
                SELECT pr.id, pr.day_plan_id, pr.record_type, pr.fill_rate,
                       pr.assigned_count, pr.excluded_count, pr.focus_time_zone,
                       pr.weights_version, pr.created_at
                FROM planner_records pr
                JOIN paired p ON pr.day_plan_id = p.day_plan_id
                WHERE pr.user_id = :user_id
                  AND pr.record_type IN ('AI_DRAFT', 'USER_FINAL')
                ORDER BY pr.day_plan_id, pr.record_type
            """)
            result = await session.execute(stmt, {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
            })
            rows = result.fetchall()
            return [dict(r._mapping) for r in rows]

    async def fetch_record_tasks(self, record_ids: list[int]) -> list[dict]:
        """
        여러 record_id의 FLEX record_tasks를 한번에 조회.
        """
        if not record_ids:
            return []

        async with AsyncSessionLocal() as session:
            stmt = text("""
                SELECT rt.record_id, rt.task_id, rt.title, rt.category,
                       rt.focus_level, rt.is_urgent,
                       rt.assignment_status, rt.assigned_by,
                       rt.start_at, rt.end_at,
                       rt.importance_score, rt.fatigue_cost,
                       rt.estimated_time_range
                FROM record_tasks rt
                WHERE rt.record_id = ANY(:record_ids)
                  AND rt.task_type = 'FLEX'
                ORDER BY rt.task_id
            """)
            result = await session.execute(stmt, {"record_ids": record_ids})
            rows = result.fetchall()
            return [dict(r._mapping) for r in rows]

    async def fetch_current_weights(self, user_id: int) -> dict | None:
        """
        user_weights 테이블에서 해당 유저의 최신 가중치 조회.
        없으면 None 반환.
        """
        async with AsyncSessionLocal() as session:
            stmt = text("""
                SELECT weights, version
                FROM user_weights
                WHERE user_id = :user_id
                ORDER BY version DESC
                LIMIT 1
            """)
            result = await session.execute(stmt, {"user_id": user_id})
            row = result.fetchone()
            if row is None:
                return None
            mapping = dict(row._mapping)
            weights = mapping["weights"]
            if isinstance(weights, str):
                weights = json.loads(weights)
            return {"weights": weights, "version": mapping["version"]}

    async def save_weights(
        self, user_id: int, weights_dict: dict, new_version: int
    ) -> None:
        """
        user_weights UPSERT: user_id 기준으로 INSERT 또는 UPDATE.
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = text("""
                    INSERT INTO user_weights (user_id, weights, version, updated_at)
                    VALUES (:user_id, :weights::jsonb, :version, NOW())
                    ON CONFLICT (user_id) DO UPDATE SET
                        weights = :weights::jsonb,
                        version = :version,
                        updated_at = NOW()
                """)
                await session.execute(stmt, {
                    "user_id": user_id,
                    "weights": json.dumps(weights_dict),
                    "version": new_version,
                })
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

    async def save_ingest_data(self, request) -> bool:
        """
        사용자 플래너 데이터 및 이력을 DB에 저장합니다.
        (planner_records -> record_tasks -> schedule_histories 순서)
        """

        # 0. 데이터 전처리
        if not request.schedules:
            return True
            
        task_to_day_map = {t.task_id: t.day_plan_id for t in request.schedules}
        
        schedules_by_day: dict[int, list] = {}
        histories_by_day: dict[int, list] = {}
        
        for item in request.schedules:
            if item.day_plan_id not in schedules_by_day:
                schedules_by_day[item.day_plan_id] = []
                histories_by_day[item.day_plan_id] = []
            schedules_by_day[item.day_plan_id].append(item)
            
        if request.schedule_histories:
            for h in request.schedule_histories:
                day_id = task_to_day_map.get(h.schedule_id)
                if day_id and day_id in histories_by_day:
                    histories_by_day[day_id].append(h)

        # 1. planner_records 일괄 데이터 준비
        record_payloads = []
        sorted_day_ids = sorted(schedules_by_day.keys())
        
        for day_plan_id in sorted_day_ids:
            day_schedules = schedules_by_day[day_plan_id]
            fill_rate = self._calculate_fill_rate(day_schedules, request.user.day_end_time)
            
            record_data = {
                "user_id": request.user.user_id,
                "day_plan_id": day_plan_id,
                "record_type": "USER_FINAL",
                "start_arrange": "00:00",
                "day_end_time": request.user.day_end_time,
                "focus_time_zone": request.user.focus_time_zone.value,
                "user_age": request.user.age,
                "user_gender": request.user.gender.value if request.user.gender else None,
                "total_tasks": len([s for s in day_schedules if s.type == "FLEX"]),
                "assigned_count": len([s for s in day_schedules if s.assignment_status == "ASSIGNED"]),
                "excluded_count": len([s for s in day_schedules if s.assignment_status == "EXCLUDED"]),
                "fill_rate": fill_rate,
                "weights_version": None,
                "created_at": datetime.now()
            }
            record_payloads.append(record_data)

        if not record_payloads:
            return True

        async with AsyncSessionLocal() as session:
            try:
                # 2. planner_records 일괄 저장 (Batch Insert with RETURNING)
                # Note: asyncpg supports multiple rows in insert with RETURNING id
                stmt = text("""
                    INSERT INTO planner_records (
                        user_id, day_plan_id, record_type, start_arrange, day_end_time, 
                        focus_time_zone, user_age, user_gender, total_tasks, 
                        assigned_count, excluded_count, fill_rate, weights_version, created_at
                    ) VALUES (
                        :user_id, :day_plan_id, :record_type, :start_arrange, :day_end_time, 
                        :focus_time_zone, :user_age, :user_gender, :total_tasks, 
                        :assigned_count, :excluded_count, :fill_rate, :weights_version, :created_at
                    ) RETURNING id, day_plan_id
                """)
                
                # We need to execute multiple inserts and get multiple IDs.
                # SQLAlchemy's execute(stmt, record_payloads) with RETURNING is tricky with multiple rows.
                # For PostgreSQL, we can use a single multi-row INSERT or loop.
                # Given we want to preserve "Batch" logic, let's use a simpler mapping approach if needed.
                
                inserted_records = []
                for payload in record_payloads:
                    res = await session.execute(stmt, payload)
                    inserted_records.append(res.fetchone())
                
                # [Mapper] day_plan_id -> record_id
                day_to_record_id = {r.day_plan_id: r.id for r in inserted_records}

                # 3. 자식 데이터(Tasks, Histories) 일괄 준비
                all_task_rows = []
                all_history_rows = []
                
                for day_plan_id in sorted_day_ids:
                    record_id = day_to_record_id.get(day_plan_id)
                    if not record_id:
                        continue
                    
                    day_schedules = schedules_by_day[day_plan_id]
                    day_histories = histories_by_day.get(day_plan_id, [])
                    
                    for item in day_schedules:
                        all_task_rows.append({
                            "record_id": record_id,
                            "task_id": item.task_id,
                            "day_plan_id": item.day_plan_id,
                            "title": item.title,
                            "status": item.status.value if item.status else None,
                            "task_type": item.type.value,
                            "assigned_by": item.assigned_by.value,
                            "assignment_status": item.assignment_status.value,
                            "start_at": item.start_at,
                            "end_at": item.end_at,
                            "estimated_time_range": item.estimated_time_range.value if item.estimated_time_range else None,
                            "focus_level": item.focus_level,
                            "is_urgent": item.is_urgent,
                            "created_at": datetime.now()
                        })
                        
                    for h in day_histories:
                        all_history_rows.append({
                            "record_id": record_id,
                            "schedule_id": h.schedule_id,
                            "event_type": h.event_type.value,
                            "prev_start_at": h.prev_start_at,
                            "prev_end_at": h.prev_end_at,
                            "new_start_at": h.new_start_at,
                            "new_end_at": h.new_end_at,
                            "created_at_client": h.created_at,
                            "created_at_server": datetime.now()
                        })

                # 4. 자식 데이터 일괄 저장
                if all_task_rows:
                    task_stmt = text("""
                        INSERT INTO record_tasks (
                            record_id, task_id, day_plan_id, title, status, task_type, 
                            assigned_by, assignment_status, start_at, end_at, 
                            estimated_time_range, focus_level, is_urgent, created_at
                        ) VALUES (
                            :record_id, :task_id, :day_plan_id, :title, :status, :task_type, 
                            :assigned_by, :assignment_status, :start_at, :end_at, 
                            :estimated_time_range, :focus_level, :is_urgent, :created_at
                        )
                    """)
                    # SQLAlchemy execute for multiple rows
                    await session.execute(task_stmt, all_task_rows)
                    
                if all_history_rows:
                    hist_stmt = text("""
                        INSERT INTO schedule_histories (
                            record_id, schedule_id, event_type, prev_start_at, prev_end_at, 
                            new_start_at, new_end_at, created_at_client, created_at_server
                        ) VALUES (
                            :record_id, :schedule_id, :event_type, :prev_start_at, :prev_end_at, 
                            :new_start_at, :new_end_at, :created_at_client, :created_at_server
                        )
                    """)
                    await session.execute(hist_stmt, all_history_rows)

                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"[PersonalizationRepository] Error: {e}")
                raise e

    def _calculate_fill_rate(self, schedules: list, day_end_time: str) -> float:
        """
        가동률(Fill Rate) 계산
        - 분모: 00:00 ~ day_end_time 까지의 총 분
        - 분자: ASSIGNED 상태인 작업들의 총 수행 시간 (분)
        """
        try:
            # 1. Total Capacity (00:00 ~ day_end_time)
            hh, mm = map(int, day_end_time.split(":"))
            total_minutes = hh * 60 + mm
            
            if total_minutes == 0:
                return 0.0

            # 2. Used Capacity
            used_minutes = 0
            for s in schedules:
                if s.assignment_status.value == "ASSIGNED" and s.start_at and s.end_at:
                    try:
                        sh, sm = map(int, s.start_at.split(":"))
                        eh, em = map(int, s.end_at.split(":"))
                        
                        start_min = sh * 60 + sm
                        end_min = eh * 60 + em
                        
                        duration = end_min - start_min
                        if duration > 0:
                            used_minutes += duration
                    except ValueError:
                        continue # 시간 형식 오류 시 무시

            # 3. Calculate Rate
            rate = used_minutes / total_minutes
            return round(rate, 4)
            
        except Exception as e:
            print(f"[_calculate_fill_rate] Error: {e}")
            return 0.0
