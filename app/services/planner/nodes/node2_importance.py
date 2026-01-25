from typing import Dict, Optional
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.request import ScheduleItem

DURATION_PARAMS = {
    "MINUTE_UNDER_30": {"avg": 20, "plan": 30, "min": 10, "max": 30},
    "MINUTE_30_TO_60": {"avg": 45, "plan": 60, "min": 20, "max": 60},
    "HOUR_1_TO_2":     {"avg": 90, "plan": 120, "min": 40, "max": 90},
}

COG_LOAD_VALUE = {
    "LOW": 0,
    "MED": 1,
    "HIGH": 2
}

def node2_importance(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 2: 중요도 산출
    - 중요도 계산
    - 피로도 계산
    - "ERROR" 카테고리 필터링
    """

    weights = state.weights # 가중치
    
    new_task_features: Dict[int, TaskFeature] = {} 
    
    flex_task_map: Dict[int, ScheduleItem] = {t.taskId: t for t in state.flexTasks}

    for task_id, feature in state.taskFeatures.items():
        original_task: Optional[ScheduleItem] = flex_task_map.get(task_id)
        
        # Node 1 결과 검정
        if not original_task:
            continue
            
        # 카테고리가 "ERROR"일 경우 해당 작업은 제거
        if feature.category == "ERROR":
            continue

        # 1. 중요도 계산
        # importanceScore = (focusLevel * w_focus) + (isUrgent ? w_urgent : 0) + w_category.get(category, 0)
        focus_level = original_task.focusLevel if original_task.focusLevel is not None else 5
        is_urgent_score = weights.w_urgent if original_task.isUrgent else 0.0
        category_score = weights.w_category.get(feature.category, 0.0) # 각 카테고리별로 가중치가 저장되어있음
        
        # 중요도 계산
        importance = (focus_level * weights.w_focus) + is_urgent_score + category_score
        
        # 2. 예상 시간 파라미터
        est_range = original_task.estimatedTimeRange
        range_params = DURATION_PARAMS.get(est_range, DURATION_PARAMS["MINUTE_30_TO_60"])
        
        # 3. 피로도 계산
        # fatigueCost = (durationPlanMin * alpha_duration) + (cognitiveLoad_value * beta_load)
        cog_load_str = feature.cognitiveLoad or "MED" 
        cog_val = COG_LOAD_VALUE.get(cog_load_str, 1) # Default to MED=1
        
        fatigue = (range_params["plan"] * weights.alpha_duration) + (cog_val * weights.beta_load)

        # 4. 피쳐 업데이트
        updated_feature = feature.model_copy(update={
            "importanceScore": importance,
            "fatigueCost": fatigue,
            "durationAvgMin": range_params["avg"],
            "durationPlanMin": range_params["plan"],
            "durationMinChunk": range_params["min"],
            "durationMaxChunk": range_params["max"]
        })
        
        new_task_features[task_id] = updated_feature

    # state 업데이트
    return state.model_copy(update={"taskFeatures": new_task_features})
