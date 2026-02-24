# AI 플래너 생성 서비스 구현 계획 (LangGraph & Supabase 기반)

`api명세서.md`의 `POST /ai/v1/planners` 기능을 `docs/LANGGRAPH_PLAN.md`에 정의된 아키텍처와 상세 설계를 바탕으로 구현하기 위한 단계별 계획입니다.

## 1. 개요
현재의 `gemini-test`용 단순 엔드포인트를 LangGraph 기반의 5단계 파이프라인(전처리 -> 구조 분석 -> 중요도 산정 -> 체인 생성 -> 시간 확정)으로 고도화하고, Supabase에 개인화 학습을 위한 데이터를 축적하는 구조를 구축합니다.

---

## 2. 사전 준비 및 인프라 (Supabase)

`docs/LANGGRAPH_PLAN.md`에 정의된 테이블 구조를 그대로 적용하여 개인화 학습(IRL) 및 로그 분석을 위한 기반을 마련합니다.

### **[Step 1] Supabase 테이블 생성**
다음 3개의 테이블을 생성합니다.
1.  **`user_weights`**: 사용자별 개인화 가중치 저장 (JSONB 활용)
    -   `user_id` (PK, UK)
    -   `weights` (JSONB): `w_focus`, `w_urgent` 등 모든 가중치 파라미터 포함
2.  **`planner_records`**: 플래너 생성/수정 이력 메타데이터
    -   `record_type`: 'AI_DRAFT'(AI 생성본) vs 'USER_FINAL'(사용자 최종본) 구분
    -   `start_arrange`, `day_end_time`, `focus_time_zone` 등 컨텍스트 저장
    -   `selected_chain_id` (Node4 결과), `fill_rate` 등 결과 지표 저장
3.  **`record_tasks`**: 개별 작업의 상세 분석 및 배치 결과
    -   `record_id` (FK)
    -   `category`, `group_id` (Node1 분석 결과)
    -   `importance_score`, `fatigue_cost` (Node2 계산 결과)
    -   `assignment_status`, `start_at`, `end_at`, `children` (Node5 배치 결과)

### **[Step 2] 환경 변수 및 패키지 설정**
- `requirements.txt`: `langgraph`, `supabase`, `sentence-transformers` 등 추가
- `.env`: `SUPABASE_URL`, `SUPABASE_KEY` 확인

---

## 3. LangGraph 파이프라인 구현

`PlannerGraphState`를 정의하고 5개의 노드를 순차적으로 구현합니다.

### **[Step 3] State 정의 (PlannerGraphState)**
- **Input**: `ArrangementState` (API Request Wrapper)
- **Shared**:
  - `taskFeatures`: Dict[int, TaskFeature] (Node1, Node2 결과 누적)
  - `freeSessions`: List[FreeSession] (가용 시간 슬롯)
  - `weights`: UserWeights (DB에서 로드한 가중치)
  - `chainCandidates`: List[ChainCandidate] (Node3 결과)
  - `selectedChainId`: str (Node4 결과)
  - `finalResults`: List[AssignmentResult] (Node5 결과)
  - `internal_logs`: 실행 로그 Key-Value

### **[Step 4] Node 1: 구조 분석 (Structure Analysis)**
- **역할**: LLM(Gemini)을 이용해 작업의 문맥을 파악하고 그룹핑 수행
- **기능**:
  - Task의 `Category` 분류 (학업, 업무, 자기계발 등)
  - `GroupId`, `OrderInGroup` 추출 (연관 작업 묶기)
  - `CognitiveLoad` (인지 부하) 추정
- **Fallback**: LLM 실패 시 기본값(카테고리=ETC, 그룹없음) 처리

### **[Step 5] Node 2: 중요도 산정 (Importance Scoring)**
- **역할**: 수식(Function) 기반으로 작업별 정량적 점수 계산
- **기능**:
  - $Score = w_{focus} \cdot P(timezone) + w_{urgent} \cdot I(urgent) + \dots$
  - `weights` (JSONB)에 저장된 사용자별 가중치 적용
  - `fatigue_cost`, `duration_plan_min`(배치용 보정 시간) 등 계산

### **[Step 6] Node 3: 체인 생성 (Chain Generator)**
- **역할**: LLM(Gemini)을 이용해 시간대(TimeZone)별 작업 분배 제안
- **기능**:
  - **Output**: `timeZoneQueues` (MORNING, AFTERNOON, EVENING, NIGHT)
  - 사용자의 선호 시간대(`focus_time_zone`) 및 작업 성격 고려
  - JSON Schema 검증으로 형식을 강제하여 파싱 에러 최소화

### **[Step 7] Node 4: 체인 평가 및 선택 (Chain Judgement)**
- **역할**: Node3에서 생성한 복수의 후보(Chain) 중 최적의 안 선택
- **기능**:
  - 오버플로우(시간 초과) 페널티 계산
  - 시간대 선호도 점수 합산
  - 제약 조건(그룹 순서 등) 위반 여부 체크

### **[Step 8] Node 5: 시간 할당 (Time Assignment)**
- **역할**: 결정론적(Deterministic) 알고리즘으로 분 단위 구체적 시간 확정
- **기능**:
  - **Bin Packing**: 가용 세션(`freeSessions`)에 작업 순차 배치
  - **Splitting**: 세션보다 작업이 길 경우에만 자동 분할 (`children` 생성). MaxChunk 기반 강제 분할은 V2로 연기.
  - **TimeZone Alignment**: 세션의 지배적(Dominant) 시간대(동점 시 앞 시간대)를 따름
  - **Break (Gap)**: 작업과 작업 사이(Inter-task)에만 휴식 삽입. (작업 도중 휴식은 V2로 연기)
  - **Tail Drop**: 가용 시간 부족 시 잔여 작업 `EXCLUDED` 처리
  - **Soft Rollback**: 그룹 작업의 일부만 배치된 경우 전체 제외 등 후처리

---

## 4. 백엔드 통합

### **[Step 9] Service Layer 구현**
- `app/graphs/planner/graph.py`: StateGraph 조립 및 컴파일
- `app/services/planner_service.py`:
  1. DB에서 `user_weights` 로드
  2. `planner_graph.ainvoke()` 실행
  3. 결과 파싱 및 `planner_records`, `record_tasks`에 **비동기 저장(BackgroundTasks)**

### **[Step 10] API 엔드포인트 연결**
- `POST /ai/v1/planners` 엔드포인트가 새 Service를 호출하도록 변경
- Request/Response Schema는 기존 `api명세서.md`를 준수

---

## 5. 저장 및 개인화 (Post-Processing)

### **[Step 11] 결과 저장 로직 구현 (AI Draft)**
- Response 반환 전/후에 Supabase 저장 로직 수행
- **`planner_records`**: `record_type='AI_DRAFT'`로 메타데이터 저장
- **`record_tasks`**: 각 Task의 Node1~Node5 처리 결과를 상세히 저장
- **참고**: 이 단계에서는 `task_embeddings`를 생성하지 않습니다. (미확정 데이터)

### **[Step 12] 데이터 수집 및 임베딩 (User Final)**
- `POST /ai/v1/personalizations/ingest` 엔드포인트 구현
- **`planner_records`**: `record_type='USER_FINAL'` 저장
- **`task_embeddings`**: 최종 확정된 작업에 대해 **즉시 임베딩 생성** (Gemini 768dim, 변경 가능)
- **`task_embeddings`** 테이블 저장 시 `record_tasks` 참조

---

## 6. 테스트 및 검증

1. **단위 테스트**: 각 Node(Function)별 입출력 검증
2. **통합 테스트**: 전체 파이프라인(`ainvoke`) 실행 후 결과 포맷 검증
3. **DB 확인**: Supabase 테이블에 데이터가 스키마대로 정확히 적재되는지 확인
