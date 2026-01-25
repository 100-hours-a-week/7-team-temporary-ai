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
    Node 2: Task Importance & Time Parameter Calculation
    - Calculates importanceScore based on weights and user inputs.
    - Calculates fatigueCost based on duration and cognitive load.
    - Assigns duration parameters (plan/avg/min/max) based on estimatedTimeRange.
    - FILTERS out tasks categorized as "ERROR" (Gibberish).
    """
    weights = state.weights
    
    # Create a NEW dictionary to store only valid features
    # This ensures dropped tasks are actually removed
    new_task_features = {} 
    
    # Create a map for quick lookup of original tasks
    flex_task_map = {t.taskId: t for t in state.flexTasks}

    for task_id, feature in state.taskFeatures.items():
        original_task = flex_task_map.get(task_id)
        
        # Should not happen if Node 1 works correctly, but safe guard
        if not original_task:
            continue
            
        # FILTERING: Skip "ERROR" category tasks (Gibberish)
        if feature.category == "ERROR":
            # Do NOT add to new_task_features => Dropped
            continue

        # 1. Importance Calculation
        # importanceScore = (focusLevel * w_focus) + (isUrgent ? w_urgent : 0) + w_category.get(category, 0)
        # Default focusLevel to 5 if None (mid-point)
        focus_level = original_task.focusLevel if original_task.focusLevel is not None else 5
        is_urgent_score = weights.w_urgent if original_task.isUrgent else 0.0
        category_score = weights.w_category.get(feature.category, 0.0)
        
        importance = (focus_level * weights.w_focus) + is_urgent_score + category_score
        
        # 2. Duration Parameters
        est_range = original_task.estimatedTimeRange
        
        # Default to MINUTE_30_TO_60 if missing or unknown (Safe Fallback)
        params = DURATION_PARAMS.get(est_range, DURATION_PARAMS["MINUTE_30_TO_60"])
        
        # 3. Fatigue Cost Calculation
        # fatigueCost = (durationPlanMin * alpha_duration) + (cognitiveLoad_value * beta_load)
        cog_load_str = feature.cognitiveLoad or "MED" 
        cog_val = COG_LOAD_VALUE.get(cog_load_str, 1) # Default to MED=1
        
        fatigue = (params["plan"] * weights.alpha_duration) + (cog_val * weights.beta_load)

        # 4. Update Feature
        updated_feature = feature.model_copy(update={
            "importanceScore": importance,
            "fatigueCost": fatigue,
            "durationAvgMin": params["avg"],
            "durationPlanMin": params["plan"],
            "durationMinChunk": params["min"],
            "durationMaxChunk": params["max"]
        })
        
        new_task_features[task_id] = updated_feature

    # Return new state with updated features
    return state.model_copy(update={"taskFeatures": new_task_features})
