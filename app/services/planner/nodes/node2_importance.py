import logfire  # [Logfire] Import
from typing import Dict, Optional
from app.models.planner.internal import PlannerGraphState, TaskFeature
from app.models.planner.request import ScheduleItem

DURATION_PARAMS = {
    "MINUTE_UNDER_30": {"avg": 30, "plan": 30, "min": 30, "max": 30},
    "MINUTE_30_TO_60": {"avg": 45, "plan": 60, "min": 30, "max": 60},
    "HOUR_1_TO_2":     {"avg": 90, "plan": 120, "min": 40, "max": 90},
}

COG_LOAD_VALUE = {
    "LOW": 0,
    "MED": 1,
    "HIGH": 2
}

@logfire.instrument  # [Logfire] Instrument
def node2_importance(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 2: 중요도 산출
    - 중요도 계산
    - 피로도 계산
    - "ERROR" 카테고리 필터링
    """

    weights = state.weights # 가중치
    
    new_task_features: Dict[int, TaskFeature] = {} 
    
    # [Logfire] 입력 데이터 로깅
    logfire.info("Node 2 Input Data", input={"taskFeatures": state.taskFeatures, "weights": state.weights})
    
    flex_task_map: Dict[int, ScheduleItem] = {t.taskId: t for t in state.flexTasks}

    for task_id, feature in state.taskFeatures.items():
        original_task: Optional[ScheduleItem] = flex_task_map.get(task_id)
        
        # Node 1 결과 검정
        if not original_task:
            continue
            
        importance = 0.0
        # 1. 중요도 계산
        if feature.category == "ERROR":
            # ERROR 카테고리는 최하위 중요도 부여 및 계산 건너뜀
            importance = -1.0
        else:
            # importanceScore = (focusLevel * w_focus) + (isUrgent ? w_urgent : 0) + w_category.get(category, 0)
            focus_level = original_task.focusLevel if original_task.focusLevel is not None else 5
            is_urgent_score = weights.w_urgent if original_task.isUrgent else 0.0
            category_score = weights.w_category.get(feature.category, 0.0)
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
    result_state = state.model_copy(update={"taskFeatures": new_task_features})
    
    # [Logfire] 결과 명시적 기록
    logfire.info("Node 2 Result", result=result_state)
    
    return result_state
