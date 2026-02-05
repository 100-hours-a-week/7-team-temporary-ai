from datetime import datetime
from typing import List, Dict, Any

from app.db.supabase_client import get_supabase_client
from app.models.personalization import (
    PersonalizationIngestRequest, 
    ScheduleIngestItem, 
    ScheduleHistoryIngestItem
)

class PersonalizationRepository:
    def __init__(self):
        self.client = get_supabase_client()

    async def save_ingest_data(self, request: PersonalizationIngestRequest) -> bool:
        """
        사용자 플래너 데이터 및 이력을 DB에 저장합니다.
        (planner_records -> record_tasks -> schedule_histories 순서)
        
        * 최적화(Batch Insert):
          일주일치(N일) 데이터를 저장할 때 N번 루프를 돌지 않고,
          1) planner_records 일괄 저장 (1회)
          2) 생성된 ID 매핑
          3) record_tasks 일괄 저장 (1회)
          4) schedule_histories 일괄 저장 (1회)
          총 3회의 DB 요청만 발생하도록 최적화.
        """
        
        # 0. 데이터 전처리
        if not request.schedules:
            return True
            
        task_to_day_map = {t.task_id: t.day_plan_id for t in request.schedules}
        
        schedules_by_day: Dict[int, List[ScheduleIngestItem]] = {}
        histories_by_day: Dict[int, List[ScheduleHistoryIngestItem]] = {}
        
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
        # 순서 보장을 위해 day_plan_id 목록 정렬
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
                "created_at": datetime.now().isoformat()
            }
            record_payloads.append(record_data)

        if not record_payloads:
            return True

        # 2. planner_records 일괄 저장 (Batch Insert)
        record_res = self.client.table("planner_records").insert(record_payloads).execute()
        if not record_res.data:
            raise Exception("Failed to batch insert planner_records")
            
        # [Mapper] day_plan_id -> record_id
        day_to_record_id = {r["day_plan_id"]: r["id"] for r in record_res.data}

        # 3. 자식 데이터(Tasks, Histories) 일괄 준비
        all_task_rows = []
        all_history_rows = []
        
        for day_plan_id in sorted_day_ids:
            record_id = day_to_record_id.get(day_plan_id)
            if not record_id:
                continue # 생성 실패한 경우? 스킵
            
            day_schedules = schedules_by_day[day_plan_id]
            day_histories = histories_by_day.get(day_plan_id, [])
            
            # Tasks
            for item in day_schedules:
                row = {
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
                    "category": None,
                    "cognitive_load": None,
                    "group_id": None,
                    "group_label": None,
                    "order_in_group": None,
                    "created_at": datetime.now().isoformat()
                }
                all_task_rows.append(row)
                
            # Histories
            for h in day_histories:
                h_row = {
                    "record_id": record_id,
                    "schedule_id": h.schedule_id,
                    "event_type": h.event_type.value,
                    "prev_start_at": h.prev_start_at,
                    "prev_end_at": h.prev_end_at,
                    "new_start_at": h.new_start_at,
                    "new_end_at": h.new_end_at,
                    "created_at_client": h.created_at.isoformat(),
                    "created_at_server": datetime.now().isoformat()
                }
                all_history_rows.append(h_row)

        # 4. 자식 데이터 일괄 저장
        if all_task_rows:
            self.client.table("record_tasks").insert(all_task_rows).execute()
            
        if all_history_rows:
            self.client.table("schedule_histories").insert(all_history_rows).execute()

        return True

    def _calculate_fill_rate(self, schedules: List[ScheduleIngestItem], day_end_time: str) -> float:
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
