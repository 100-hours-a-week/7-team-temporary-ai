
import json
import logging
import asyncio
import logfire  # [Logfire] Import
from typing import List, Dict, Any, Optional, Literal

from app.models.planner.internal import TaskFeature, PlannerGraphState
from app.llm.gemini_client import get_gemini_client
from app.llm.runpod_client import get_runpod_client
from app.llm.prompts.node1_prompt import NODE1_SYSTEM_PROMPT, format_tasks_for_llm
from app.models.planner.request import EstimatedTimeRange, ScheduleItem
from app.models.planner.errors import map_exception_to_error_code, is_retryable_error

logger = logging.getLogger(__name__)

@logfire.instrument  # [Logfire] Instrument
async def node1_structure_analysis(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 1: 작업 구조 분석
    - LLM을 활용하여 FLEX인 Task의 Category와 Cognitive Load를 분석
    - parentScheduleId를 기반으로 그룹핑을 강제
    - Structural mismatch에 대한 재시도 로직 구현 (최대 4회)
    """
    flex_tasks: List[ScheduleItem] = state.flexTasks # FLEX인 Task 리스트
    
    # 1. 입력 준비
    runpod_client = get_runpod_client()
    gemini_client = get_gemini_client()
    formatted_tasks = format_tasks_for_llm(flex_tasks)
    
    # [Logfire] LLM 입력 데이터 로깅
    logfire.info("Node 1 Input Data", input=formatted_tasks)
    
    # taskId와 original task를 매핑
    task_map = {t.taskId: t for t in flex_tasks}
    
    parsed_result = None
    validation_error = None
    
    # --- Phase 1: RunPod Execution (2 attempts) ---
    max_runpod_retries = 2
    for attempt in range(max_runpod_retries):
        try:
            logger.info(f"Node 1: RunPod 시도 {attempt + 1}/{max_runpod_retries}")
            
            response_json = await runpod_client.generate(
                system=NODE1_SYSTEM_PROMPT,
                user=formatted_tasks
            )
            
            # 응답 검증 함수 (공통 사용)
            parsed_result = _validate_node1_response(response_json, task_map)
            break # 성공
            
        except Exception as e:
            validation_error = str(e)
            logger.warning(f"Node 1 RunPod Attempt {attempt + 1} failed: {e}")
            
            # 재시도 대기 (마지막 시도 제외)
            if attempt < max_runpod_retries - 1:
                await asyncio.sleep(1.0) # 1초 대기

    # --- Phase 2: Gemini Execution (2 attempts) if RunPod failed ---
    if not parsed_result:
        logger.warning("Node 1: RunPod failed. Switching to Gemini.")
        
        max_gemini_retries = 2
        for attempt in range(max_gemini_retries):
            try:
                logger.info(f"Node 1: Gemini 시도 {attempt + 1}/{max_gemini_retries}")
                
                response_json = await gemini_client.generate(
                    system=NODE1_SYSTEM_PROMPT,
                    user=formatted_tasks
                )
                
                # 응답 검증
                parsed_result = _validate_node1_response(response_json, task_map)
                break # 성공
                
            except Exception as e:
                validation_error = str(e)
                logger.warning(f"Node 1 Gemini Attempt {attempt + 1} failed: {e}")
                
                # 재시도 대기 (마지막 시도 제외)
                if attempt < max_gemini_retries - 1:
                    await asyncio.sleep(2.0) # 2초 대기
    
    # 2. 결과 처리
    task_features: Dict[int, TaskFeature] = {} # 각 작업에 대한 feature를 저장
    
    # 모든 시도가 실패했을 경우 (Fallback)
    if not parsed_result:
        logger.error(f"Node 1 failed after RunPod & Gemini attempts. Using Fallback.")
        # Fallback 로직 적용
        for task in flex_tasks:
            task_features[task.taskId] = _create_fallback_feature(task)
            
        return state.model_copy(update={
            "taskFeatures": task_features,
            "retry_node1": state.retry_node1 + 1, # 단순 증가 (상세 카운트는 생략)
            "warnings": state.warnings + [f"Node 1 Fallback triggered: {validation_error}"]
        })

    # LLM이 성공했을 경우
    llm_items = {item["taskId"]: item for item in parsed_result.get("tasks", [])}
    
    for task in flex_tasks:
        llm_item = llm_items.get(task.taskId)
        
        if llm_item:
            # 정상 처리
            category = llm_item.get("category", "기타")
            cog_load = llm_item.get("cognitiveLoad", "MED")
            order_in_group = llm_item.get("orderInGroup")
            
            # 유효한 값만 매핑
            if category not in ["학업", "업무", "운동", "취미", "생활", "기타", "ERROR"]:
                category = "기타"
            if cog_load not in ["LOW", "MED", "HIGH"]:
                cog_load = "MED"
                
            # state에 저장할 feature 생성
            feature = TaskFeature(
                taskId=task.taskId,
                dayPlanId=task.dayPlanId,
                title=task.title,
                type=task.type,
                category=category,
                cognitiveLoad=cog_load,
                # 그룹핑: 항상 parentScheduleId 사용
                groupId=str(task.parentScheduleId) if task.parentScheduleId is not None else None,
                groupLabel=None, 
                orderInGroup=order_in_group if task.parentScheduleId is not None else None, 
            )
            
            # 그룹이 존재할 경우 groupLabel 채우기
            if task.parentScheduleId:
                parent_task = next((t for t in state.request.schedules if t.taskId == task.parentScheduleId), None)
                if parent_task:
                    feature.groupLabel = parent_task.title
            
            # 각각의 작업에 대한 feature를 통합 저장
            task_features[task.taskId] = feature

        else:
            # LLM이 실패한 경우 fallback feature를 생성
            task_features[task.taskId] = _create_fallback_feature(task)

    # 3. state 업데이트
    result_state = state.model_copy(update={
        "taskFeatures": task_features,
        "retry_node1": 0 # 성공 시 0으로 (또는 시도 횟수 기록 가능하나 로직 단순화)
    })
    
    # [Logfire] 결과 명시적 기록
    logfire.info("Node 1 Result", result=result_state)
    
    return result_state

def _validate_node1_response(response_json: dict, task_map: dict) -> dict:
    """Node 1 응답 유효성 검사 (JSON 구조 및 값 검증)"""
    if not isinstance(response_json, dict) or "tasks" not in response_json:
        raise ValueError("Invalid JSON format: missing 'tasks' key")
        
    for item in response_json.get("tasks", []):
        t_id = item.get("taskId")
        # 1. Hallucination Check
        if t_id not in task_map:
            raise ValueError(f"AI hallucinated invalid taskId: {t_id}")

        # 2. Category Validation
        cat = item.get("category", "")
        if cat not in ["학업", "업무", "운동", "취미", "생활", "기타", "ERROR"]:
            raise ValueError(f"Invalid category: {cat}")
        
        # 3. Cognitive Load Validation
        cog = item.get("cognitiveLoad", "")
        # Allow ERROR or None/Empty if category is ERROR, or just generally allow ERROR as it will be mapped to MED later
        if cog not in ["LOW", "MED", "HIGH", "ERROR", None, ""]:
             # If it's not one of the standard values, and not ERROR/Empty, then it's invalid.
             # But let's be strict about random strings, but allow known "failure" modes from LLM.
             pass 
        
        if cog not in ["LOW", "MED", "HIGH", "ERROR"] and cog: # If it has a value but not a valid one
             raise ValueError(f"Invalid cognitiveLoad: {cog}")
            
    return response_json

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
