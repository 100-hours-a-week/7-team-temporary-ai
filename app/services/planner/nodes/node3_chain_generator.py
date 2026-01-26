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

@logfire.instrument  # [Logfire] Instrument
async def node3_chain_generator(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 3: 작업 체인 생성 (Task Chain Generator)
    - LLM을 활용하여 시간대별(MORNING/AFTERNOON...) 작업 분배 후보 4-6개 생성
    - 가용량(Capacity) 및 사용자 선호 시간대(focusTimeZone) 고려
    """
    task_features = state.taskFeatures
    free_sessions = state.freeSessions
    
    # 1. 입력 준비
    # 시간대별 가용 용량 계산 (분 단위)
    capacity = calculate_capacity(free_sessions)
    
    # Fixed Task 추출 (Prompt Context용)
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
    max_retries = 4
    candidates_result: List[ChainCandidate] = []
    
    # 2. LLM 호출 및 파싱 (재시도 로직)
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"Node 3 체인 생성 시도 {attempt + 1}/{max_retries + 1}")
            
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
                
                # 큐 검증 (MORNING, etc 존재 여부)
                # (간단히 pass, Pydantic validation에서 걸러짐 or default dict)
                
                # ChainCandidate 생성 (Pydantic validation)
                cand = ChainCandidate(
                    chainId=chainId,
                    timeZoneQueues=queues, # Dict[TimeZone, List[int]]
                    rationaleTags=tags
                )
                
                # --- Integrity Check (Strict) ---
                # 1. Hallucination Check: All taskIds must be in task_features
                valid_ids = set(task_features.keys())
                for tz, q in cand.timeZoneQueues.items():
                    for tid in q:
                        if tid not in valid_ids:
                            raise ValueError(f"AI hallucinated invalid taskId {tid} in queue {tz}")

                # 2. Key Check: Must have at least one valid candidate structure (Implicit by Pydantic)
                      
                valid_candidates.append(cand)
            
            if not valid_candidates:
                raise ValueError("No valid candidates parsed (List is empty)")
                
            candidates_result = valid_candidates
            break # 성공
            
        except Exception as e:
            # 에러 매핑 및 재시도 여부 판단
            error_code = map_exception_to_error_code(e)
            is_retryable = is_retryable_error(error_code)

            logger.warning(f"Node 3 Attempt {attempt + 1} failed: {e} (Code: {error_code.value})")
            
            if not is_retryable:
                logger.error(f"Node 3: Non-retryable error encountered ({error_code.value}). Stopping retries.")
                break # 재시도 불가능한 에러는 즉시 중단 (Fallback으로 이동)
            
            # 지수 백오프 적용 (Exponential Backoff)
            if attempt < max_retries:
                delay = 1.0 * (2 ** attempt)  # 1s, 2s, 4s, 8s...
                logger.info(f"Node 3: Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)

            if attempt == max_retries:
                logger.error("Node 3 Max retries reached. Using Fallback.")
    
    # 3. 실패 시 Fallback 전략
    if not candidates_result:
        candidates_result = [_create_fallback_chain(state)]
    
    # 4. State 업데이트
    result_state = state.model_copy(update={
        "chainCandidates": candidates_result,
        "retry_node3": state.retry_node3 # 재시도 횟수 등은 필요 시 증가
    })
    
    # [Logfire] 결과 명시적 기록
    logfire.info("Node 3 Result", result=result_state)
    
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
