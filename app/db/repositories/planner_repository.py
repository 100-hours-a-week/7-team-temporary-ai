from datetime import datetime
from typing import List, Optional

from app.db.supabase_client import get_supabase_client
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.response import AssignmentResult
from app.models.personalization import AssignmentStatus

class PlannerRepository:
    def __init__(self):
        self.client = get_supabase_client()

    async def save_ai_draft(self, state: PlannerGraphState) -> bool:
        """
        AI가 생성한 초안(AI_DRAFT)을 DB에 저장합니다.
        (planner_records -> record_tasks)
        """
        print(f"[PlannerRepository] save_ai_draft called for User {state.request.user.userId}")
        try:
            user_id = state.request.user.userId
            # Fixed: Select max dayPlanId to ensure we capture the latest (today's) plan ID,
            # avoiding issues where past tasks (EXCLUDED) with smaller IDs appear first in the list.
            day_plan_id = max((t.dayPlanId for t in state.request.schedules), default=0) if state.request.schedules else 0
            
            # 1. Prepare Record Data
            fill_rate = state.fillRate if hasattr(state, 'fillRate') else 0.0
            
            # Calculate stats
            flex_tasks = state.flexTasks
            assigned_count = len(state.finalResults) # This might include EXCLUDED, need to filter?
            # actually finalResults has status.
            
            assigned_real_count = len([r for r in state.finalResults if r.assignmentStatus == "ASSIGNED"])
            excluded_count = len([r for r in state.finalResults if r.assignmentStatus == "EXCLUDED"])
            
            record_payload = {
                "user_id": user_id,
                "day_plan_id": day_plan_id, # Assuming all tasks belong to same day plan for now
                "record_type": "AI_DRAFT",
                "start_arrange": state.request.startArrange,
                "day_end_time": state.request.user.dayEndTime,
                "focus_time_zone": state.request.user.focusTimeZone,
                "user_age": None,    # AI Draft creation doesn't necessarily know or store demographics here
                "user_gender": None, 
                "total_tasks": len(flex_tasks),
                "assigned_count": assigned_real_count,
                "excluded_count": excluded_count,
                "fill_rate": fill_rate,
                "weights_version": 1, # Default or current version
                "created_at": datetime.now().isoformat()
            }
            
            # 2. Insert planner_records
            record_res = self.client.table("planner_records").insert(record_payload).execute()
            if not record_res.data:
                print("Failed to insert planner_records for AI_DRAFT")
                return False
                
            record_id = record_res.data[0]["id"]
            
            # 3. Prepare Tasks Data
            task_rows = []
            
            # Use taskFeatures for full analysis details
            # Use finalResults for assignment details
            
            # Map assignment results by taskId
            assignment_map = {res.taskId: res for res in state.finalResults}
            
            for task_id, feature in state.taskFeatures.items():
                original_task = next((t for t in state.flexTasks if t.taskId == task_id), None)
                if not original_task:
                    continue # Should not happen
                
                assign_res = assignment_map.get(task_id)
                
                # Check mapping
                assignment_status = assign_res.assignmentStatus if assign_res else "NOT_ASSIGNED"
                
                # Start/End: If split, parent has NO time. If not split, parent has time.
                start_at = assign_res.startAt if assign_res else None
                end_at = assign_res.endAt if assign_res else None
                assigned_by = "AI"
                children_data = [c.model_dump() for c in assign_res.children] if assign_res and assign_res.children else None
                is_split = bool(children_data)
                
                # If Split: Parent's Time should be None (Container)
                if is_split:
                    start_at = None
                    end_at = None
                
                # --- 1. Create Parent Row ---
                row = {
                    "record_id": record_id,
                    "task_id": task_id,
                    "day_plan_id": original_task.dayPlanId,
                    "title": original_task.title,
                    "status": "TODO", 
                    "task_type": "FLEX",
                    "assigned_by": assigned_by,
                    "assignment_status": assignment_status,
                    "start_at": start_at,
                    "end_at": end_at,
                    "estimated_time_range": original_task.estimatedTimeRange,
                    "focus_level": original_task.focusLevel,
                    "is_urgent": original_task.isUrgent,
                    
                    # AI Analysis Results
                    "category": feature.category,
                    "cognitive_load": feature.cognitiveLoad,
                    "group_id": feature.groupId,
                    "group_label": feature.groupLabel,
                    "order_in_group": feature.orderInGroup,
                    
                    # Computed Metrics
                    "importance_score": float(feature.importanceScore) if feature.importanceScore is not None else None,
                    "fatigue_cost": float(feature.fatigueCost) if feature.fatigueCost is not None else None,
                    "duration_avg_min": feature.durationAvgMin,
                    "duration_plan_min": feature.durationPlanMin,
                    "duration_min_chunk": feature.durationMinChunk,
                    "duration_max_chunk": feature.durationMaxChunk,
                    
                    "children": children_data, # Keep JSON for reference/debugging
                    "is_split": is_split, 
                    
                    "created_at": datetime.now().isoformat()
                }
                task_rows.append(row)
                
                # --- 2. Create Child Rows (If Split) ---
                if is_split and children_data:
                    for child in children_data:
                         child_row = row.copy() # Copy parent attributes
                         
                         # Override specific child attributes
                         # Using same task_id as requested
                         child_row["title"] = child["title"] # e.g. "Title - 1"
                         child_row["start_at"] = child["startAt"]
                         child_row["end_at"] = child["endAt"]
                         child_row["is_split"] = False # Child itself is not split
                         child_row["children"] = None
                         child_row["created_at"] = datetime.now().isoformat()
                         
                         task_rows.append(child_row)
                
            # 3.2 FIXED Tasks
            # Fixed tasks are not in taskFeatures (Node 1 only analyzes FLEX), 
            # so we create rows with minimal AI info.
            for ft in state.fixedTasks:
                 row = {
                    "record_id": record_id,
                    "task_id": ft.taskId,
                    "day_plan_id": ft.dayPlanId,
                    "title": ft.title,
                    "status": "TODO",
                    "task_type": "FIXED",
                    "assigned_by": "USER",
                    "assignment_status": "ASSIGNED", # Fixed are always assigned by definition in draft
                    "start_at": ft.startAt,
                    "end_at": ft.endAt,
                    "estimated_time_range": None,
                    "focus_level": None,
                    "is_urgent": None,
                    
                    # AI Analysis Results (None for FIXED)
                    "category": None,
                    "cognitive_load": None,
                    "group_id": None,
                    "group_label": None,
                    "order_in_group": None,
                    
                    # Computed Metrics (None for FIXED)
                    "importance_score": None,
                    "fatigue_cost": None,
                    "duration_avg_min": None,
                    "duration_plan_min": None,
                    "duration_min_chunk": None,
                    "duration_max_chunk": None,
                    
                    "children": None,
                    
                    "created_at": datetime.now().isoformat()
                }
                 task_rows.append(row)
                
            # 4. Insert record_tasks
            if task_rows:
                self.client.table("record_tasks").insert(task_rows).execute()
                
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[PlannerRepository] save_ai_draft Error: {e}")
            # Don't throw error to main flow, just log
            return False
