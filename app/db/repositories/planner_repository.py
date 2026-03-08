from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.response import AssignmentResult

class PlannerRepository:
    def __init__(self):
        pass

    async def save_ai_draft(self, state: PlannerGraphState) -> bool:
        """
        AI가 생성한 초안(AI_DRAFT)을 DB에 저장합니다.
        (planner_records -> record_tasks)
        """
        print(f"[PlannerRepository] save_ai_draft called for User {state.request.user.userId}")
        try:
            user_id = state.request.user.userId
            day_plan_id = max((t.dayPlanId for t in state.request.schedules), default=0) if state.request.schedules else 0
            
            fill_rate = state.fillRate if hasattr(state, 'fillRate') else 0.0
            
            assigned_real_count = len([r for r in state.finalResults if r.assignmentStatus == "ASSIGNED"])
            excluded_count = len([r for r in state.finalResults if r.assignmentStatus == "EXCLUDED"])
            
            record_payload = {
                "user_id": user_id,
                "day_plan_id": day_plan_id,
                "record_type": "AI_DRAFT",
                "start_arrange": state.request.startArrange,
                "day_end_time": state.request.user.dayEndTime,
                "focus_time_zone": state.request.user.focusTimeZone,
                "user_age": None,
                "user_gender": None,
                "total_tasks": len(state.flexTasks),
                "assigned_count": assigned_real_count,
                "excluded_count": excluded_count,
                "fill_rate": fill_rate,
                "weights_version": 1,
                "created_at": datetime.now()
            }
            
            async with AsyncSessionLocal() as session:
                # 1. Insert planner_records
                stmt = text("""
                    INSERT INTO planner_records (
                        user_id, day_plan_id, record_type, start_arrange, day_end_time,
                        focus_time_zone, user_age, user_gender, total_tasks,
                        assigned_count, excluded_count, fill_rate, weights_version, created_at
                    ) VALUES (
                        :user_id, :day_plan_id, :record_type, :start_arrange, :day_end_time,
                        :focus_time_zone, :user_age, :user_gender, :total_tasks,
                        :assigned_count, :excluded_count, :fill_rate, :weights_version, :created_at
                    ) RETURNING id
                """)
                
                res = await session.execute(stmt, record_payload)
                record_id = res.scalar()
                
                if not record_id:
                    print("Failed to get record_id for AI_DRAFT")
                    return False
                
                # 2. Prepare Tasks Data
                task_rows = []
                assignment_map = {res.taskId: res for res in state.finalResults}
                
                for task_id, feature in state.taskFeatures.items():
                    original_task = next((t for t in state.flexTasks if t.taskId == task_id), None)
                    if not original_task: continue
                    
                    assign_res = assignment_map.get(task_id)
                    assignment_status = assign_res.assignmentStatus if assign_res else "NOT_ASSIGNED"
                    
                    start_at = assign_res.startAt if assign_res else None
                    end_at = assign_res.endAt if assign_res else None
                    children_data = [c.model_dump() for c in assign_res.children] if assign_res and assign_res.children else None
                    is_split = bool(children_data)
                    
                    if is_split:
                        start_at = None
                        end_at = None
                    
                    row = {
                        "record_id": record_id,
                        "task_id": task_id,
                        "day_plan_id": original_task.dayPlanId,
                        "parent_schedule_id": original_task.parentScheduleId,
                        "title": original_task.title,
                        "status": "TODO",
                        "task_type": "FLEX",
                        "assigned_by": "AI",
                        "assignment_status": assignment_status,
                        "start_at": start_at,
                        "end_at": end_at,
                        "estimated_time_range": original_task.estimatedTimeRange,
                        "focus_level": original_task.focusLevel,
                        "is_urgent": original_task.isUrgent,
                        "category": feature.category,
                        "cognitive_load": feature.cognitiveLoad,
                        "group_id": feature.groupId,
                        "group_label": feature.groupLabel,
                        "order_in_group": feature.orderInGroup,
                        "importance_score": float(feature.importanceScore) if feature.importanceScore is not None else None,
                        "fatigue_cost": float(feature.fatigueCost) if feature.fatigueCost is not None else None,
                        "duration_avg_min": feature.durationAvgMin,
                        "duration_plan_min": feature.durationPlanMin,
                        "duration_min_chunk": feature.durationMinChunk,
                        "duration_max_chunk": feature.durationMaxChunk,
                        # "children": children_data, # Use JSON conversion if needed
                        "is_split": is_split,
                        "created_at": datetime.now()
                    }
                    task_rows.append(row)
                    
                    if is_split and children_data:
                        for child in children_data:
                            child_row = row.copy()
                            child_row["title"] = child["title"]
                            child_row["start_at"] = child["startAt"]
                            child_row["end_at"] = child["endAt"]
                            child_row["is_split"] = False
                            # child_row["children"] = None
                            child_row["created_at"] = datetime.now()
                            task_rows.append(child_row)
                    
                for ft in state.fixedTasks:
                    task_rows.append({
                        "record_id": record_id,
                        "task_id": ft.taskId,
                        "day_plan_id": ft.dayPlanId,
                        "parent_schedule_id": ft.parentScheduleId,
                        "title": ft.title,
                        "status": "TODO",
                        "task_type": "FIXED",
                        "assigned_by": "USER",
                        "assignment_status": "ASSIGNED",
                        "start_at": ft.startAt,
                        "end_at": ft.endAt,
                        "created_at": datetime.now()
                    })
                    
                if task_rows:
                    # Generic insert for record_tasks. 
                    # Note: We only insert columns that exist in the DB.
                    # Some fields like importance_score etc. were added in the dict above.
                    # We use a keys list to ensure all rows have same keys for binary execute.
                    first_row_keys = task_rows[0].keys()
                    cols = ", ".join(first_row_keys)
                    vals = ", ".join([f":{k}" for k in first_row_keys])
                    task_stmt = text(f"INSERT INTO record_tasks ({cols}) VALUES ({vals})")
                    await session.execute(task_stmt, task_rows)
                    
                await session.commit()
                return True
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[PlannerRepository] save_ai_draft Error: {e}")
            return False
