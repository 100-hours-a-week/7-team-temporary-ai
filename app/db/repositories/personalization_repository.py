import json
from datetime import datetime
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.models.personalization import (
    PersonalizationIngestRequest, 
    ScheduleIngestItem
)

class PersonalizationRepository:
    async def save_ingest_data(self, request: PersonalizationIngestRequest) -> bool:
        """
        사용자 플래너 데이터 및 이력을 DB에 저장합니다.
        """
        if not request.schedules:
            return True
            
        task_to_day_map = {t.task_id: t.day_plan_id for t in request.schedules}
        schedules_by_day = {}
        histories_by_day = {}
        
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

        try:
            async with AsyncSessionLocal() as session:
                day_to_record_id = {}
                sorted_day_ids = sorted(schedules_by_day.keys())
                
                # 1. Insert planner_records
                for day_plan_id in sorted_day_ids:
                    day_schedules = schedules_by_day[day_plan_id]
                    fill_rate = self._calculate_fill_rate(day_schedules, request.user.day_end_time)
                    
                    record_query = text("""
                        INSERT INTO planner_records (
                            user_id, day_plan_id, record_type, start_arrange, day_end_time, 
                            focus_time_zone, user_age, user_gender, total_tasks, 
                            assigned_count, excluded_count, fill_rate, created_at
                        ) VALUES (
                            :user_id, :day_plan_id, :record_type, :start_arrange, :day_end_time, 
                            :focus_time_zone, :user_age, :user_gender, :total_tasks, 
                            :assigned_count, :excluded_count, :fill_rate, :created_at
                        ) RETURNING id
                    """)
                    res = await session.execute(record_query, {
                        "user_id": request.user.user_id,
                        "day_plan_id": day_plan_id,
                        "record_type": "USER_FINAL",
                        "start_arrange": "00:00",
                        "day_end_time": request.user.day_end_time,
                        "focus_time_zone": request.user.focus_time_zone.value,
                        "user_age": request.user.age,
                        "user_gender": request.user.gender.value if request.user.gender else None,
                        "total_tasks": len([s for s in day_schedules if s.type.value == "FLEX"]),
                        "assigned_count": len([s for s in day_schedules if s.assignment_status.value == "ASSIGNED"]),
                        "excluded_count": len([s for s in day_schedules if s.assignment_status.value == "EXCLUDED"]),
                        "fill_rate": fill_rate,
                        "created_at": datetime.now()
                    })
                    day_to_record_id[day_plan_id] = res.scalar()

                # 2. Insert record_tasks & schedule_histories
                task_rows = []
                history_rows = []
                for day_plan_id in sorted_day_ids:
                    record_id = day_to_record_id.get(day_plan_id)
                    if not record_id: continue
                    
                    for item in schedules_by_day[day_plan_id]:
                        task_rows.append({
                            "record_id": record_id, "task_id": item.task_id, "day_plan_id": item.day_plan_id,
                            "title": item.title, "status": item.status.value if item.status else None,
                            "task_type": item.type.value, "assigned_by": item.assigned_by.value,
                            "assignment_status": item.assignment_status.value, "start_at": item.start_at,
                            "end_at": item.end_at, "estimated_time_range": item.estimated_time_range.value if item.estimated_time_range else None,
                            "focus_level": item.focus_level, "is_urgent": item.is_urgent, "created_at": datetime.now()
                        })
                        
                    for h in histories_by_day.get(day_plan_id, []):
                        history_rows.append({
                            "record_id": record_id, "schedule_id": h.schedule_id, "event_type": h.event_type.value,
                            "prev_start_at": h.prev_start_at, "prev_end_at": h.prev_end_at,
                            "new_start_at": h.new_start_at, "new_end_at": h.new_end_at,
                            "created_at_client": h.created_at, "created_at_server": datetime.now()
                        })

                if task_rows:
                    await session.execute(text("""
                        INSERT INTO record_tasks (
                            record_id, task_id, day_plan_id, title, status, task_type, 
                            assigned_by, assignment_status, start_at, end_at, 
                            estimated_time_range, focus_level, is_urgent, created_at
                        ) VALUES (
                            :record_id, :task_id, :day_plan_id, :title, :status, :task_type, 
                            :assigned_by, :assignment_status, :start_at, :end_at, 
                            :estimated_time_range, :focus_level, :is_urgent, :created_at
                        )
                    """), task_rows)
                    
                if history_rows:
                    await session.execute(text("""
                        INSERT INTO schedule_histories (
                            record_id, schedule_id, event_type, prev_start_at, prev_end_at, 
                            new_start_at, new_end_at, created_at_client, created_at_server
                        ) VALUES (
                            :record_id, :schedule_id, :event_type, :prev_start_at, :prev_end_at, 
                            :new_start_at, :new_end_at, :created_at_client, :created_at_server
                        )
                    """), history_rows)

                await session.commit()
                return True
        except Exception as e:
            print(f"[PersonalizationRepository] save_ingest_data Error: {e}")
            return False

    def _calculate_fill_rate(self, schedules: list[ScheduleIngestItem], day_end_time: str) -> float:
        try:
            hh, mm = map(int, day_end_time.split(":"))
            total_minutes = hh * 60 + mm
            if total_minutes == 0: return 0.0
            used_minutes = 0
            for s in schedules:
                if s.assignment_status.value == "ASSIGNED" and s.start_at and s.end_at:
                    try:
                        sh, sm = map(int, s.start_at.split(":"))
                        eh, em = map(int, s.end_at.split(":"))
                        duration = (eh * 60 + em) - (sh * 60 + sm)
                        if duration > 0: used_minutes += duration
                    except ValueError: continue
            return round(used_minutes / total_minutes, 4)
        except: return 0.0
