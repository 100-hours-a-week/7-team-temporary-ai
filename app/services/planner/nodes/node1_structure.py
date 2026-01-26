import json
import logging
from typing import List, Dict, Any, Optional, Literal

from app.models.planner.internal import TaskFeature, PlannerGraphState
from app.llm.gemini_client import get_gemini_client
from app.llm.prompts.node1_prompt import NODE1_SYSTEM_PROMPT, format_tasks_for_llm
from app.models.planner.request import EstimatedTimeRange, ScheduleItem
from app.models.planner.errors import map_exception_to_error_code, is_retryable_error

logger = logging.getLogger(__name__)

async def node1_structure_analysis(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 1: 작업 구조 분석
    - LLM을 활용하여 FLEX인 Task의 Category와 Cognitive Load를 분석
    - parentScheduleId를 기반으로 그룹핑을 강제
    - Structural mismatch에 대한 재시도 로직 구현 (최대 4회)
    """
    flex_tasks: List[ScheduleItem] = state.flexTasks # FLEX인 Task 리스트
    
    # 1. 입력 준비
    client = get_gemini_client()
    formatted_tasks = format_tasks_for_llm(flex_tasks)
    
    # taskId와 original task를 매핑
    task_map = {t.taskId: t for t in flex_tasks}
    
    # 반복 루프
    ## 현재 gemini만 사용해서 4회 반복을 지정함
    ### 추후 다른 LLM을 사용할 경우, 이 부분을 수정할 필요가 있음
    max_retries = 4
    current_retry = state.retry_node1
    
    parsed_result = None
    validation_error = None
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Node 1 작업 구조 분석 시도 {attempt + 1}/{max_retries + 1}")
            
            # LLM 호출
            response_json = await client.generate(
                system=NODE1_SYSTEM_PROMPT,
                user=formatted_tasks
            )
            
            # JSON 형식의 응답을 받았는지 확인
            if not isinstance(response_json, dict) or "tasks" not in response_json:
                raise ValueError("Invalid JSON format: missing 'tasks' key")
                
            # 응답된 데이터를 처리
            for item in response_json.get("tasks", []):
                t_id = item.get("taskId")
                # 1. 보내준 목록이 실존하는 작업 아이디인지 확인 (Hallucination Check)
                if t_id not in task_map:
                    raise ValueError(f"AI hallucinated invalid taskId: {t_id}")

                # 2. Category 유효성 검사
                cat = item.get("category", "")
                if cat not in ["학업", "업무", "운동", "취미", "생활", "기타", "ERROR"]:
                    raise ValueError(f"Invalid category: {cat}")
                
                # 3. Cognitive Load 유효성 검사
                cog = item.get("cognitiveLoad", "")
                if cog not in ["LOW", "MED", "HIGH"]:
                    raise ValueError(f"Invalid cognitiveLoad: {cog}")

            parsed_result = response_json
            break # 성공: 시도 중단

        except Exception as e:
            validation_error = str(e)
            
            # 에러 매핑 및 재시도 여부 판단
            error_code = map_exception_to_error_code(e)
            is_retryable = is_retryable_error(error_code)
            
            logger.warning(f"Node 1 Attempt {attempt + 1} failed: {validation_error} (Code: {error_code.value})")
            
            if not is_retryable:
                logger.error(f"Node 1: Non-retryable error encountered ({error_code.value}). Stopping retries.")
                break # 재시도 불가능한 에러는 즉시 중단
            
            continue
    
    # 2. 결과 처리
    task_features: Dict[int, TaskFeature] = {} # 각 작업에 대한 feature를 저장
    
    # 4번의 재시도가 전부 실패했을 경우
    if not parsed_result:
        logger.error(f"Node 1 failed after {max_retries + 1} attempts. Using Fallback.")
        # Fallback 로직 적용
        ## 자동으로 fallback feature를 생성
        for task in flex_tasks:
            task_features[task.taskId] = _create_fallback_feature(task) #아래에 정의
            
        # fallback feature를 생성한 후, state 업데이트
        return state.model_copy(update={ # model_copy는 state의 일부만 업데이트
            "taskFeatures": task_features,
            "retry_node1": max_retries + 1,
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
                groupId=str(task.parentScheduleId) if task.parentScheduleId else None,
                groupLabel=None, # 그룹이 존재할 경우 system이 채워넣음 (LLM이 아님)
                orderInGroup=order_in_group, 
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
    return state.model_copy(update={
        "taskFeatures": task_features,
        "retry_node1": attempt # 재시도 횟수 업데이트
    })

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
