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
        """
        # 1. planner_records 생성 (USER_FINAL)
        # 주의: request에 start_arrange가 없으므로 API 명세/DB 스키마에 따라
        #       해당 필드가 필수라면 임의값("00:00") 혹은 NULL 처리 필요.
        #       현재 DB 스키마는 NOT NULL이므로 "00:00"으로 처리하거나
        #       API Request 모델에 startArrange 추가를 고려해야 함.
        #       여기서는 임시로 "00:00" 사용.
        
        # day_plan_id는 schedule 중 하나에서 가져오거나 해야 하는데
        # Request Body root에는 dayPlanId가 없음.
        # schedule 아이템들의 dayPlanId가 모두 같다고 가정하고 첫 번째에서 추출하거나,
        # 만약 schedule이 비어있다면 저장할 의미가 낮음.
        
        day_plan_id = 0
        if request.schedules:
            day_plan_id = request.schedules[0].day_plan_id

        record_data = {
            "user_id": request.user.user_id,
            "day_plan_id": day_plan_id,
            "record_type": "USER_FINAL",
            "start_arrange": "00:00",  # Request에 없음, 기본값
            "day_end_time": request.user.day_end_time,
            "focus_time_zone": request.user.focus_time_zone.value,
            "user_age": request.user.age,
            "user_gender": request.user.gender.value if request.user.gender else None,
            
            # 통계 (단순 계산)
            "total_tasks": len([s for s in request.schedules if s.type == "FLEX"]),
            "assigned_count": len([s for s in request.schedules if s.assignment_status == "ASSIGNED"]),
            "excluded_count": len([s for s in request.schedules if s.assignment_status == "EXCLUDED"]),
            "fill_rate": 0.0, # 계산 로직 복잡하므로 0.0 처리 (필요 시 추가 구현)
            
            # AI Draft 관련 필드는 null
            "weights_version": None,
            
            "created_at": datetime.now().isoformat()
        }
        
        record_res = self.client.table("planner_records").insert(record_data).execute()
        
        if not record_res.data:
            raise Exception("Failed to insert planner_records: No data returned")
            
        record_id = record_res.data[0]["id"]

        # 2. record_tasks 일괄 저장
        if request.schedules:
            task_rows = []
            for item in request.schedules:
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
                    
                    # USER_FINAL 레코드이므로 AI 분석 결과(category 등)는 
                    # 백엔드가 안 보내주면 null. (API 명세상 request에 없음)
                    "category": None,
                    "cognitive_load": None,
                    "group_id": None,
                    "group_label": None,
                    "order_in_group": None,
                    
                    "created_at": datetime.now().isoformat()
                }
                task_rows.append(row)
            
            self.client.table("record_tasks").insert(task_rows).execute()

        # 3. schedule_histories 일괄 저장
        if request.schedule_histories:
            history_rows = []
            for h in request.schedule_histories:
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
                history_rows.append(h_row)
            
            self.client.table("schedule_histories").insert(history_rows).execute()

        return True
