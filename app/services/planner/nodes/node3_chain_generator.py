import json
import logging
import asyncio
import logfire  # [Logfire] Import
from typing import List, Dict, Any

from app.models.planner.internal import PlannerGraphState, ChainCandidate
from app.llm.gemini_client import get_gemini_client
from app.llm.prompts.node3_prompt import NODE3_SYSTEM_PROMPT, format_node3_input
from app.services.planner.utils.session_utils import calculate_capacity
from app.models.planner.errors import map_exception_to_error_code, is_retryable_error

logger = logging.getLogger(__name__)

@logfire.instrument
async def node3_chain_generator(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 3: 작업 체인 생성 (Single Attempt for LangGraph)
    - LLM을 활용하여 시간대별(MORNING/AFTERNOON...) 작업 분배 후보 4-6개 생성
    - 실패 시 retry_node3 카운트 증가 및 에러 기록
    """
    task_features = state.taskFeatures
    free_sessions = state.freeSessions
    
    # 입력 준비
    capacity = calculate_capacity(free_sessions)
    
    fixed_tasks_list = []
    if state.fixedTasks:
        for t in state.fixedTasks:
            fixed_tasks_list.append({
                "title": t.title,
                "startAt": t.startAt,
                "endAt": t.endAt
            })

    # LLM 입력 포맷팅
    user_input_str = format_node3_input(
        task_features=task_features,
        fixed_schedules=fixed_tasks_list,
        capacity=capacity,
        focus_timezone=state.request.user.focusTimeZone
    )
    
    client = get_gemini_client()
    
    try:
        logger.info(f"Node 3 체인 생성 시도 (Retry: {state.retry_node3})")
        
        response_json = await client.generate(
            system=NODE3_SYSTEM_PROMPT,
            user=user_input_str
        )
        
        # 응답 검증
        if not isinstance(response_json, dict) or "candidates" not in response_json:
            raise ValueError("Invalid JSON format: missing 'candidates' key")
        
        raw_candidates = response_json.get("candidates", [])
        if not isinstance(raw_candidates, list) or len(raw_candidates) == 0:
            raise ValueError("No candidates returned from LLM")
        
        # 객체 변환
        valid_candidates = []
        for item in raw_candidates:
            chainId = item.get("chainId")
            queues = item.get("timeZoneQueues")
            tags = item.get("rationaleTags", [])
            
            # 필수 필드 검사
            if not chainId or not queues:
                continue
            
            cand = ChainCandidate(
                chainId=chainId,
                timeZoneQueues=queues, 
                rationaleTags=tags
            )
            
            # Integrity Check
            valid_ids = set(task_features.keys())
            for tz, q in cand.timeZoneQueues.items():
                for tid in q:
                    if tid not in valid_ids:
                        raise ValueError(f"AI hallucinated invalid taskId {tid} in queue {tz}")

            valid_candidates.append(cand)
        
        if not valid_candidates:
            raise ValueError("No valid candidates parsed (List is empty)")
            
        # 성공 시 State 업데이트
        result_state = state.model_copy(update={
            "chainCandidates": valid_candidates,
            # retry count는 유지
        })
        
        logfire.info("Node 3 Result (Success)", result=result_state)
        return result_state
        
    except Exception as e:
        error_msg = str(e)
        error_code = map_exception_to_error_code(e)
        logger.warning(f"Node 3 Failed: {error_msg} (Code: {error_code.value})")
        
        # 실패 시 state 업데이트
        return state.model_copy(update={
            "retry_node3": state.retry_node3 + 1,
            "warnings": state.warnings + [f"Node 3 Error: {error_msg}"]
        })

@logfire.instrument
def node3_fallback(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 3 Fallback: 모든 재시도 실패 시 Fallback Chain 생성 (1회)
    """
    logger.error(f"Node 3 Fallback Triggered after {state.retry_node3} retries.")
    
    fallback_chain = _create_fallback_chain(state) # 내부 함수 재사용
    
    result_state = state.model_copy(update={
        "chainCandidates": [fallback_chain],
        "warnings": state.warnings + ["Node 3 Fallback applied"]
    })
    
    logfire.info("Node 3 Fallback Result", result=result_state)
    return result_state

def _create_fallback_chain(state: PlannerGraphState) -> ChainCandidate:
    """
    LLM 실패 시 Fallback Chain 생성: 
    중요도 순으로 Task를 정렬한 뒤, 사용자의 Focus TimeZone을 최우선으로 하여
    각 시간대별 Capacity의 120%를 넘지 않도록 분산 배치한다.
    """
    # 1. 중요도 내림차순 정렬
    sorted_tasks = sorted(
        state.taskFeatures.values(),
        key=lambda f: f.importanceScore,
        reverse=True
    )
    
    # 2. Capacity 및 Limit 계산 (120%)
    capacity = calculate_capacity(state.freeSessions)
    limits = {tz: cap * 1.2 for tz, cap in capacity.items()}
    usage = {tz: 0 for tz in capacity} # 현재 사용량 상태
    
    # 3. Zone 우선순위 결정 (FocusZone -> 시간순)
    focus_tz = state.request.user.focusTimeZone
    all_zones = ["MORNING", "AFTERNOON", "EVENING", "NIGHT"]
    # FocusZone을 맨 앞으로, 나머지는 순서대로
    zone_priority = [focus_tz] + [z for z in all_zones if z != focus_tz]
    
    queues = {tz: [] for tz in all_zones}
    
    # 4. Greedy 배정
    for task in sorted_tasks:
        duration = task.durationAvgMin
        assigned = False
        
        # 4-1. Limit(120%) 이내로 들어가는 구간 탐색
        for tz in zone_priority:
            limit = limits.get(tz, 0)
            if limit > 0 and (usage[tz] + duration <= limit):
                queues[tz].append(task.taskId)
                usage[tz] += duration
                assigned = True
                break
        
        # 4-2. 모든 구간이 120% 찼거나 Capacity가 부족한 경우
        # -> 가장 '적게 찬(비율 기준)' 곳에 강제 배정 (Load Balancing)
        if not assigned:
            best_tz = None
            min_load_ratio = float('inf')
            
            for tz in zone_priority:
                limit = limits.get(tz, 0)
                curr = usage[tz]
                
                # Capacity가 0인 구간은 비율 계산 불구 -> 우선순위 낮춤(Infinity)
                if limit <= 0:
                    ratio = float('inf') 
                else:
                    ratio = curr / limit
                
                # 비율이 젤 낮은 곳 선택 (동률이면 Priority 순)
                if ratio < min_load_ratio:
                    min_load_ratio = ratio
                    best_tz = tz
            
            # 모든 구간이 Capacity 0이거나 꽉 찼다면? 
            # -> 그래도 FocusZone이나 첫번째 우선순위에 넣어야 함
            target_tz = best_tz if best_tz is not None and min_load_ratio != float('inf') else zone_priority[0]
            
            queues[target_tz].append(task.taskId)
            usage[target_tz] += duration

    return ChainCandidate(
        chainId="fallback_distributed",
        timeZoneQueues=queues,
        rationaleTags=["static_distribution_cap_120", "focus_priority"]
    )
