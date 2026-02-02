import logfire  # [Logfire] Import
import math
from typing import List, Dict, Optional, Tuple, Set
from pydantic import BaseModel

from app.models.planner.internal import PlannerGraphState, FreeSession, TaskFeature, ChainCandidate
from app.models.planner.response import AssignmentResult, SubTaskResult
from app.services.planner.utils.time_utils import hhmm_to_minutes, minutes_to_hhmm
from app.models.planner.request import TimeZone

# 상수 정의
GAP_MINUTES = 10  # 90분 이상 연속 작업 시 삽입할 휴식 시간 (Gap)
MAX_CONSECUTIVE_MINUTES = 90 # 연속 근무 최대 시간

@logfire.instrument  # [Logfire] Instrument
def node5_time_assignment(state: PlannerGraphState) -> PlannerGraphState:
    """
    Node 5: 최종 시간 배정 (Task Time Assignment)
    - 결정론적 로직으로 시간 확정
    - 분할(Splitting) 및 자투리 우선 배정(Remainder First)
    - Gap 기반 휴식 처리
    """
    # [Logfire] Input Logging
    logfire.info("Node 5 Input Data", input={
        "selectedChainId": state.selectedChainId,
        "chainCandidates": state.chainCandidates,
        "session_count": len(state.freeSessions)
    })

    # 1. 입력 데이터 준비
    selected_chain_id = state.selectedChainId
    if not selected_chain_id:
        return state

    user_id = state.request.user.userId  # userId 확보

    candidates = state.chainCandidates
    selected_chain = next((c for c in candidates if c.chainId == selected_chain_id), None)
    if not selected_chain:
        return state

    # 세션 정렬: 시간 순서대로 (startAt 오름차순)
    sessions = sorted(state.freeSessions, key=lambda s: s.start)
    
    task_features = state.taskFeatures
    
    # 작업 큐 준비 (Node 3가 제안한 시간대별 작업 목록)
    # 복사해서 사용 (pop으로 소모할 것이므로)
    queues: Dict[str, List[int]] = {
        tz: list(ids) for tz, ids in selected_chain.timeZoneQueues.items()
    }
    
    # 결과 저장소
    results: List[AssignmentResult] = []
    assigned_task_ids: Set[int] = set()

    # --- 배정 로직 시작 ---
    
    # 자투리(Remainder) 보관함: (parent_task_id, sequence_start_index)
    # Node 5 V1 정책: 자투리는 무조건 다음 가용 세션의 최우선 순위로 들어간다.
    pending_remainder_id: Optional[int] = None
    pending_sequence: int = 1

    for session in sessions:
        # 세션의 가용 시간 범위 (분 단위)
        # [V2 Logic] Start/End 10분 단위 정렬 Guarantee
        # 예: 09:03 -> 09:10으로 올림 (math.ceil)
        # 예: 남은 시간이 17분이면 -> 10분만 사용 (내림)
        current_time_raw = session.start
        current_time = math.ceil(current_time_raw / 10.0) * 10 
        
        session_end = session.end
        
        # 세션의 지배적 시간대 판별 (Dominant TimeZone)
        dominant_tz = _get_dominant_timezone(session)
        
        # 해당 시간대의 대기열 가져오기
        queue = queues.get(dominant_tz, [])

        # 세션 채우기 루프
        while current_time < session_end:
            # 유효 남은 시간 계산 (10분 단위 내림)
            raw_remaining = session_end - current_time
            effective_remaining_time = (raw_remaining // 10) * 10
            
            # 만약 유효 시간이 0이면(예: 7분 남음), 이 세션엔 더 이상 배정 불가
            if effective_remaining_time <= 0:
                break
                
            # 1순위: 자투리 작업이 남아있는가? (V1 정책: 무조건 최우선)
            target_task_id = None
            
            if pending_remainder_id is not None:
                target_task_id = pending_remainder_id
                # 자투리는 큐에서 꺼낼 필요 없음 (이미 꺼내진 상태)
            elif queue:
                target_task_id = queue[0]
            else:
                # 더 이상 배정할 작업이 없음 -> 다음 세션으로
                break

            feature = task_features[target_task_id]
            
            # 작업의 필요 시간 (배치용 durationPlanMin 사용)
            # 자투리인 경우 pending_remainder_duration 사용
            current_task_duration = 0
            if pending_remainder_id is not None:
                current_task_duration = pending_remainder_duration
            else:
                current_task_duration = feature.durationPlanMin

            # --- 배치 가능 여부 및 분할 판정 ---
            # 비교 대상: effective_remaining_time
            
            # A. 세션에 통째로 들어가는 경우 (No Split needed for this chunk)
            if current_task_duration <= effective_remaining_time:
                # [배정 성공]
                start_at_str = minutes_to_hhmm(current_time)
                end_at_str = minutes_to_hhmm(current_time + current_task_duration)
                
                # 결과 생성
                if pending_remainder_id is not None:
                    # 이전에 분할된 작업의 마지막 조각
                    _append_child_to_result(results, pending_remainder_id, feature.title, start_at_str, end_at_str, pending_sequence)
                    pending_remainder_id = None
                    pending_remainder_duration = 0
                    pending_sequence = 1
                else:
                    # 새로운 작업 배정 (분할 없음)
                    results.append(AssignmentResult(
                        userId=user_id,
                        taskId=feature.taskId,
                        dayPlanId=feature.dayPlanId,
                        title=feature.title,
                        type="FLEX",
                        assignedBy="AI",
                        assignmentStatus="ASSIGNED",
                        startAt=start_at_str,
                        endAt=end_at_str,
                        children=None
                    ))
                    # 큐에서 제거
                    if queue and queue[0] == feature.taskId:
                        queue.pop(0)
                
                assigned_task_ids.add(feature.taskId)
                current_time += current_task_duration
                
                # 작업 간 휴식 (Gap) 삽입 - 작업 사이 10분
                if current_time < session_end:
                     current_time += GAP_MINUTES
                
                continue

            # B. 세션 공간 부족 -> 분할 (Splitting)
            # 할당할 수 있는 만큼만 할당 (유효 시간만큼)
            allocatable = effective_remaining_time
            
            # 최소 청크(MinChunk) 체크: 
            # 만약 배정하려는 시간이 너무 짧으면(예: 10분 미만), 
            # 이 세션에는 배정하지 않고 다음 세션으로 넘기는 게 낫다.
            if allocatable < feature.durationMinChunk:
                # 이 세션 포기, 다음 세션으로 (break while loop)
                break 

            # [V2 Logic] 남은 부분(Remainder)이 최소 청크보다 작게 남으면 아예 분할하지 않는다.
            # 즉, 자식이 될 부분이 너무 작아지면 안 됨.
            remainder_if_split = current_task_duration - allocatable
            # 단, 이미 자투리 작업인 경우(pending_remainder_id is not None)는
            # "마지막 조각"이 되는 것이므로 remainder가 0이 될 수도 있음 -> 이건 괜찮음.
            # 하지만 "새로운 조각"을 남길 때는 그 조각이 MinChunk보다 커야 함.
            if remainder_if_split > 0 and remainder_if_split < feature.durationMinChunk:
                 # 남는 게 너무 작으면 분할 불가 -> 이 세션 포기
                 break
                
            # [부분 배정 수행]
            start_at_str = minutes_to_hhmm(current_time)
            end_at_str = minutes_to_hhmm(current_time + allocatable)
            
            # 자투리 여부에 따라 처리
            if pending_remainder_id is not None:
                # 기존 부모에 child 추가
                _append_child_to_result(results, pending_remainder_id, feature.title, start_at_str, end_at_str, pending_sequence)
            else:
                # 새 부모 생성 (Status=ASSIGNED, but Time=Null)
                results.append(AssignmentResult(
                    userId=user_id,
                    taskId=feature.taskId,
                    dayPlanId=feature.dayPlanId,
                    title=feature.title,
                    type="FLEX",
                    assignedBy="AI",
                    assignmentStatus="ASSIGNED", # 자식이 있으므로 ASSIGNED 취급
                    startAt=None,
                    endAt=None,
                    children=[]
                ))
                # 첫 번째 child 추가
                _append_child_to_result(results, feature.taskId, feature.title, start_at_str, end_at_str, 1)
                
                # 큐에서 제거 (이제 pending으로 관리됨)
                if queue and queue[0] == feature.taskId:
                    queue.pop(0)

            assigned_task_ids.add(feature.taskId)
            
            # 상태 업데이트
            current_time += allocatable
            
            # 남은 양 계산
            if pending_remainder_id is not None:
                pending_remainder_duration -= allocatable
            else:
                pending_remainder_duration = feature.durationPlanMin - allocatable
            
            # 다음 루프/세션을 위해 설정
            pending_remainder_id = feature.taskId
            pending_sequence += 1
            
            # 만약 남은 양이 0 이하라면 완료 처리 (Floating point error 방지)
            if pending_remainder_duration <= 0:
                pending_remainder_id = None
                pending_remainder_duration = 0
                pending_sequence = 1
            
            # 세션이 꽉 찼으므로 루프 종료? -> break while (이미 allocatable = remaining_session_time임)
            # 단, Gap 로직은? 세션이 끝났으므로 Gap을 굳이 더할 필요는 없음 (다음 세션 start부터 시작하면 됨)
            # 하지만 논리적으로 current_time은 session_end가 됨.
            break

    # 3. 미배정 작업 처리 (Tail Drop) -> EXCLUDED
    # pending_remainder가 남아있다면? -> 이것도 결국 배정 못 한 것.
    # 하지만 이미 앞부분은 배정되었으므로 'ASSIGNED' 상태는 유지하되, 뒷부분은 잘림.
    # (사용자에게 "시간 부족으로 일부만 배정됨"을 알릴 방법이 현재 스펙엔 없음. 그냥 둔다.)
    
    # 아예 배정 안 된 작업들 처리
    all_flex_ids = state.taskFeatures.keys()
    
    for tid in all_flex_ids:
        if tid not in assigned_task_ids:
            feat = task_features[tid]
            results.append(AssignmentResult(
                userId=user_id,
                taskId=feat.taskId,
                dayPlanId=feat.dayPlanId,
                title=feat.title,
                type="FLEX",
                assignedBy="AI",
                assignmentStatus="EXCLUDED",
                startAt=None,
                endAt=None,
                children=None
            ))
            
    # Soft Rollback (그룹 일관성) - V1에서는 생략 가능하지만, 안전장치로 구현 권장
    # 구현 복잡도상 V1에서는 "배정된 건 유지" 정책으로 가되, 
    # 차후 고도화 시 추가

    # 4. [Post-Processing] 단일 자식(Single Child) Flattening
    # 분할되었으나(Branch B), Tail Drop 등으로 인해 자식이 하나만 남은 경우
    # 굳이 Parent-Child 구조를 유지할 필요가 없으므로 일반 Task로 변환한다.
    final_results_processed = []
    for res in results:
        if res.children and len(res.children) == 1:
            child = res.children[0]
            # 부모(res)를 자식(child)의 내용으로 덮어씀
            # 단, taskId나 title 등은 부모 원본 유지 (child.subTaskId 대신 parentId 사용)
            # 여기서는 '하나뿐인 조각'이 곧 '전체 배정'이 된 셈 (비록 duration은 짧아졌을 수 있지만)
            # -> V1 정책상 부분 배정도 ASSIGNED로 본다면, 그냥 Start/End를 채우고 Children 제거
            res.startAt = child.startAt
            res.endAt = child.endAt
            res.children = None
            final_results_processed.append(res)
        else:
            final_results_processed.append(res)

    results = final_results_processed

    # 4. 결과 반환
    # 내부 상태 업데이트
    state.finalResults = results
    
    # 가동률(Fill Rate) 계산: 배정된 작업 수 / 전체 FLEX 수
    if len(all_flex_ids) > 0:
        state.fillRate = len(assigned_task_ids) / len(all_flex_ids)
    else:
        state.fillRate = 1.0
        
    # [Logfire] 결과 명시적 기록
    logfire.info("Node 5 Result", final_results=results, fill_rate=state.fillRate)
    
    return state


def _get_dominant_timezone(session: FreeSession) -> str:
    """
    세션의 지배적 시간대(Dominant TimeZone)를 판별
    - 각 시간대별(MORNING 등) 겹치는 분(minute)을 계산
    - 가장 많이 겹치는 시간대를 반환
    - 동점 시: MORNING > AFTERNOON > EVENING > NIGHT 순 (앞 시간대 우선)
    """
    # session.timeZoneProfile: Dict[TimeZone, int] (이미 계산되어 있음)
    # 예: {"MORNING": 30, "AFTERNOON": 90}
    
    if not session.timeZoneProfile:
        return "MORNING" # Fallback

    # 정렬 우선순위: (분량 내림차순, 시간대 순서 오름차순)
    # 시간대 순서 매핑
    tz_order = {"MORNING": 0, "AFTERNOON": 1, "EVENING": 2, "NIGHT": 3}
    
    sorted_tz = sorted(
        session.timeZoneProfile.items(),
        key=lambda item: (-item[1], tz_order.get(item[0], 99))
    )
    
    return sorted_tz[0][0]


def _append_child_to_result(results: List[AssignmentResult], parent_id: int, 
                            parent_title: str, start: str, end: str, seq: int):
    """결과 리스트에서 부모를 찾아 child 추가"""
    # results는 순차적으로 append 되므로, 뒤에서부터 찾는 게 빠를 수 있음
    # 혹은 map을 안쓰므로 순회해야 함.
    parent = next((r for r in results if r.taskId == parent_id), None)
    if not parent:
        # 혹시 모를 에러 방지 (부모가 없는데 자식이 생길 순 없음)
        return

    if parent.children is None:
        parent.children = []
    
    parent.children.append(SubTaskResult(
        title=f"{parent_title} - {seq}",
        startAt=start,
        endAt=end
    ))

