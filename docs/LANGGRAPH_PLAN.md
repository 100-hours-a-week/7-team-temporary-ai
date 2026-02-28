# LangGraph 기반 AI 플래너 생성 파이프라인 구현 계획

> 작성일: 2026-01-23
> 참조 문서: [V1-플래너생성-파이프라인.md](../V1-플래너생성-파이프라인.md)

---

## 목표

`POST /ai/v1/planners/v2` API를 LangGraph 기반 5개 노드 파이프라인으로 구현

### 파이프라인 흐름
```
Request → Preprocess → Node1 → Node2 → Node3 → Node4 → Node5 → Response
                       (LLM)   (수식)   (LLM)   (수식)   (수식)
```

---

## 구현 순서

| 단계 | 작업 | 설명 |
|------|------|------|
| 1 | [Supabase DB 설정](#1-supabase-db-설정) | 테이블 생성, 연결 설정 |
| 2 | [기반 구조](#2-기반-구조) | 모델 정의, 유틸리티, LLM 클라이언트 |
| 3 | [Node1 구현](#3-node1-task-structure-analysis) | 카테고리/그룹/순서 추출 (LLM) |
| 4 | [Node2 구현](#4-node2-task-importance) | 중요도/피로도 계산 (수식) |
| 5 | [Node3 구현](#5-node3-task-chain-generator) | 체인 후보 생성 (LLM) |
| 6 | [Node4 구현](#6-node4-chain-judgement) | 체인 점수 산출 및 선택 (수식) |
| 7 | [Node5 구현](#7-node5-task-time-assignment) | 최종 시간 배치 (수식) |
| 8 | [그래프 조립](#8-그래프-조립) | LangGraph StateGraph 구성 |
| 9 | [API 통합](#9-api-통합-및-테스트) | FastAPI 라우터, 테스트 |

---

## 1. Supabase DB 설정

### 1.1 DB 스키마 및 API 연동
전체 데이터베이스 스키마와 API 연동 가이드는 **[docs/DB_SCHEMA_AND_API.md](DB_SCHEMA_AND_API.md)** 문서로 이동되었습니다.
해당 문서를 참조하여 테이블을 생성하고, 환경 변수 및 설정을 구성하십시오.


---

## 2. 기반 구조

### 2.1 디렉토리 생성

```
app/
├── models/planner/
│   ├── __init__.py
│   ├── request.py      # ArrangementState, UserInfo, ScheduleItem
│   ├── response.py     # PlannerResponse, AssignmentResult
│   ├── internal.py     # FreeSession, TaskFeature, ChainCandidate
│   └── weights.py      # WeightParams
├── services/planner/utils/
│   ├── __init__.py
│   ├── time_utils.py   # 시간 변환 함수
│   └── session_utils.py # FreeSession 계산
├── db/
│   ├── __init__.py
│   └── supabase_client.py
└── llm/
    ├── __init__.py
    ├── gemini_client.py
    └── prompts/
        ├── __init__.py
        ├── node1_prompt.py
        └── node3_prompt.py
```

### 2.2 핵심 모델 정의

**request.py:**
```python
class UserInfo(BaseModel):
    userId: int
    focusTimeZone: TimeZone  # MORNING | AFTERNOON | EVENING | NIGHT
    dayEndTime: str          # "HH:MM"

class ScheduleItem(BaseModel):
    taskId: int
    parentScheduleId: Optional[int]
    dayPlanId: int
    title: str
    type: TaskType           # FIXED | FLEX
    startAt: Optional[str]
    endAt: Optional[str]
    estimatedTimeRange: Optional[EstimatedTimeRange]
    focusLevel: Optional[int]
    isUrgent: Optional[bool]

class ArrangementState(BaseModel):
    user: UserInfo
    startArrange: str
    schedules: List[ScheduleItem]
    groups: List[GroupInfo]
```

**weights.py (기본값):**
```python
class WeightParams(BaseModel):
    w_focus: float = 1.0
    w_urgent: float = 5.0
    w_overflow: float = 2.0
    w_fatigue_risk: float = 0.5
    alpha_duration: float = 0.05
    beta_load: float = 1.0
    # ... 기타 가중치
```

### 2.3 시간 유틸리티

```python
# time_utils.py
def hhmm_to_minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m

def minutes_to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def get_timezone(minutes: int) -> TimeZone:
    if 480 <= minutes < 720:    return "MORNING"    # 08:00-12:00
    if 720 <= minutes < 1080:   return "AFTERNOON"  # 12:00-18:00
    if 1080 <= minutes < 1260:  return "EVENING"    # 18:00-21:00
    return "NIGHT"                                   # 21:00-08:00
```

### 2.4 의존성 추가

```
# requirements.txt
langgraph>=0.2.0
langchain-core>=0.3.0
supabase>=2.0.0
```

---

## 3. Node1: Task Structure Analysis

> **타입**: LLM
> **역할**: 카테고리/그룹/순서 추출, cognitiveLoad 분류

### 3.1 입력/출력

| 구분 | 내용 |
|------|------|
| 입력 | FLEX 작업 목록, groups 리스트 |
| 출력 | TaskFeature (category, cognitiveLoad, groupId, orderInGroup) |

### 3.2 LLM 프롬프트

```python
# prompts/node1_prompt.py
NODE1_SYSTEM_PROMPT = """
당신은 작업 분류 전문가입니다.
주어진 작업 목록을 분석하여 카테고리와 인지 부하를 분류하세요.

출력 형식 (JSON):
{
  "tasks": [
    {"taskId": 1, "category": "학업", "cognitiveLoad": "HIGH"}
  ]
}

카테고리 예시: 학업, 업무, 운동, 취미, 생활, 기타
cognitiveLoad: LOW(단순 작업) | MED(보통) | HIGH(고집중 필요)
"""
```

### 3.3 구현

```python
# nodes/node1_structure_analysis.py
async def node1_structure_analysis(state: PlannerGraphState) -> PlannerGraphState:
    flex_tasks = state["flexTasks"]

    # LLM 호출
    response = await gemini_client.generate(
        system=NODE1_SYSTEM_PROMPT,
        user=format_tasks_for_llm(flex_tasks)
    )

    # 파싱 및 TaskFeature 생성
    parsed = parse_node1_response(response)

    task_features = {}
    for task in flex_tasks:
        llm_result = find_task_result(parsed, task.taskId)
        task_features[task.taskId] = TaskFeature(
            taskId=task.taskId,
            category=llm_result.get("category", "기타"),
            cognitiveLoad=llm_result.get("cognitiveLoad", "MED"),
            groupId=str(task.parentScheduleId) if task.parentScheduleId else None,
            # ... 기타 필드
        )

    return {**state, "taskFeatures": task_features}
```

### 3.4 폴백 전략

```python
def node1_fallback(state: PlannerGraphState) -> PlannerGraphState:
    """LLM 실패 시 기본값 사용"""
    task_features = {}
    for task in state["flexTasks"]:
        # estimatedTimeRange 기반 cognitiveLoad 추론
        cognitive = infer_cognitive_load(task.estimatedTimeRange)
        task_features[task.taskId] = TaskFeature(
            taskId=task.taskId,
            category="기타",
            cognitiveLoad=cognitive,
            groupId=str(task.parentScheduleId) if task.parentScheduleId else None,
        )
    return {**state, "taskFeatures": task_features}
```

---

## 4. Node2: Task Importance

> **타입**: 수식
> **역할**: importanceScore, fatigueCost, 분할 파라미터 계산

### 4.1 입력/출력

| 구분 | 내용 |
|------|------|
| 입력 | TaskFeature (Node1), WeightParams |
| 출력 | TaskFeature (importanceScore, fatigueCost, 분할 파라미터 추가) |

### 4.2 수식

**중요도 계산:**
```
importanceScore = focusLevel × w_focus
                + (isUrgent ? w_urgent : 0)
                + w_category.get(category, 0)
```

**피로도 계산:**
```
cognitiveLoad_value = {LOW: 0, MED: 1, HIGH: 2}
fatigueCost = durationPlanMin × α_duration + cognitiveLoad_value × β_load
```

### 4.3 분할 파라미터

| EstimatedTimeRange | avgMin | planMin | minChunk | maxChunk |
|--------------------|--------|---------|----------|----------|
| MINUTE_UNDER_30 | 20 | 30 | 10 | 30 |
| MINUTE_30_TO_60 | 45 | 60 | 20 | 60 |
| HOUR_1_TO_2 | 90 | 120 | 40 | 90 |

### 4.4 구현

```python
# nodes/node2_importance.py
DURATION_PARAMS = {
    "MINUTE_UNDER_30": {"avg": 20, "plan": 30, "min": 10, "max": 30},
    "MINUTE_30_TO_60": {"avg": 45, "plan": 60, "min": 20, "max": 60},
    "HOUR_1_TO_2":     {"avg": 90, "plan": 120, "min": 40, "max": 90},
}

def node2_importance(state: PlannerGraphState) -> PlannerGraphState:
    weights = state["weights"]
    task_features = state["taskFeatures"].copy()

    for task_id, feature in task_features.items():
        original_task = find_task(state["flexTasks"], task_id)

        # 중요도 계산
        importance = (
            (original_task.focusLevel or 5) * weights.w_focus +
            (weights.w_urgent if original_task.isUrgent else 0)
        )

        # 분할 파라미터
        params = DURATION_PARAMS.get(original_task.estimatedTimeRange, DURATION_PARAMS["MINUTE_30_TO_60"])

        # 피로도 계산
        cog_value = {"LOW": 0, "MED": 1, "HIGH": 2}[feature.cognitiveLoad]
        fatigue = params["plan"] * weights.alpha_duration + cog_value * weights.beta_load

        # 업데이트
        feature.importanceScore = importance
        feature.fatigueCost = fatigue
        feature.durationAvgMin = params["avg"]
        feature.durationPlanMin = params["plan"]
        feature.durationMinChunk = params["min"]
        feature.durationMaxChunk = params["max"]

    return {**state, "taskFeatures": task_features}
```

---

## 5. Node3: Task Chain Generator

> **타입**: LLM
> **역할**: 시간대 버킷 기반 체인 후보 생성

### 5.1 입력/출력

| 구분 | 내용 |
|------|------|
| 입력 | TaskFeature, 시간대별 capacity, focusTimeZone |
| 출력 | ChainCandidate[] (4-6개) |

### 5.2 시간대별 Capacity 계산

```python
def calculate_capacity(free_sessions: List[FreeSession]) -> Dict[TimeZone, int]:
    capacity = {"MORNING": 0, "AFTERNOON": 0, "EVENING": 0, "NIGHT": 0}
    for session in free_sessions:
        for tz, minutes in session.timeZoneProfile.items():
            capacity[tz] += minutes
    return capacity
```

### 5.3 LLM 프롬프트

```python
NODE3_SYSTEM_PROMPT = """
당신은 일정 배치 전문가입니다.
주어진 작업들을 시간대별로 배치하는 후보 체인 4-6개를 생성하세요.

규칙:
- 각 시간대 용량의 110-120%까지 과적재 허용
- 사용자의 집중 시간대(focusTimeZone)에 고몰입 작업 우선 배치
- 그룹 내 순서(orderInGroup) 유지

출력 형식 (JSON):
{
  "candidates": [
    {
      "chainId": "C1",
      "timeZoneQueues": {
        "MORNING": [taskId1, taskId2],
        "AFTERNOON": [taskId3],
        "EVENING": [],
        "NIGHT": []
      },
      "rationaleTags": ["focus_zone_first"]
    }
  ]
}
"""
```

### 5.4 구현

```python
# nodes/node3_chain_generator.py
async def node3_chain_generator(state: PlannerGraphState) -> PlannerGraphState:
    task_features = state["taskFeatures"]
    free_sessions = state["freeSessions"]
    focus_zone = state["request"].user.focusTimeZone

    # Capacity 계산
    capacity = calculate_capacity(free_sessions)

    # LLM 입력 준비
    tasks_info = [
        {
            "taskId": f.taskId,
            "title": f.title,
            "importance": f.importanceScore,
            "duration": f.durationAvgMin,
            "groupId": f.groupId,
            "orderInGroup": f.orderInGroup
        }
        for f in task_features.values()
    ]

    # LLM 호출
    response = await gemini_client.generate(
        system=NODE3_SYSTEM_PROMPT,
        user=json.dumps({
            "tasks": tasks_info,
            "capacity": capacity,
            "focusTimeZone": focus_zone
        })
    )

    candidates = parse_node3_response(response)
    return {**state, "chainCandidates": candidates}
```

### 5.5 폴백 전략

```python
def node3_fallback(state: PlannerGraphState) -> PlannerGraphState:
    """importanceScore 내림차순으로 단일 체인 생성"""
    sorted_tasks = sorted(
        state["taskFeatures"].values(),
        key=lambda f: f.importanceScore,
        reverse=True
    )

    # 모든 작업을 MORNING 큐에 (Node5가 실제 배치)
    chain = ChainCandidate(
        chainId="fallback",
        timeZoneQueues={
            "MORNING": [t.taskId for t in sorted_tasks],
            "AFTERNOON": [],
            "EVENING": [],
            "NIGHT": []
        }
    )
    return {**state, "chainCandidates": [chain]}
```

---

## 6. Node4: Chain Judgement

> **타입**: 수식
> **역할**: Closure 적용, Overflow 계산, 최적 체인 선택

### 6.1 입력/출력

| 구분 | 내용 |
|------|------|
| 입력 | ChainCandidate[], TaskFeature, WeightParams |
| 출력 | selectedChainId |

### 6.2 Overflow 페널티 (단계적)

```python
def overflow_penalty(overflow: int, capacity: int, w_overflow: float) -> float:
    safe_buffer = capacity * 0.2  # 20% 완충
    if overflow <= safe_buffer:
        return 0.001 * overflow   # 미세 페널티
    else:
        excess = overflow - safe_buffer
        return w_overflow * (excess ** 2)  # 기하급수 페널티
```

### 6.3 체인 점수 수식

```
Score = w_included × Σ(importance of included tasks)
      - w_excluded × Σ(importance of excluded tasks)
      - w_overflow × P_overflow
      - w_fatigue_risk × P_fatigue
      + w_focus_align × FocusAlignScore
```

### 6.4 구현

```python
# nodes/node4_chain_judgement.py
def node4_chain_judgement(state: PlannerGraphState) -> PlannerGraphState:
    candidates = state["chainCandidates"]
    task_features = state["taskFeatures"]
    weights = state["weights"]
    capacity = calculate_capacity(state["freeSessions"])

    best_chain = None
    best_score = float("-inf")

    for chain in candidates:
        # 1. Closure 적용 (그룹 순서 위반 처리)
        chain = apply_closure(chain, task_features)

        # 2. Overflow 계산
        overflow_total = 0
        for tz, task_ids in chain.timeZoneQueues.items():
            total_duration = sum(task_features[tid].durationAvgMin for tid in task_ids)
            overflow = max(0, total_duration - capacity.get(tz, 0))
            overflow_total += overflow_penalty(overflow, capacity.get(tz, 1), weights.w_overflow)

        # 3. 포함/제외 점수
        included_ids = set()
        for ids in chain.timeZoneQueues.values():
            included_ids.update(ids)

        included_score = sum(task_features[tid].importanceScore for tid in included_ids)
        excluded_ids = set(task_features.keys()) - included_ids
        excluded_score = sum(task_features[tid].importanceScore for tid in excluded_ids)

        # 4. 총점 계산
        score = (
            weights.w_included * included_score
            - weights.w_excluded * excluded_score
            - overflow_total
        )

        if score > best_score:
            best_score = score
            best_chain = chain

    return {**state, "selectedChainId": best_chain.chainId}
```

---

## 7. Node5: Task Time Assignment

> **타입**: 수식
> **역할**: 최종 시간 배치, 분할, 휴식 삽입, tail-drop

### 7.1 입력/출력

| 구분 | 내용 |
|------|------|
| 입력 | selectedChainId, FreeSession[], TaskFeature |
| 출력 | AssignmentResult[] |

### 7.2 핵심 로직

1. 세션 순회 (startAt 오름차순)
2. **시간대 판별 (Dominant TimeZone)**: 해당 세션에 가장 많이 포함된 시간대를 선택 (동점 시 앞 시간대)
3. 시간대별 큐에서 작업 pop 및 배치
4. **분할 (Splitting)**: 세션 잔여 시간보다 작업이 길면 분할 (`children` 생성, 부모는 시간 null) (MaxChunk 강제분할은 V2로 연기)
5. **자투리 우선 (Remainder First)**: 분할 후 남은 자투리는 다음 세션에 무조건 최우선 배치 (V1: Priority Flip 없음)
6. **휴식 (Gap)**: 작업 배정 직후(Inter-cycle) 휴식만 삽입함. (작업 도중 휴식은 V2로 연기)
7. **제외 (Tail Drop)**: 가용 시간 부족 시 남은 작업 `EXCLUDED` 처리
8. **그룹 롤백**: 그룹 제약 위반 시 후행 작업 제외

### 7.3 구현

```python
# nodes/node5_time_assignment.py
def node5_time_assignment(state: PlannerGraphState) -> PlannerGraphState:
    selected_chain = find_chain(state["chainCandidates"], state["selectedChainId"])
    sessions = sorted(state["freeSessions"], key=lambda s: hhmm_to_minutes(s.startAt))
    task_features = state["taskFeatures"]

    results: List[AssignmentResult] = []
    queues = {tz: list(ids) for tz, ids in selected_chain.timeZoneQueues.items()}
    assigned_ids = set()

    for session in sessions:
        current_time = hhmm_to_minutes(session.startAt)
        end_time = hhmm_to_minutes(session.endAt)
        tz = get_dominant_timezone(session)

        while current_time < end_time and queues[tz]:
            task_id = queues[tz][0]
            feature = task_features[task_id]
            remaining = end_time - current_time

            if feature.durationPlanMin <= remaining:
                # 전체 배치
                results.append(AssignmentResult(
                    taskId=task_id,
                    assignmentStatus="ASSIGNED",
                    startAt=minutes_to_hhmm(current_time),
                    endAt=minutes_to_hhmm(current_time + feature.durationPlanMin),
                    children=None
                ))
                current_time += feature.durationPlanMin
                queues[tz].pop(0)
                assigned_ids.add(task_id)
            else:
                # 분할 필요
                children = split_task(feature, current_time, end_time, sessions)
                results.append(AssignmentResult(
                    taskId=task_id,
                    assignmentStatus="ASSIGNED",
                    startAt=None,
                    endAt=None,
                    children=children
                ))
                queues[tz].pop(0)
                assigned_ids.add(task_id)
                break

    # EXCLUDED 처리
    for task_id in task_features.keys():
        if task_id not in assigned_ids:
            results.append(AssignmentResult(
                taskId=task_id,
                assignmentStatus="EXCLUDED",
                startAt=None,
                endAt=None,
                children=None
            ))

    # 가동률 체크
    fill_rate = len(assigned_ids) / len(task_features)

    return {**state, "finalResults": results, "fillRate": fill_rate}
```

### 7.4 분할 함수

```python
def split_task(feature: TaskFeature, start: int, session_end: int,
               all_sessions: List[FreeSession]) -> List[SubTaskResult]:
    children = []
    remaining = feature.durationPlanMin
    current = start
    sequence = 1

    while remaining > 0:
        available = session_end - current
        chunk = min(available, feature.durationMaxChunk, remaining)

        if chunk < feature.durationMinChunk:
            # 다음 세션으로
            break

        children.append(SubTaskResult(
            subTaskId=f"{feature.taskId}_{sequence}",
            parentTaskId=feature.taskId,
            title=f"{feature.title} - {sequence}",
            startAt=minutes_to_hhmm(current),
            endAt=minutes_to_hhmm(current + chunk)
        ))

        remaining -= chunk
        current += chunk
        sequence += 1

    return children
```

---

## 8. 그래프 조립

### 8.1 StateGraph 구성

```python
# graphs/planner/graph.py
from langgraph.graph import StateGraph, END

def create_planner_graph():
    graph = StateGraph(PlannerGraphState)

    # 노드 추가
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("node1", node1_structure_analysis)
    graph.add_node("node1_fallback", node1_fallback)
    graph.add_node("node2", node2_importance)
    graph.add_node("node3", node3_chain_generator)
    graph.add_node("node3_fallback", node3_fallback)
    graph.add_node("node4", node4_chain_judgement)
    graph.add_node("node5", node5_time_assignment)
    graph.add_node("postprocess", postprocess_node)

    # 엣지 정의
    graph.set_entry_point("preprocess")
    graph.add_edge("preprocess", "node1")
    graph.add_conditional_edges("node1", should_retry_node1, {
        "retry": "node1",
        "fallback": "node1_fallback",
        "continue": "node2"
    })
    graph.add_edge("node1_fallback", "node2")
    graph.add_edge("node2", "node3")
    graph.add_conditional_edges("node3", should_retry_node3, {
        "retry": "node3",
        "fallback": "node3_fallback",
        "continue": "node4"
    })
    graph.add_edge("node3_fallback", "node4")
    graph.add_edge("node4", "node5")
    graph.add_conditional_edges("node5", should_replan, {
        "replan": "node4",
        "end": "postprocess"
    })
    graph.add_edge("postprocess", END)

    return graph.compile()
```

### 8.2 조건부 엣지

```python
# graphs/planner/edges.py
def should_retry_node1(state: PlannerGraphState) -> str:
    if state.get("node1_error") and state["retry_node1"] < 2:
        return "retry"
    elif state.get("node1_error"):
        return "fallback"
    return "continue"

def should_replan(state: PlannerGraphState) -> str:
    if state.get("fillRate", 1.0) < 0.6 and state["replan_loops"] < 2:
        return "replan"
    return "end"
```

---

## 9. API 통합 및 테스트

### 9.1 라우터

```python
# app/api/v1/planners.py
from fastapi import APIRouter, BackgroundTasks
from app.graphs.planner.graph import create_planner_graph

router = APIRouter(prefix="/ai/v1", tags=["AI Planner (LangGraph)"])
planner_graph = create_planner_graph()

@router.post("/planners/v2", response_model=PlannerResponse)
async def create_planner_v2(
    request: ArrangementState,
    background_tasks: BackgroundTasks
):
    start_time = time.time()

    # 초기 상태 구성
    initial_state = {
        "request": request,
        "weights": await load_user_weights(request.user.userId),
        "fixedTasks": [s for s in request.schedules if s.type == "FIXED"],
        "flexTasks": [s for s in request.schedules if s.type == "FLEX"],
        "retry_node1": 0,
        "retry_node3": 0,
        "replan_loops": 0,
    }

    # 그래프 실행
    final_state = await planner_graph.ainvoke(initial_state)

    process_time = time.time() - start_time

    # 비동기 저장
    background_tasks.add_task(
        save_snapshot,
        request.user.userId,
        final_state["finalResults"]
    )

    return PlannerResponse(
        success=True,
        processTime=process_time,
        userId=request.user.userId,
        results=final_state["finalResults"],
        totalCount=len(final_state["finalResults"])
    )
```

### 9.2 main.py 수정

```python
# app/main.py
from app.api.v1 import planners

app.include_router(planners.router)
```

### 9.3 테스트

```bash
# 서버 실행
uvicorn app.main:app --reload

# Swagger UI
# http://localhost:8000/docs

# POST /ai/v1/planners/v2 테스트
```

---

## 체크리스트

- [ ] **1. Supabase DB 설정**
  - [ ] 테이블 생성 (user_weights, planner_snapshots)
  - [ ] 환경 변수 설정
  - [ ] Supabase 클라이언트 구현

- [ ] **2. 기반 구조**
  - [ ] 모델 정의 (request, response, internal, weights)
  - [ ] 시간 유틸리티 구현
  - [ ] LLM 클라이언트 구현

- [ ] **3. Node1 구현**
  - [ ] 프롬프트 작성
  - [ ] 노드 함수 구현
  - [ ] 폴백 함수 구현

- [ ] **4. Node2 구현**
  - [ ] 수식 구현
  - [ ] 단위 테스트

- [ ] **5. Node3 구현**
  - [ ] 프롬프트 작성
  - [ ] 노드 함수 구현
  - [ ] 폴백 함수 구현

- [ ] **6. Node4 구현**
  - [ ] Overflow 페널티 구현
  - [ ] 체인 점수 계산 구현
  - [ ] 단위 테스트

- [ ] **7. Node5 구현**
  - [ ] 배치 로직 구현
  - [ ] 분할 로직 구현
  - [ ] 단위 테스트

- [ ] **8. 그래프 조립**
  - [ ] StateGraph 구성
  - [ ] 조건부 엣지 구현

- [ ] **9. API 통합**
  - [ ] 라우터 구현
  - [ ] main.py 수정
  - [ ] 통합 테스트
