# 개발 진행 상황

날짜별 개발 진행 상황을 기록합니다.

---


## 2026-01-29

### 10분 단위 시간 배정 (Time Granularity) 적용

**목적**: 플래너의 가독성을 높이고 사용자 경험을 개선하기 위해, 모든 AI 배정 작업(FLEX)의 시간 단위를 10분(10, 20, 30...)으로 통일함.

#### 주요 변경 사항

1. **[app/services/planner/nodes/node5_time_assignment.py](app/services/planner/nodes/node5_time_assignment.py)**
   - **Start Time Alignment**: 세션 시작 시간이 10분 단위가 아닐 경우(예: 09:03), 다음 10분 단위(09:10)로 올림 처리.
   - **End Time Alignment**: 세션 종료 시간이 10분 단위가 아닐 경우(예: 09:17), 이전 10분 단위(09:10)로 내림 처리하여 자투리 시간 발생 방지.
   - **FLEX Task Guarantee**: 사용자가 설정한 FIXED 일정이 불규칙하더라도(분 단위), AI가 배정하는 FLEX 일정은 항상 깔끔한 10분 단위로 생성됨을 보장.

2. **[tests_local/test_planner_granularity.py](tests_local/test_planner_granularity.py)** (신규)
   - **검증**: 불규칙한 시작/종료 시간(Irregular Session boundaries)에 대해 올비르게 정렬되는지 확인하는 전용 테스트 작성.

### LangSmith 도입 (Local LLM Debugging)

**목적**: 복잡한 LangGraph 파이프라인의 디버깅 효율을 높이기 위해, 로컬 개발 환경에 한해 상세한 LLM 실행 추적(Trace) 도구인 LangSmith를 도입함. (실서버 배포 시에는 비활성화)

#### 주요 변경 사항

1. **[requirements.txt](requirements.txt)**
   - **라이브러리 추가**: `langsmith==0.4.37` 및 `urllib3==1.26.20`.
   - **버전 정책**: Python 3.9 호환성 및 네트워크 안정성을 위해 검증된 버전으로 명시적 고정.

2. **[app/llm/gemini_client.py](app/llm/gemini_client.py)**
   - **Instrumentation**: `generate` 메서드에 `@traceable` 데코레이터 적용.
   - **효과**: LangChain을 사용하지 않는 직접 API 호출 방식에서도 LangSmith에 자동으로 로그가 남도록 설정.

3. **[tests_local/test_langsmith.py](tests_local/test_langsmith.py)** (신규)
   - **연결 테스트**: API Key 및 네트워크 연결 상태를 진단하고, 강제로 테스트 로그를 전송하는 스크립트.

4. **[app/main.py](app/main.py)**
   - **환경 변수 로드**: `langsmith` 라이브러리가 초기화되기 전에 `.env` 파일의 설정을 먼저 읽어오도록 `load_dotenv()` 호출 시점 조정.



### Logfire 환경 변수 설정 공식화

**목적**: 클라우드 및 협업 환경에서 Logfire 연결을 위한 인증 토큰(`LOGFIRE_TOKEN`) 관리 체계를 수립하고, 코드 차원에서 이를 명시적으로 지원함.

#### 주요 변경 사항

1. **환경 변수 파일 업데이트**:
   - `.env`, `.env.example`, `.env.production`, `.env.staging` 파일에 `LOGFIRE_TOKEN` 변수 추가.
   - 로컬 개발 및 배포 환경별로 유연하게 토큰을 주입할 수 있는 기반 마련.

2. **[app/core/config.py](app/core/config.py)**
   - **설정 추가**: `Settings` 클래스에 `logfire_token: Optional[str]` 필드 추가.
   - **Configuration as Code**: 외부에서 주입된 토큰을 앱 설정 객체를 통해 접근 가능하도록 개선.

### DB 연동 (Planner Draft & User Weights)

**목적**: AI 플래너 생성 결과(`AI_DRAFT`)를 데이터베이스에 저장하여, 향후 개인화 학습(IRL) 및 성과 분석을 위한 데이터를 축적함. (사용자 가중치 조회는 현재 기본값 사용)

#### 주요 변경 사항

1. **[app/db/repositories/planner_repository.py](app/db/repositories/planner_repository.py)** (신규)
   - **기능**: `save_ai_draft` 메서드 구현 (FLEX 및 FIXED 작업 모두 저장).
   - **데이터 흐름**: `PlannerGraphState` → `planner_records` (메타데이터) → `record_tasks` (작업 상세) 순서로 저장.
   - **분할 작업(Splitting) 저장 전략**:
     - **부모 Row** (`is_split=True`): 시간 정보(`start_at`, `end_at`)는 `NULL`, 자식 정보는 `children` JSON 컬럼에 보관.
     - **자식 Row** (`is_split=False`): 부모와 동일한 `task_id`를 공유하며, 실제 시간 정보와 분할된 제목 저장.
   - **통계 저장**: 플래너 생성 시점의 `fill_rate`, `assigned_count` 등 주요 지표 자동 산출 및 저장.

2. **[app/api/v1/endpoints/planners.py](app/api/v1/endpoints/planners.py)**
   - **비동기 저장**: `POST /ai/v1/planners/test` 요청 처리 후, `BackgroundTasks`를 통해 사용자 응답 지연 없이 DB 저장 로직을 실행하도록 개선.

3. **[tests_local/test_planner_repository.py](tests_local/test_planner_repository.py)** (신규)
   - **검증**: Mock 데이터를 활용하여 `planner_records` 및 `record_tasks` 테이블에 데이터가 정상적으로 INSERT 되는지 확인하는 통합 테스트 작성.

---

## 2026-01-28

### LangGraph 파이프라인 완성 (Node 1 ~ Node 5)

**목적**: AI 플래너 생성 파이프라인의 핵심인 5단계 노드 구현을 모두 완료하고, 결정론적 시간 배정 로직(V1)을 적용하여 신뢰성 있는 플래너를 생성함.

#### 주요 변경 사항

1. **[app/services/planner/nodes/node5_time_assignment.py](app/services/planner/nodes/node5_time_assignment.py)** (신규)
   - **결정론적 시간 배정 (Deterministic Logic)**: Node 4가 선택한 최적 체인의 시간대별 대기열을 받아, 실제 분 단위 시간을 확정.
   - **Logic V1 정책 적용**:
     - **Gap-based Break**: 90분 이상 연속 작업 시 10분간 빈 시간(Gap)을 자동 삽입.
     - **Dominant TimeZone**: 세션이 여러 시간대에 걸칠 경우, 가장 많이 포함된 시간대를 기준으로 작업 할당.
     - **Remainder First**: 작업 분할(Splitting) 시 남은 자투리 작업은 다음 가용 세션의 최우선 순위로 배치.

2. **[tests/test_node5.py](tests/test_node5.py)** (신규)
   - **단위 테스트**: 기본 배정, 작업 분할(Splitting), MaxChunk 초과 시 Gap 삽입, 잔여 작업 제외(Tail Drop) 등 엣지 케이스 검증.

3. **[tests/test_integration_node1_to_node5.py](tests/test_integration_node1_to_node5.py)** (신규)
   - **전체 파이프라인 통합 테스트**: LLM 구조 분석(Node 1)부터 최종 시간 확정(Node 5)까지 데이터 흐름 검증.
   - **가시성 확보**: 결과 테이블에 FIXED 작업과 FLEX 작업을 시간순으로 정렬하여 전체 일정 가시화.

4. **관측성 강화 (Logfire)**
   - **전 구간 적용**: Node 1(구조), Node 2(중요도), Node 3(체인), Node 4(평가), Node 5(배정) 전 구간에 Logfire 적용 완료.
   - **Input/Result 로깅**: 각 노드의 입출력 데이터를 명시적으로 기록하여 디버깅 및 품질 모니터링 체계 구축.

5. **[app/api/v1/endpoints/planners.py](app/api/v1/endpoints/planners.py)** (신규)
   - **엔드포인트**: `POST /ai/v1/planners/test` 구현 (LangGraph 파이프라인 전체 연동).
   - **Dynamic Swagger Example**: `tests/data/test_request.json` 파일을 서버 시작 시 로드하여 Swagger UI 예시 데이터로 자동 설정.

6. **Logfire GenAI Analytics 적용**
   - **Manual Instrumentation**: `app/llm/gemini_client.py`에 OpenTelemetry Semantic Conventions 적용.
   - **기능**: LLM 토큰 사용량(비용) 분석, 프롬프트 디버깅(Replay) 대시보드 활성화. (향후 RunPod 등 타 LLM 도입 시 표준 가이드로 활용 가능)

### CI/CD 테스트 환경 구축 및 클라우드 배포 안정성 확보

**목적**: 클라우드(AWS, RunPod 등) 배포 환경에서 데이터 손상 없이 안전하게 실행 가능한 자동화 테스트 슈트를 구축하고, 로컬 개발 환경과 명확히 격리함.

#### 주요 변경 사항

1.  **클라우드 전용 테스트 (Cloud-Safe Tests) 구현**:
    - **[tests/test_connectivity.py](tests/test_connectivity.py)** (신규):
        - **네트워크 점검**: Gemini API 및 Supabase DB에 대한 단순 Ping/Auth 테스트 수행.
        - **비파괴적 검증**: 실제 데이터를 수정하지 않고 연결 상태만 확인함으로써 운영 환경에서도 안전하게 실행 가능.
    - **[tests/test_logic_mock.py](tests/test_logic_mock.py)** (신규):
        - **Mock 기반 검증**: `unittest.mock`을 활용하여 외부 LLM 호출 없이 Node 1~5 전체 파이프라인 로직을 시뮬레이션.
        - **무비용/고속 실행**: 토큰 비용 발생 없이 핵심 비즈니스 로직(Pydantic 모델 검증, 데이터 흐름 등)을 반복 테스트 가능.

2.  **테스트 구조 이원화 (격리 전략)**:
    - **`tests/`**: CI/CD 파이프라인 및 배포 직후 실행할 안전한 테스트만 포함.
    - **`tests_local/`**: 실제 DB에 Write하거나 유료 LLM을 사용하는 로컬 전용 테스트들을 이동.
    - **[.gitignore](.gitignore) 업데이트**: `tests_local/` 폴더를 제외 처리하여 실수로 운영 환경에 무거운 테스트 코드가 배포되는 것을 원천 차단.

3.  **의존성 및 실행 환경 표준화**:
    - **[requirements.txt](requirements.txt)**: `pytest`, `httpx` 등 테스트 실행에 필수적인 라이브러리 명시.
    - **실행 편의성**: `pytest tests/` 명령어 하나로 클라우드 배포 시 필수 점검 사항(연결성+로직)을 한 번에 검증 가능하도록 구성.

## 2026-01-27

### 개인화 데이터 수집 (Personalization Ingest) API 구현

**목적**: 사용자가 수정한 최종 플래너 데이터를 DB에 저장(Ingest)하여, 향후 개인화 학습(IRL)을 위한 기초 데이터를 확보함.

#### 주요 변경 사항

1. **[app/models/personalization.py](app/models/personalization.py)** (신규)
   - **Pydantic 모델**: `PersonalizationIngestRequest` 등 요청/응답 스키마 정의.
   - **Swagger 연동**: 일주일치 대용량 샘플 데이터를 예시로 탑재하여 즉시 테스트 가능하도록 설정.

2. **[app/db/repositories/personalization_repository.py](app/db/repositories/personalization_repository.py)** (신규)
   - **DB 연동**: Supabase Client를 통해 `planner_records`, `record_tasks`, `schedule_histories` 테이블에 트랜잭션 단위(논리적)로 데이터 저장.

3. **[app/api/v1/endpoints/personalization.py](app/api/v1/endpoints/personalization.py)** (신규)
   - **엔드포인트**: `POST /ai/v1/personalizations/ingest` 구현.

4. **[tests/data/personalization_ingest_week_sample.json](tests/data/personalization_ingest_week_sample.json)** (신규)
   - **테스트 데이터**: 일주일치 데모 데이터셋 생성 (Swagger UI 및 자동화 테스트 공용).

   - **테스트 데이터**: 일주일치 데모 데이터셋 생성 (Swagger UI 및 자동화 테스트 공용).

### API 안정성 및 유지보수 개선

**목적**: Swagger UI 가시성 확보 및 에러 핸들링 고도화를 통해 API 사용성 개선.

#### 주요 변경 사항

1. **에러 코드 확장 및 구조화**:
   - `PersonalizationErrorCode` 추가: `DB_CONNECTION_ERROR`, `DB_INSERT_ERROR` 등 구체적 에러 상황 식별 가능.
   - `PersonalizationIngestResponse`: `errorCode` 필드 추가로 클라이언트가 실패 원인을 명확히 파악 가능.

2. **Swagger UI 중복 라우터 버그 수정**:
   - `gemini_test_planners` 라우터 등록 시 중복 태그(`tags=["Gemini Test"]`) 제거.
   - 단일 엔드포인트가 두 개의 그룹으로 나뉘어 보이는 문제 해결.

3. **의존성 관리 강화**:
   - `requirements.txt`: `supabase==2.27.2` 등 주요 라이브러리 버전 명시.

### Ingest API 성능 최적화 및 로직 개선

**목적**: 대량의 개인화 데이터(일주일치)를 효율적으로 저장하고, 데이터 정합성을 확보함.

#### 주요 변경 사항

1.  **일주일치 데이터 일괄 처리 (Batch Processing)**:
    - `PersonalizationRepository`: 단일 요청에 포함된 7일치 플래너 데이터를 `day_plan_id` 기준으로 자동 그룹핑하여 처리.
    - **Planner Record 자동 생성**: 각 날짜별로 `USER_FINAL` 타입의 부모 레코드를 생성하여 데이터 무결성 보장.

2.  **DB 성능 최적화 (Batch Insert)**:
    - **Before**: 날짜별 반복 호출 (7일 $\times$ 3회 = 21회 호출)
    - **After**: 단계별 일괄 저장 (Records $\to$ Tasks $\to$ Histories = 3회 호출)
    - **효과**: 네트워크 오버헤드 최소화 및 처리 시간 단축 ($0.8s \to 0.47s$).

3.  **데이터 품질 향상**:
    - **Fill Rate 계산 로직 구현**: `0.0`으로 고정되던 가동률을 `(총 배치 시간 / 하루 가용 시간)` 공식으로 실제 계산하여 저장하도록 개선.
    - **테스트 데이터 확장**: `personalization_ingest_week_sample.json`을 일주일치(19개 작업)로 확장하고, 사용자 제외(`EXCLUDED by USER`) 케이스 등 다양한 시나리오 추가.

### Node 3 (Task Chain Generator) 고도화 - 중요도 정규화

**목적**: LLM이 작업 간의 상대적 중요도를 명확히 파악할 수 있도록, 입력되는 중요도 점수(`importanceScore`)를 0~1 범위로 정규화(Min-Max Normalization)하여 제공함. 이를 통해 입력 스케일에 구애받지 않는 강건한 의사결정을 지원함.

#### 주요 변경 사항

1. **[app/llm/prompts/node3_prompt.py](app/llm/prompts/node3_prompt.py)**
   - **Min-Max 정규화 로직 추가**: 입력된 모든 Task의 중요도 점수를 계산하여 `(score - min) / (max - min)` 공식으로 0.0~1.0 사이 값으로 변환.
   - **Prompt 개선**: `Tasks` 설명에 중요도 점수가 정규화된 상대값임을 명시하여 LLM의 혼동 방지.

2. **[tests/test_node3_normalization.py](tests/test_node3_normalization.py)** (신규)
   - **단위 테스트**: 다양한 케이스(일반 분포, 단일 값, 동일 값, 빈 리스트)에 대해 정규화 로직이 올바르게 동작하는지 검증.

3. **[README.md](README.md)**
   - **테스트 가이드 추가**: Node 3 정규화 로직 테스트 실행 명령어(`python -m unittest tests/test_node3_normalization.py`) 추가.

---

## 2026-01-26

### 에러 코드 중앙화 및 선별적 재시작 로직

**목적**: 에러 코드를 중앙에서 관리하여 유지보수성을 높이고, 랭그래프 노드에 지능형 재시작 로직(선별적 재시작)을 도입하여 시스템 안정성을 강화함.

#### 주요 변경 사항

1. **[app/models/planner/errors.py](app/models/planner/errors.py)** (신규)
   - **에러 코드 정의**: `PlannerErrorCode` Enum을 통해 에러 코드를 상수로 관리.
   - **헬퍼 함수**: `map_exception_to_error_code` (예외 매핑), `is_retryable_error` (재시작 가능 여부 판단) 구현.

2. **[app/api/v1/gemini_test_planners.py](app/api/v1/gemini_test_planners.py)**
   - **리팩토링**: 하드코딩된 에러 문자열을 `PlannerErrorCode` 상수로 교체하여 일관성 확보.

3. **[app/services/planner/nodes/node1_structure.py](app/services/planner/nodes/node1_structure.py)**
   - **전면 재시도 (Comprehensive Retry)**: **서버 에러(5xx)** 뿐만 아니라 **LLM 할루시네이션, JSON 구조 오류(400)** 등 모든 데이터 무결성 실패에 대해 적극적으로 재시도하도록 로직을 강화함.
   - **무결성 검증**: TaskId, Category, CognitiveLoad 값이 유효하지 않은 경우 즉시 `ValueError`를 발생시켜 재시도 트리거.

4. **[app/services/planner/nodes/node3_chain_generator.py](app/services/planner/nodes/node3_chain_generator.py)**
   - **전면 재시도**: Node 1과 동일하게 서버 에러 및 데이터 무결성 오류(할루시네이션, 빈 후보 등) 발생 시 전면 재시도 적용.

5. **지수 백오프 (Exponential Backoff)**
   - **부하 분산**: 재시도 시 고정 시간이 아닌 점진적으로 대기 시간을 늘려 (`1초` → `2초` → `4초` → `8초`) 서버 과부하 상태에서 회복할 시간을 확보.
   - **Node 1 & Node 3 적용**: `asyncio.sleep`을 활용하여 비동기 적으로 대기하도록 구현.


### Node 4 (Chain Judgement) 구현

**목적**: LLM이 생성한 여러 체인 후보 중 **수학적 최적해**를 선택하는 Node 4를 구현함. 현실성(Overflow)과 논리적 완결성(Closure)을 보장하는 정교한 점수 산정 로직 적용.

#### 주요 변경 사항

1. **[app/services/planner/nodes/node4_chain_judgement.py](app/services/planner/nodes/node4_chain_judgement.py)** (신규)
   - **Closure 강제**: 그룹 작업의 순서(`orderInGroup`)를 엄격히 검사하여, 선행 작업이 없는 후행 작업을 체인에서 자동 제거.
   - **Overflow Penalty**: 시간대별 가용량의 120%까지는 "안전 구간(Safe Buffer)"으로 보아 미세 페널티 부여, 그 이상은 기하급수적($O^2$) 페널티를 부여하여 현실성 없는 계획 차단.
   - **Comprehensive Scoring**: 단순 포함/제외 점수뿐만 아니라 피로도 위험(`Fatigue Risk`), 집중 시간대 정렬(`Focus Align`) 보너스 등을 종합 반영.

2. **[tests/test_node4.py](tests/test_node4.py)** (신규)
   - **단위 테스트**: Closure 강제 로직, Overflow 페널티 함수, 최종 체인 선택 로직에 대한 검증 코드 작성 (3/3 pass).

3. **[tests/test_integration_node1_to_node4.py](tests/test_integration_node1_to_node4.py)** (신규)
   - **통합 테스트**: Node 1(구조) -> Node 2(중요도) -> Node 3(체인생성) -> Node 4(체인평가)로 이어지는 전체 파이프라인 검증 및 최적 체인 선택 확인.

### LLM 파이프라인 관측성 (Observability) 강화 - Logfire 도입

**목적**: 복잡한 LangGraph 파이프라인의 실행 흐름과 데이터 변화(State Transition)를 시각적으로 추적하기 위해 **[Logfire](https://logfire.pydantic.dev)**를 도입함.

#### 주요 변경 사항

1. **[app/services/planner/nodes/node1_structure.py](app/services/planner/nodes/node1_structure.py)**
   - **Instrumentation**: `node1_structure_analysis` 함수에 `@logfire.instrument` 데코레이터를 적용하여 입력(State)과 출력(Updated State)을 자동 추적.

2. **[tests/test_node1.py](tests/test_node1.py)**
   - **Logfire 적용**: 테스트 실행 시 Logfire를 초기화하고, `with logfire.span(...)`을 통해 테스트 실행 구간을 명시적으로 기록.
   - **환경 개선**: `sys.path.append` 로직을 최상단으로 이동하여 모듈 import 오류 해결.

3. **Node 2 (Importance) 관측성 적용**
   - **[app/services/planner/nodes/node2_importance.py](app/services/planner/nodes/node2_importance.py)**: `node2_importance` 함수에 Instrumentation 적용.

4. **Node 3 (Chain Generator) 관측성 적용**
   - **[app/services/planner/nodes/node3_chain_generator.py](app/services/planner/nodes/node3_chain_generator.py)**: `node3_chain_generator` 함수에 Instrumentation 적용.

5. **Node 4 (Chain Judgement) 관측성 적용**
   - **[app/services/planner/nodes/node4_chain_judgement.py](app/services/planner/nodes/node4_chain_judgement.py)**: `node4_chain_judgement` 함수에 Instrumentation 적용.
   - **테스트 업데이트**: `tests/test_node4.py` 및 `tests/test_integration_node1_to_node4.py`에 Logfire 관측 영역 추가.

6. **LLM 입출력 데이터 명시적 로깅 (Input/Result Logging)**
   - **Node 1, 2, 3, 4 적용**: `logfire.info("... Input Data", input=...)` 및 `logfire.info("... Result", result=...)`를 추가하여 대시보드에서 LLM 입력 프롬프트와 최종 상태값을 즉시 확인할 수 있도록 개선.

7. **테스트 안정성 및 가용성 검증 강화**
   - **[tests/test_node3.py](tests/test_node3.py)**: `NIGHT` 시간대(21:00~23:00) 가용 세션을 추가하여 야간 작업 배분 로직 검증.
   - **통합 테스트 리팩토링**: `tests/test_integration_node1_to_node3.py` 및 `tests/test_integration_node1_to_node4.py`에서 하드코딩된 대역 데이터를 제거하고, `calculate_free_sessions` 유틸리티를 사용하여 `test_request.json` 설정에 따라 동적으로 가용 시간을 계산하도록 개선.
   - **Logfire 관측 영역 확장**: 모든 단위 테스트 및 통합 테스트에 Logfire Span을 추가하여 테스트 실행 과정의 가시성 확보.

### Node 5 Logic Refinement (V1 정책 명확화)

**목적**: 물리적 시간 배정 로직(Node 5)을 V1 요구사항에 맞춰 단순화하고, 결과값의 품질을 개선함.

#### 주요 변경 사항

1. **단일 자식 평탄화 (Single-Child Flattening)**:
    - 분할 시도가 있었으나 결과적으로 자식 작업이 하나만 생성된 경우(예: Tail Drop), 불필요한 Parent-Child 구조를 제거하고 일반 FLEX 작업으로 자동 변환.
2. **분할 로직 최적화 (Optimization)**:
    - **강제 분할(MaxChunk) 제거**: 작업이 세션 내에 물리적으로 들어간다면 시간이 길어도 분할하지 않음 (V2로 연기).
    - **배치 조건**: 오직 세션 공간이 부족하거나 중간에 FIXED 일정이 있는 경우에만 분할 수행.
3. **휴식 정책 변경**:
    - **Intra-task Break 연기**: 작업 도중 쉬는 시간은 V2로 연기하고, 작업 완료 후 휴식(Gap)만 적용하여 타임라인 파편화 방지.
4. **통합 테스트 출력 개선**:
    - `test_integration_node1_to_node5.py` 결과 테이블에서 분할된 작업(SUB)을 개별 행으로 시각화하여, FIXED 작업이 그 사이에 끼어있는 시간 순서를 정확히 표현.

---

## 2026-01-25

### Node 3 (Task Chain Generator) 및 시스템 안정화

**목적**: 후보 체인을 생성하는 Node 3를 구현하고, 지능형 Fallback 로직과 무결성 검증을 도입하여 안정성을 확보함. 또한 FIXED 작업 제약을 완화하여 사용자 편의성을 개선함.

#### 주요 변경 사항

1. **[app/services/planner/nodes/node3_chain_generator.py](app/services/planner/nodes/node3_chain_generator.py)** (신규)
   - **LLM 기반 배치**: Gemini 2.5 Flash Lite를 활용해 4~6개의 배치 시나리오 생성 로직 구현.
   - **지능형 Fallback**: API 실패 시 "중요도 순 정렬 + 시간대별 분산(Safety Cap 120%)" 방식의 안전장치 적용.
   - **무결성 검증**: LLM이 생성한 `taskId`가 원본에 없는 경우(Hallucination) 자동 필터링.

2. **[app/llm/prompts/node3_prompt.py](app/llm/prompts/node3_prompt.py)** (신규)
   - **Prompt Engineering**: 시간대별 할당 규칙, JSON 스키마, COT(Chain-of-Thought) 유도를 포함한 시스템 프롬프트 정의.

3. **[app/services/planner/utils/session_utils.py](app/services/planner/utils/session_utils.py)**
   - **기능 추가**: `calculate_capacity` 함수를 추가하여 시간대별(MORNING, AFTERNOON 등) 분 단위 가용량을 계산.

4. **[app/models/planner/internal.py](app/models/planner/internal.py)**
   - **모델 수정**: `ChainCandidate` 모델 적용 및 `TaskFeature`에 `combined_embedding_text` 필드 추가.
   - **타입 강화**: `SchedulerItem` 등의 명시적 타입 힌트 적용으로 안정성 확보.

5. **[app/models/planner_test.py](app/models/planner_test.py) & [app/services/gemini_test_planner_service.py](app/services/gemini_test_planner_service.py)**
   - **정책 변경**: FIXED 작업의 시간 제약(startArrange~dayEndTime) 검증 로직 제거 (사용자 입력 존중).

6. **[app/services/planner/nodes/node1_structure.py](app/services/planner/nodes/node1_structure.py)**
   - **리팩토링**: Pydantic `default_factory` 활용으로 불필요한 초기화 코드 제거 및 가독성 개선.
   - **타입 힌트**: 명시적 타입 힌트 추가.

7. **[tests/test_node3.py](tests/test_node3.py) & [tests/test_node3_fallback.py](tests/test_node3_fallback.py)** (신규)
   - **단위 테스트**: Node 3의 정상 동작(LLM 연동) 및 에러 상황(Fallback) 검증 코드 작성.

8. **[tests/test_integration_node1_to_node3.py](tests/test_integration_node1_to_node3.py)** (신규)
   - **통합 테스트**: Node 1 -> Node 2 -> Node 3 파이프라인 연계 및 데이터 흐름 검증.

9. **[tests/test_node1.py](tests/test_node1.py) & [tests/test_node2.py](tests/test_node2.py)**
   - **환경 개선**: 한글/영문 혼용 시 터미널 표 깨짐 방지를 위한 `get_display_width` 정렬 로직 적용.
   - **경로 수정**: `sys.path` 추가로 테스트 실행 경로 유연성 확보.

---

## 2026-01-24

### API 라우팅 구조 리팩토링 (버전화)

**목적**: API 버전 관리의 용이성과 확장성을 위해 라우팅 구조를 계층화함.

#### 주요 변경 사항

1. [app/api/v1/__init__.py](app/api/v1/__init__.py) (신규)
   - v1의 모든 기능을 통합하는 `router` 인스턴스 생성
   - `gemini_test_planners` 라우터를 포함하여 v1 API 그룹화

2. [app/main.py](app/main.py)
   - 개별 기능 라우터(`gemini_test_planners`) 직접 등록 방식 제거
   - 버전별 통합 라우터(`v1.router`)를 `/ai/v1` 접두어와 함께 등록하도록 개선
   - 향후 v2, v3 추가 시 `main.py` 수정 없이 버전별 폴더 내에서만 관리 가능하도록 구조화

3. [app/api/v1/gemini_test_planners.py](app/api/v1/gemini_test_planners.py)
   - `APIRouter` 내의 중복된 `prefix="/ai/v1"` 제거 (통합 라우터에서 관리)

#### 효과
- **유지보수성 향상**: 새로운 API 추가 시 `app/api/v1/__init__.py`만 수정하면 됨
- **확장성 확보**: v2, v3 등 새로운 버전을 독립적으로 추가하고 관리하기 쉬운 구조 구축

---

## 2026-01-23

### AI 플래너 생성 파이프라인(V2) 설계

**목적**: `POST /ai/v1/planners`를 단순 Gemini API 호출에서 LangGraph 기반의 5단계 파이프라인으로 고도화하고, 개인화 학습(IRL)을 위한 데이터베이스 구조를 설계함.

#### 생성된 문서

1. **[docs/planner_implementation_plan.md](docs/planner_implementation_plan.md)**
   - 전체 구현 계획서
   - 11단계 마일스톤 (DB 설정 -> 노드 구현 -> 백엔드 연동 -> 저장 및 테스트)
   - 주요 LangGraph 노드(전처리, 구조 분석, 중요도 산정, 체인 생성, 시간 할당) 상세 설계 포함

2. **[docs/LANGGRAPH_PLAN.md](docs/LANGGRAPH_PLAN.md)**
   - 상세 아키텍처 및 구현 가이드
   - Supabase 테이블 스키마 (`user_weights`, `planner_records`, `record_tasks`) 확정
   - 각 노드별 핵심 로직 및 Python 의사 코드(Pseudo-code) 포함

#### 설계된 Supabase 스키마 (확정)

- **user_weights**: 사용자별 개인화 가중치 (JSONB)
- **planner_records**: 플래너 생성/수정 이력 메타데이터 (AI 초안 vs 사용자 최종본 구분)
- **record_tasks**: 개별 작업별 분석 결과 및 배치 정보 상세 기록

- **record_tasks**: 개별 작업별 분석 결과 및 배치 정보 상세 기록

#### 기술적 의사결정 (Embedding Strategy)

- **이원화 전략**:
  - `POST /ai/v1/planners` (초안): 임베딩 생성 안 함 (불필요한 리소스 낭비 방지)
  - `POST /ai/v1/personalizations/ingest` (최종확정): 검색 정확도를 위해 **이 시점에 임베딩 즉시 생성**
  - **유연성**: 현재 Gemini 768차원을 사용하나, 추후 벤치마크 결과에 따라 변경 가능성을 열어둠

#### 향후 계획

1. Supabase 테이블 생성 및 환경 설정
2. LangGraph 노드 순차적 구현 (Node1 ~ Node5)
3. API 엔드포인트 연동 및 비동기 로깅 구현

### AI 플래너 파이프라인(V2) 기반 구현 (Step 1 ~ 2)

**목적**: LangGraph 기반 플래너 생성을 위한 환경 설정 및 기본 데이터 구조 구현

#### 구현 내용

1.  **환경 설정**
    - [x] [requirements.txt](requirements.txt): `langgraph`, `supabase`, `sentence-transformers` 등 필수 패키지 확인
    - [x] [app/core/config.py](app/core/config.py): Supabase 관련 설정 추가 (`supabase_url`, `supabase_key`) 및 복구

2.  **기반 구조 구현 (Base Infrastructure)**
    - [x] **디렉토리 구조**: `app/models/planner`, `app/db`, `app/services/planner/utils` 등 생성
    - [x] **[app/db/supabase_client.py](app/db/supabase_client.py)**: Supabase 클라이언트 싱글톤 패턴 구현
    - [x] **[app/models/planner/request.py](app/models/planner/request.py)**: API 요청 모델 (`ArrangementState`, `ScheduleItem` 등)
    - [x] **[app/models/planner/response.py](app/models/planner/response.py)**: API 응답 모델 (`AssignmentResult` 등)
    - [x] **[app/models/planner/internal.py](app/models/planner/internal.py)**: 내부 로직용 모델 (`TaskFeature`, `FreeSession`, `ChainCandidate`)
    - [x] **[app/models/planner/weights.py](app/models/planner/weights.py)**: 개인화 가중치 파라미터 모델 (`WeightParams`)
    - [x] **[app/services/planner/utils/time_utils.py](app/services/planner/utils/time_utils.py)**: 시간 변환 및 TimeZone 계산 유틸리티
    - [x] **[app/services/planner/utils/session_utils.py](app/services/planner/utils/session_utils.py)**: 가용 시간(FreeSession) 계산 로직

3.  **Step 3: Node 1 (Structure Analysis) 구현 및 검증 완료**
    - [x] **[app/llm/prompts/node1_prompt.py](app/llm/prompts/node1_prompt.py)**: LLM 프롬프트 설계 (Category, CogLoad, OrderInGroup 추출)
    - [x] **[app/llm/gemini_client.py](app/llm/gemini_client.py)**: `google-genai` 라이브러리 기반 Gemini 2.5 Flash Lite 연동
        - **Note**: 현재 LLM은 `gemini-2.5-flash-lite`를 사용 중이며, 추후 변경될 수 있음.
    - [x] **[app/services/planner/nodes/node1_structure.py](app/services/planner/nodes/node1_structure.py)**: 구조 분석 노드 로직
        - **Strict Grouping**: LLM의 임의 그룹 생성을 차단하고 시스템의 상위 작업(`parentScheduleId`) 기반 강제 그룹핑 적용
        - **Error Handling**: 무의미한 입력(Gibberish)을 `ERROR` 카테고리로 필터링
        - **Retry Logic**: 안정성을 위해 총 5회(초기 1회 + 재시도 4회) 시도 후 Fallback 처리하도록 설정 (추후 조정 가능)
        - **Real LLM Verification**: 실제 Gemini API 연동 테스트(`tests/test_node1.py`)를 통해 논문/취업준비 시나리오 검증 완료
    - [x] **Refactoring**: API 명세서 준수를 위해 `request.py`의 `groups` 필드 제거 및 `schedules` 내 Parent Task 조회 방식으로 변경

4.  **Step 4: Node 2 (Task Importance) 구현 및 검증 완료**
    - [x] **[app/services/planner/nodes/node2_importance.py](app/services/planner/nodes/node2_importance.py)**: 중요도(Importance) 및 피로도(Fatigue) 계산 로직
        - **Importance**: `FocusLevel` + `Urgency` + `CategoryWeight` 기반 점수 산정
        - **Fatigue**: `Duration` + `CognitiveLoad` 기반 피로도 비용 산정
        - **Filtering**: **오타 허용/Gibberish 필터링** 정책 적용 (단순 오타는 허용, "asdf" 등은 삭제)
    - [x] **[models/planner/request.py](models/planner/request.py)**: 불필요한 `HOUR_OVER_2` 옵션 제거
    - [x] **Test Infrastructure Refactoring**:
        - `tests/data/test_request.json` 생성 (공용 테스트 데이터셋)
        - `tests/test_node1.py`, `tests/test_node2.py`가 위 JSON 데이터를 공유하도록 수정
    - [x] **Integration Test**: `tests/test_integration_node1_node2.py`를 통해 Node 1 -> Node 2 파이프라인 흐름 및 필터링 검증 완료

## 2026-01-22

### API 통합 및 기능 개선

**변경 사항**: 기존 `/ai/v1/planners` (단순 에코) API를 삭제하고, Gemini 테스트 API를 `/ai/v1/planners`로 통합

#### 삭제된 파일

- `app/api/v1/planners_test.py`: 기존 단순 에코 API
- `app/services/planner_service_test.py`: 기존 단순 에코 서비스

#### 수정된 파일

1. **[app/api/v1/gemini_test_planners.py](app/api/v1/gemini_test_planners.py)**
   - prefix 변경: `/ai/v1/gemini-test` → `/ai/v1`
   - tags는 `"AI Planner (GEMINI TEST)"` 유지

2. **[app/main.py](app/main.py)**
   - `planners_test` 라우터 import 및 등록 제거
   - `gemini_test_planners` 라우터만 유지

3. **[app/models/planner_test.py](app/models/planner_test.py)**
   - 예시 데이터의 FIXED 작업 시간 수정: "아침 운동" `07:00~08:00` → "아침 스트레칭" `09:00~09:30` (startArrange 범위 내로)
   - `PlannerGenerateRequestTest`에 FIXED 작업 시간 범위 검증 추가 (`startArrange`~`dayEndTime` 범위 체크)
   - `PlannerScheduleResultTest`에 `title` 필드 추가

4. **[app/services/gemini_test_planner_service.py](app/services/gemini_test_planner_service.py)**
   - `_validate_and_fix_time_range()` 함수 추가: AI 생성 결과가 시간 범위를 벗어나면 EXCLUDED로 변경
   - 결과에 `title` 포함하도록 수정
   - 시간 순서대로 오름차순 정렬 로직 추가 (ASSIGNED는 startAt 기준, EXCLUDED는 맨 뒤로)
   - 모델 변경: `gemini-2.0-flash-exp` → `gemini-3-flash-preview`

5. **[requirements.txt](requirements.txt)**
   - 버전 명확히 지정: `google-genai>=1.60.0` → `google-genai==1.60.0`

6. **[.env.example](.env.example)**
   - `GEMINI_API_KEY` 필드 추가

7. **[README.md](README.md)**
   - 프로젝트 구조에 각 파일 역할 상세 설명 추가
   - 환경 변수 설정 섹션 간소화 (`.env.example` 참고로 안내)
   - 스테이징/프로덕션 배포 가이드는 `CLOUD_DEPLOYMENT_INFO.md`로 이동

8. **[CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md)**
   - 스테이징/프로덕션 환경 변수에 `GEMINI_API_KEY` 추가
   - Gemini API 키 발급 방법 상세 안내 추가
   - Docker 실행 명령어에 `GEMINI_API_KEY` 환경 변수 추가

#### API 명세 (변경됨)

- **엔드포인트**: `POST /ai/v1/planners` (Gemini TEST 버전)
- **모델**: `gemini-3-flash-preview`
- **Request/Response**: `PlannerGenerateRequestTest`, `PlannerGenerateResponseTest`

#### 주요 기능

1. **FIXED 작업 시간 유지**: 사용자가 설정한 고정 일정의 시간은 절대 변경하지 않음
2. **FLEX 작업 최적 배치**: AI가 유동적인 작업을 빈 시간에 배치
3. **시간 겹침 방지**: 모든 작업이 1분도 겹치지 않도록 배치
4. **FLEX 작업 40-60% EXCLUDED**: 현실적인 플래너 작성을 위해 일부 작업 제외
5. **우선순위 고려**: 긴급도(`isUrgent`)와 몰입도(`focusLevel`)를 고려한 배치
6. **몰입 시간대 활용**: 사용자의 몰입 시간대에 집중 작업 우선 배치
7. **시간 범위 검증**: 입력 및 출력 모두 `startArrange`~`dayEndTime` 범위 내로 제한
8. **결과 정렬**: 시간 순서대로 오름차순 정렬 (EXCLUDED는 맨 뒤)
9. **title 포함**: 응답에 각 작업의 제목 포함

#### 테스트 방법

1. 서버 실행: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
2. Swagger UI 접속: http://localhost:8000/docs
3. `POST /ai/v1/planners` 엔드포인트 테스트
4. 예시 Request Body로 테스트 가능 (Swagger UI에 내장)

#### 나중에 삭제할 파일 (gemini_test 접두사로 쉽게 식별 가능)

- `app/services/gemini_test_planner_service.py`
- `app/api/v1/gemini_test_planners.py`
- [app/main.py](app/main.py)에서 `gemini_test_planners` import 및 router 등록
- [.env](.env)에서 `GEMINI_API_KEY` 라인

#### 참고 사항

- Gemini API 키가 필요 (`.env` 파일에 설정)
- 최신 `google-genai` 패키지 사용 (deprecated된 `google-generativeai` 대신)

---

## 2026-01-20

### Gemini API 연동 플래너 생성 기능 최초 구현 (GEMINI TEST)

**목적**: Gemini 3 Flash Preview API를 사용한 AI 플래너 생성 기능 구현

#### 구현 내용

1. **새로운 파일 생성**
   - [x] [app/services/gemini_test_planner_service.py](app/services/gemini_test_planner_service.py): Gemini API 호출 및 플래너 생성 로직
   - [x] [app/api/v1/gemini_test_planners.py](app/api/v1/gemini_test_planners.py): Gemini 기반 플래너 API 엔드포인트

2. **수정된 파일**
   - [x] [requirements.txt](requirements.txt): `google-genai>=1.60.0` 패키지 추가
   - [x] [app/main.py](app/main.py): Gemini 라우터 등록
   - [x] [app/core/config.py](app/core/config.py): `gemini_api_key` 설정 추가
   - [x] [.env](.env): `GEMINI_API_KEY` 환경 변수 추가

### AI 플래너 생성 TEST API 개발 완료 (단순 에코 버전 - 삭제됨)

- [x] [app/models/planner_test.py](app/models/planner_test.py): Pydantic 모델 구현
- [x] ~~app/services/planner_service_test.py~~: 서비스 로직 구현 (2026-01-22 삭제됨)
- [x] ~~app/api/v1/planners_test.py~~: API 엔드포인트 구현 (2026-01-22 삭제됨)
- [x] [app/main.py](app/main.py): FastAPI 애플리케이션 설정
- [x] [app/core/config.py](app/core/config.py): 환경 변수 관리
