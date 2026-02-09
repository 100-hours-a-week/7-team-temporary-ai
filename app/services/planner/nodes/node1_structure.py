
import json
import logging
import asyncio
import logfire  # [Logfire] Import
from typing import List, Dict, Any, Optional, Literal

from app.models.planner.internal import TaskFeature, PlannerGraphState
from app.llm.gemini_client import get_gemini_client
from app.llm.prompts.node1_prompt import NODE1_SYSTEM_PROMPT, format_tasks_for_llm
from app.models.planner.request import EstimatedTimeRange, ScheduleItem
from app.models.planner.errors import map_exception_to_error_code, is_retryable_error

logger = logging.getLogger(__name__)

@logfire.instrument
async def node1_structure_analysis(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 1: 작업 구조 분석 (Single Attempt for LangGraph)
    - LLM을 활용하여 FLEX인 Task의 Category와 Cognitive Load를 분석
    - 실패 시 retry_node1 카운트 증가 및 에러 기록
    """
    flex_tasks: List[ScheduleItem] = state.flexTasks
    
    # 입력 준비
    client = get_gemini_client()
    formatted_tasks = format_tasks_for_llm(flex_tasks)
    
    # [Logfire] LLM 입력 데이터 로깅
    logfire.info("Node 1 Input Data", input=formatted_tasks)
    
    task_map = {t.taskId: t for t in flex_tasks}
    
    try:
        logger.info(f"Node 1 작업 구조 분석 시도 (Retry: {state.retry_node1})")
        
        # LLM 호출
        response_json = await client.generate(
            system=NODE1_SYSTEM_PROMPT,
            user=formatted_tasks
        )
        
        # JSON 형식 검증
        if not isinstance(response_json, dict) or "tasks" not in response_json:
            raise ValueError("Invalid JSON format: missing 'tasks' key")
            
        parsed_result = response_json
        
        # 데이터 검증 및 Feature 생성
        task_features: Dict[int, TaskFeature] = {}
        llm_items = {item["taskId"]: item for item in parsed_result.get("tasks", [])}
        
        for task in flex_tasks:
            llm_item = llm_items.get(task.taskId)
            
            if llm_item:
                # Hallucination Check
                if task.taskId not in task_map:
                     raise ValueError(f"AI hallucinated invalid taskId: {task.taskId}")

                category = llm_item.get("category", "기타")
                cog_load = llm_item.get("cognitiveLoad", "MED")
                order_in_group = llm_item.get("orderInGroup")
                
                # 유효성 검사
                if category not in ["학업", "업무", "운동", "취미", "생활", "기타", "ERROR"]:
                    category = "기타"
                if cog_load not in ["LOW", "MED", "HIGH"]:
                    cog_load = "MED"
                    
                feature = TaskFeature(
                    taskId=task.taskId,
                    dayPlanId=task.dayPlanId,
                    title=task.title,
                    type=task.type,
                    category=category,
                    cognitiveLoad=cog_load,
                    groupId=str(task.parentScheduleId) if task.parentScheduleId is not None else None,
                    groupLabel=None,
                    orderInGroup=order_in_group if task.parentScheduleId is not None else None, 
                )
                
                if task.parentScheduleId:
                    parent_task = next((t for t in state.request.schedules if t.taskId == task.parentScheduleId), None)
                    if parent_task:
                        feature.groupLabel = parent_task.title
                
                task_features[task.taskId] = feature
            else:
                 # 일부 누락된 경우 -> 이것도 에러로 볼 것인가? 
                 # 기존 로직: Fallback 사용. 여기서는 일부 누락 시 해당 건만 Fallback하든, 전체 Fail하든 결정 필요.
                 # 기존은 "else: fallback"
                 task_features[task.taskId] = _create_fallback_feature(task)

        # 성공 시 state 업데이트
        result_state = state.model_copy(update={
            "taskFeatures": task_features,
            # retry count는 성공 시 리셋하지 않고 그대로 두거나, 
            # 다음 노드에서 참조 안하므로 상관없음.
        })
        
        logfire.info("Node 1 Result (Success)", result=result_state)
        return result_state

    except Exception as e:
        error_msg = str(e)
        error_code = map_exception_to_error_code(e)
        logger.warning(f"Node 1 Failed: {error_msg} (Code: {error_code.value})")
        
        # 실패 시 state 업데이트 (Retry Count 증가)
        return state.model_copy(update={
            "retry_node1": state.retry_node1 + 1,
            "warnings": state.warnings + [f"Node 1 Error: {error_msg}"]
        })

@logfire.instrument
def node1_fallback(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 1 Fallback: 모든 재시도 실패 시 기본값 생성
    """
    logger.error(f"Node 1 Fallback Triggered after {state.retry_node1} retries.")
    
    task_features = {}
    for task in state.flexTasks:
        task_features[task.taskId] = _create_fallback_feature(task)
        
    result_state = state.model_copy(update={
        "taskFeatures": task_features,
        "warnings": state.warnings + ["Node 1 Fallback applied"]
    })
    
    logfire.info("Node 1 Fallback Result", result=result_state)
    return result_state

def _create_fallback_feature(task: ScheduleItem) -> TaskFeature:
    """
    LLM이 실패한 경우 fallback feature를 생성
    """
    # 추정 시간을 기반으로 cognitive load를 추정
    est: Optional[EstimatedTimeRange] = task.estimatedTimeRange
    cog: Literal["LOW", "MED", "HIGH"]
    
    if est == "MINUTE_UNDER_30":
        cog = "LOW"
    elif est == "MINUTE_30_TO_60":
        cog = "MED"
    else:
        cog = "HIGH"
        
    return TaskFeature(
        taskId=task.taskId,
        dayPlanId=task.dayPlanId,
        title=task.title,
        type=task.type,
        category="기타",
        cognitiveLoad=cog,
        groupId=str(task.parentScheduleId) if task.parentScheduleId else None
    )
