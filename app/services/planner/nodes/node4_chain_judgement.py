from typing import AsyncGenerator, Annotated, Set, Tuple
from collections import defaultdict
import math
import logfire  # [Logfire] Import

from app.models.planner.internal import PlannerGraphState, ChainCandidate, TaskFeature
from app.services.planner.utils.session_utils import calculate_capacity

def apply_closure(chain: ChainCandidate, task_features: dict[int, TaskFeature]) -> ChainCandidate:
    """
    그룹 작업의 순서(Closure)를 강제합니다.
    규칙: 그룹 내 순서 N이 포함되려면 1..N-1도 반드시 포함되어야 함.
    위반 시: 위반된 작업(N)을 제거(Excluded 처리).
    """
    # 1. 현재 체인에 포함된 작업 ID 집합
    included_ids = set()
    for ids in chain.timeZoneQueues.values():
        included_ids.update(ids)
    
    # 2. 그룹별로 포함된 작업들의 순서(orderInGroup) 수집
    # group_id -> [(taskId, order), ...]
    group_map = defaultdict(list)
    for tid in included_ids:
        feature = task_features.get(tid)
        if feature and feature.groupId and feature.orderInGroup is not None:
            group_map[feature.groupId].append((tid, feature.orderInGroup))
            
    # 3. 위반 작업 식별
    to_remove = set()
    
    for group_id, items in group_map.items():
        # 순서대로 정렬
        items.sort(key=lambda x: x[1])
        # "그룹 내 task들 중, 현재 chain에 포함된 것들의 orderSet을 확인했을 때,
        #  만약 order K가 포함되어 있다면, 1 ~ K-1에 해당하는 모든 task도 포함되어 있어야 한다."
        # 해당 그룹의 전체 Order 집합 파악
        all_group_tasks = [
            f for f in task_features.values() 
            if f.groupId == group_id and f.orderInGroup is not None
        ]
        all_group_orders = {f.orderInGroup: f.taskId for f in all_group_tasks}
        
        # 현재 체인에 포함된 order 집합
        current_included_orders = {order for _, order in items}
        
        for tid, order in items:
            # 1부터 order-1까지의 모든 순서가 포함되어 있는지 확인
            is_valid = True
            for prev_order in range(1, order):
                # 만약 prev_order에 해당하는 작업이 존재하는데(all_group_orders에 있음)
                # 현재 체인에는 없다면(current_included_orders에 없음) -> 위반
                if prev_order in all_group_orders and prev_order not in current_included_orders:
                    is_valid = False
                    break
            
            if not is_valid:
                to_remove.add(tid)
                
    # 4. 위반 작업 제거하여 새 체인 반환
    if not to_remove:
        return chain
        
    new_queues = {}
    for tz, ids in chain.timeZoneQueues.items():
        new_queues[tz] = [tid for tid in ids if tid not in to_remove]
        
    return ChainCandidate(
        chainId=chain.chainId,
        timeZoneQueues=new_queues,
        rationaleTags=chain.rationaleTags + ["closure_enforced"]
    )

def overflow_penalty(overflow: int, capacity: int, w_overflow: float) -> float:
    """
    초과량에 따른 단계적 페널티 계산
    - Safe Buffer (20%): 미세 페널티
    - Penalty Zone (>20%): 기하급수 페널티
    """
    if capacity <= 0:
        # 가용량이 0인데 오버플로우가 있으면 즉시 큰 페널티
        return w_overflow * (overflow ** 2) if overflow > 0 else 0.0

    safe_buffer = capacity * 0.2
    
    if overflow <= safe_buffer:
        # 안전 구간: 아주 작은 선형 페널티 (우선순위 구분을 위해 0은 아님)
        return 0.001 * overflow
    else:
        # 위험 구간: (초과분 - 버퍼)^2 * 가중치
        excess = overflow - safe_buffer
        return w_overflow * (excess ** 2)

def calculate_chain_score(
    chain: ChainCandidate, 
    task_features: dict[int, TaskFeature],
    capacity: dict[str, int],
    weights, # WeightParams
    focus_timezone: str
) -> Tuple[float, dict[str, float]]:
    """
    체인 점수 계산
    Returns: (Total Score, Details Dict)
    """
    
    included_ids = set()
    for ids in chain.timeZoneQueues.values():
        included_ids.update(ids)
        
    excluded_ids = set(task_features.keys()) - included_ids
    
    # 1. Included Utility
    score_included = sum(task_features[tid].importanceScore for tid in included_ids)
    
    # 2. Excluded Cost
    score_excluded = sum(task_features[tid].importanceScore for tid in excluded_ids)
    
    # 3. Overflow Penalty
    penalty_overflow_total = 0.0
    for tz, task_ids in chain.timeZoneQueues.items():
        # 해당 시간대 작업들의 평균 소요시간 합
        tz_duration_sum = sum(task_features[tid].durationAvgMin for tid in task_ids)
        tz_capacity = capacity.get(tz, 0)
        
        overflow = max(0, tz_duration_sum - tz_capacity)
        penalty_overflow_total += overflow_penalty(overflow, tz_capacity, weights.w_overflow)
        
    # 4. Fatigue Risk Penalty
    # 시간대별 Fatigue 합계가 Capacity를 넘으면 페널티 (단순화: 전체 합산보다는 시간대별로 보는게 맞음)
    # 기획서: "특정 시간대 내 fatigueCost 총합이 capacity를 초과할 경우"
    penalty_fatigue_total = 0.0
    for tz, task_ids in chain.timeZoneQueues.items():
        tz_fatigue_sum = sum(task_features[tid].fatigueCost for tid in task_ids)
        tz_capacity = capacity.get(tz, 0)
        
        # 피로도 비용은 '시간' 단위가 아닐 수 있으나, 여기서는 상대적 비교.
        # 보통 fatigueCost = duration * alpha + load * beta
        # duration 기반이므로 capacity와 비교 가능.
        if tz_fatigue_sum > tz_capacity:
            penalty_fatigue_total += (tz_fatigue_sum - tz_capacity) * weights.w_fatigue_risk

    # 5. Focus Alignment Bonus
    # 집중 시간대(focus_timezone)에 배치된 '중요 작업'에 대한 보너스
    # 중요 작업 기준? 상위 30%? or 그냥 importanceScore 비례?
    # 여기서는 importanceScore 자체를 가중치로 사용.
    score_focus_align = 0.0
    focus_queue = chain.timeZoneQueues.get(focus_timezone, [])
    for tid in focus_queue:
        score_focus_align += task_features[tid].importanceScore
        
    # 최종 점수
    # Score = (w_inc * U_inc) - (w_exc * U_exc) - P_overflow - P_fatigue + (w_align * FocusAlign)
    
    term_included = weights.w_included * score_included
    term_excluded = weights.w_excluded * score_excluded
    term_align = weights.w_focus_align * score_focus_align
    
    final_score = (
        term_included
        - term_excluded
        - penalty_overflow_total
        - penalty_fatigue_total
        + term_align
    )
    
    details = {
        "included_utility": term_included,
        "excluded_cost": term_excluded,
        "overflow_penalty": penalty_overflow_total,
        "fatigue_penalty": penalty_fatigue_total,
        "focus_align_bonus": term_align,
        "raw_included": score_included,
        "raw_excluded": score_excluded
    }
    
    return final_score, details

@logfire.instrument  # [Logfire] Instrument
def node4_chain_judgement(state: PlannerGraphState) -> PlannerGraphState:
    # [Logfire] Input Logging
    logfire.info("Node 4 Input Data", input={
        "candidates": state.chainCandidates,
        "taskFeatures": state.taskFeatures,
        "weights": state.weights,
        "focusTimeZone": state.request.user.focusTimeZone
    })
    
    candidates = state.chainCandidates
    task_features = state.taskFeatures
    weights = state.weights
    start_arrange = state.request.startArrange
    
    # Capacity 계산
    capacity = calculate_capacity(state.freeSessions)
    
    best_chain = None
    best_score = float("-inf")
    best_details = {}
    
    # 만약 후보가 없다면? (Node3 실패 등) -> Fallback 처리 또는 빈 상태
    if not candidates:
        # 후보가 아예 없으면 selectedChainId=None으로 남김 (Node5에서 처리하거나 에러)
        return state
        
    for chain in candidates:
        # 1. Closure 강제
        closed_chain = apply_closure(chain, task_features)
        
        # 2. 점수 계산
        score, details = calculate_chain_score(
            closed_chain,
            task_features,
            capacity,
            weights,
            state.request.user.focusTimeZone
        )
        
        if score > best_score:
            best_score = score
            best_chain = closed_chain
            best_details = details
            
    # 로그나 디버깅 정보 저장 가능
    # state.internal_logs["best_chain_score"] = best_score
    # state.internal_logs["best_chain_details"] = best_details
    
    # 선택된 체인이 수정되었을 수 있으므로(Closure), candidates 목록 자체를 업데이트할지,
    # 아니면 selectedChainId만 저장하고 Node5에서 재참조할지 결정해야 함.
    # 구조상 selectedChainId는 string ID임. 
    # 따라서, 만약 chain이 수정되었다면(closed_chain), 이를 candidates 리스트에 업데이트해줘야 Node5가 수정된 버전을 찾을 수 있음.
    
    # 수정된 체인을 candidates에 반영 (ID가 같다면 덮어쓰기 or 새 ID?)
    # ID가 같으면 덮어쓰는게 안전함.
    
    updated_candidates = []
    # 선택된 체인만 업데이트해서 넣거나, 전체를 다시 넣거나.
    # 여기서는 선택된 Best Chain을 확실히 리스트에 포함시킴.
    
    # 주의: best_chain이 candidates에 있는 원본 객체와 다를 수 있음(new object).
    # 따라서 candidates 리스트를 교체하거나 업데이트해야 함.
    
    # 전략: 모든 후보에 대해 closure를 적용한 결과로 candidates를 교체한다.
    # (선택 안 된 후보들도 closure 적용된 상태가 논리적으로 맞음)
    
    final_candidates = []
    for chain in candidates:
        final_candidates.append(apply_closure(chain, task_features))
        
    # 점수 계산은 이미 위에서 수행했음. (순서가 약간 비효율적일 수 있으나 명확성을 위해)
    # 최적화를 위해 위 루프에서 final_candidates를 만들면서 점수 계산
    
    result_state = state.model_copy(update={
        "chainCandidates": final_candidates,
        "selectedChainId": best_chain.chainId if best_chain else None
    })
    
    # [Logfire] Result Logging
    logfire.info("Node 4 Result", result=result_state)
    
    return result_state
