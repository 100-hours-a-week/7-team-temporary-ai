# 트러블슈팅 가이드 (Troubleshooting History)

MOLIP AI 서버 개발 과정에서 발생했던 이슈들과 해결 과정을 날짜별로 기록한 문서입니다. `CHANGELOG.md`와 연계하여 참조하시기 바랍니다.

---



## 2026-02-10

### 1. LangGraph 모듈 제거 후 Import 에러
- **현상**: `langgraph` 제거 후 서버 실행 시 `ModuleNotFoundError: No module named 'langgraph'` 또는 `ImportError` 발생 가능성.
- **원인**: `app/graphs/planner_graph.py`를 참조하거나, `langgraph`에 의존하던 구버전 코드가 남아있을 경우 발생.
- **해결**:
  - `requirements.txt`에서 `langgraph` 제거 확인.
  - `app/api/v1/endpoints/planners.py`가 새로운 선형 파이프라인(Linear Pipeline)을 사용하는지 확인.
  - `app/graphs/` 디렉토리 삭제 확인.

### 2. LangSmith API Key 경고
- **현상**: 서버 로그에 `LANGCHAIN_API_KEY` 미설정 경고가 뜨거나, `LangSmith` 연결 실패 로그가 남음.
- **원인**: 코드에서 `LangSmith` 관련 로직은 제거되었으나, `.env` 파일에 환경 변수가 남아있거나 `main.py`에 주석 처리가 덜 된 부분이 있을 수 있음.
- **해결**:
  - `.env` 파일에서 `LANGCHAIN_` 관련 변수 삭제 (선택 사항, 기능 영향 없음).
  - `app/main.py`에서 `load_dotenv()` 호출 시점의 주석 및 관련 불필요한 코드 확인.

## 2026-02-09

### 1. Supabase 데이터 저장 실패 (ImportError: AssignmentStatus)
- **현상**: API 요청은 성공(200 OK)하지만, Supabase에 데이터가 저장되지 않음. 서버 로그에 `cannot import name 'AssignmentStatus' from 'app.models.personalization'` 경고 발생.
- **원인**: `app/models/personalization.py`에서 `AssignmentStatus` 정의가 제거되었으나, `app/db/repositories/planner_repository.py`에 사용하지 않는 import 문이 남아있어 백그라운드 태스크 실행 시 에러가 발생함.
- **해결**: **Unused Import Removal**.
  - `app/db/repositories/planner_repository.py`에서 불필요한 `from app.models.personalization import AssignmentStatus` 라인을 삭제하여 해결.

### 2. Parent Schedule ID 저장 누락 (DB Insert Miss)
- **현상**: 플래너 생성 결과는 정상적이나, `record_tasks` 테이블에 `parent_schedule_id`가 저장되지 않아 하위 작업의 관계가 유실됨.
- **원인**: API 요청 객체(`ArrangementState`)에는 값이 있으나, Repository의 `save_ai_draft` 메서드에서 DB Insert용 딕셔너리로 옮길 때 해당 필드 매핑이 누락됨.
- **해결**: **Field Mapping Addition**.
  - `app/db/repositories/planner_repository.py`에 `parent_schedule_id: original_task.parentScheduleId` 매핑 코드를 추가하여 해결.

### 3. RunPod 제어 통합 (Server-side Control)
- **요구사항**: 터미널 스크립트(`start.py`, `stop.py`)로만 가능한 RunPod 제어를 서버 API로 통합하고, Swagger UI에서 즉시 실행해보고 싶음.
- **해결**: **Dedicated API Endpoints Backend Integration**.
  - `start.py`, `stop.py`의 로직을 그대로 사용하되, FastAPI 엔드포인트로 래핑.
  - `RUNPOD_POD_ID` 환경 변수를 Default 값으로 주입하여, Swagger에서 "Execute" 버튼만 누르면 즉시 동작하도록 UX 개선.

## 2026-02-08

### 1. 422 Unprocessable Entity (Personalization Ingest)
- **Issue**: `/ai/v1/personalizations/ingest` 호출 시 `422 Unprocessable Entity` 에러 발생.
- **Cause**: API 명세가 변경되어 `schedules`, `scheduleHistories` 등의 복잡한 객체 대신 `userIds`와 `targetDate`만 요구함.
- **Solution**: Request Body를 `{ "userIds": [...], "targetDate": "YYYY-MM-DD" }` 형태로 수정할 것.

### 2. DB 적재 시 FK 매핑 누락 (Auto-Increment ID)
- **현상**: `planner_records` 테이블에 데이터를 INSERT 했으나, 그 ID를 알 수 없어 하위 테이블(`record_tasks`)에 `record_id`를 채울 수 없는 문제 예상.
- **원인**: PK(`id`)가 DB에서 Auto-Increment로 생성되므로, 애플리케이션 레벨에서는 INSERT 직전까지 ID를 알 수 없음.
- **해결**: **RETURNING 절 활용**.
  - `INSERT INTO ... RETURNING id` 쿼리를 사용하여, 저장과 동시에 생성된 ID를 반환받도록 가이드함.
  - 반환받은 ID를 메모리에 변수로 저장해두었다가, 이어지는 `record_tasks` INSERT 시 `record_id` 값으로 바인딩하여 무결성 유지.

## 2026-02-05

### 1. LangGraph 모듈 없음 (ModuleNotFoundError)
- **현상**: `tests/test_graph.py` 실행 시 `ModuleNotFoundError: No module named 'langgraph'` 발생.
- **원인**: `requirements.txt`에는 추가했으나, 로컬 가상환경(venv)에 패키지를 설치하지 않은 상태에서 테스트를 실행함.
- **해결**: `pip install -r requirements.txt` 명령어를 실행하여 의존성 설치 완료.

### 2. LangSmith 환경 변수 미적용
- **현상**: `.env`에 `LANGCHAIN_TRACING_V2=true`를 설정했으나 LangSmith 대시보드에 로그가 남지 않음.
- **원인**: `app/main.py` 등 진입점에서 `load_dotenv()`가 `langgraph`나 `logfire` 모듈이 임포트되기 전에 호출되어야 환경 변수가 라이브러리 초기화 시점에 적용됨.
- **해결**: `app/main.py` 최상단(임포트 구문 전)에 `load_dotenv()` 호출 위치를 확인하고, 서버 재시작 시 정상 적용됨을 확인.

## 2026-02-03

### 1. Pydantic Settings Parsing Error (CORS_ORIGINS)
- **현상**: 서버 실행 시 `pydantic_settings.sources.SettingsError: error parsing value for field "cors_origins" from source "EnvSettingsSource"` 에러 발생하며 구동 실패.
- **원인**: `.env` 파일에 `CORS_ORIGINS=url1,url2` 형태로 문자열을 입력했으나, Pydantic의 `List[str]` 타입 필드는 기본적으로 JSON 형식의 리스트 문자열(`["url1", "url2"]`)을 기대하기 때문에 파싱 단계에서 실패함.
- **해결**: **Type Hint Relaxation**.
  - `app/core/config.py`의 `cors_origins` 타입을 `Union[str, List[str]]`로 변경하여, raw string 입력도 허용한 후 Validator(`assemble_cors_origins`)에서 리스트로 변환하도록 처리 흐름 개선.

## 2026-02-02

### 1. 테스트와 코드의 파라미터 불일치 (DURATION_PARAMS)
- **현상**: `tests/test_duration_constraints.py` 테스트 실행 중 `MINUTE_UNDER_30`의 최대값(`max`)이 기대값(40분)과 실제값(30분)이 달라 `AssertionError` 발생.
- **원인**: `CHANGELOG.md` (2026-02-01)에 기록된 스펙 변경 사항(`30~40분`으로 상향)이 테스트 코드에는 반영되었으나, 실제 구현 코드(`node2_importance.py`)에는 누락되어 있었음.
- **해결**: **코드 동기화**.
  - `app/services/planner/nodes/node2_importance.py`의 `DURATION_PARAMS["MINUTE_UNDER_30"]["max"]` 값을 `30`에서 **`40`**으로 수정하여 테스트와 일치시킴.

## 2026-02-01

### 1. 30분 미만 작업의 프론트엔드 텍스쳐 깨짐
- **현상**: 플래너 결과화면(타임라인)에서 10분, 20분짜리 짧은 작업이 렌더링될 때 그래픽 텍스쳐가 깨지거나 UI가 어긋나는 현상 발생.
- **원인**: 프론트엔드 컴포넌트가 최소 30분 높이의 블록을 기준으로 디자인되어 있어, 그보다 작은 작업이 들어올 경우 렌더링 로직이 꼬임.
- **해결**: **Backend Constraints Enforcement**.
  - `MINUTE_UNDER_30` 카테고리의 정의를 **30~40분**으로 변경하여 원천적으로 30분 미만 작업 생성을 차단.
  - 작업 분할(Splitting) 시에도 남은 조각이 30분 미만이 될 것 같으면 분할하지 않고 다음 세션으로 넘기도록 `Node 5` 로직 수정.


## 2026-01-30

### 1. 플래너 입력 데이터 디버깅 (Initial State)
- **현상**: 복잡한 파이프라인(Node 1~5)을 거치기 전, 클라이언트가 보낸 원본 요청 데이터(JSON)가 `PlannerGraphState`로 어떻게 변환되었는지 확인하기 어려움.
- **해결**: `app/api/v1/endpoints/planners.py`의 진입점에 `logfire.info("Initial State", state=state)`를 추가하여, Logfire 대시보드에서 처리 전 원본 상태를 즉시 조회할 수 있도록 개선.


### 2. 날짜 기반 검색의 한계 (created_at only)
- **현상**: DB에 `created_at`(Timestamp) 컬럼만 존재하여, "특정 날짜의 계획"을 조회하려면 시분초 범위를 계산해야 하는 번거로움이 있음 (`WHERE created_at >= '...' AND created_at < '...'`).
- **해결**: **Date 컬럼 추가 및 Default 설정**.
  - 모든 주요 테이블(`planner_records`, `record_tasks` 등)에 `plan_date` 또는 `created_date` (DATE 타입) 컬럼을 추가.
  - `DEFAULT CURRENT_DATE`를 설정하여, 백엔드 코드 수정 없이도 데이터 삽입 시 자동으로 날짜가 채워지도록 스키마 개선.
  - 이제 `WHERE plan_date = '2024-01-30'`과 같은 직관적인 쿼리 가능.

### 3. Parent Task 누락 시 LLM의 환각(Hallucination)
- **현상**: `parentScheduleId`가 없는 작업임에도 불구하고, LLM(Node 1)이 임의로 `orderInGroup`을 `1`, `2` 등으로 할당하는 현상 발생.
- **원인**: 프롬프트에 `ParentID` 정보가 명확히 전달되지 않아(누락됨), LLM이 문맥을 오해하거나 일반적인 패턴을 적용해버림.
- **해결**: **Dual Safety Mechanism** 적용.
  - **Prompt Level**: 입력 데이터 포맷팅 시 `ParentID: null`을 명시하고, 시스템 프롬프트에 "ParentID가 없으면 Order도 null이어야 한다"는 강력한 지침 추가.
  - **Code Level**: `node1_structure.py`에서 LLM의 응답과 무관하게, 원본 데이터에 `parentScheduleId`가 없으면 `orderInGroup` 값을 강제로 `None`으로 덮어쓰는 안전 장치 구현.

### 4. 무의미한 텍스트(Chat-like)의 잘못된 분류
- **현상**: "안녕", "아니", "그게 맞아요?" 등 단순 대화형 텍스트가 `ERROR`가 아닌 `기타(Others)` 카테고리로 분류되어 실제 일정에 포함되는 문제.
- **원인**: `기타` 카테고리가 "나머지 전부"를 포괄하도록 느슨하게 정의되어 있어, 작업이 아닌 텍스트도 흡수함. 반면 `ERROR`는 "무의미어(Gibberish)"로만 좁게 정의됨.
- **해결**: **비작업(Non-Task) 필터링 강화**.
  - `기타`: **실행 가능한 구체적 행동(Actionable Task)**이 있는 경우로만 범위를 축소 (예: "은행 가기").
  - `ERROR`: 무의미어뿐만 아니라 인사말, 추임새, 맥락 없는 질문, 모호한 텍스트 등을 포함하도록 정의 확장 및 구체적 예시 추가.

### 5. Monitoring Stack Migration (LangSmith → Langfuse)
- **결정 배경 (Decision)**:
    - **LangSmith의 제약**: Python 3.9 환경에서 최신 버전 호환성 문제 및 다른 로깅 툴(Logfire)과의 역할 중복.
    - **Langfuse 도입 목적**: 오픈소스 기반으로 로컬 LLM 확장성이 좋고, Docker Self-hosting이 용이하여 장기적인 비용/관리 효율성 증대.
- **마이그레이션 중 발생한 이슈 및 해결**:
    1. **Python 3.9 호환성**: 최신 SDK(3.12.1) 설치 불가 → `3.7.0`으로 버전 고정 및 Import 경로(`langfuse.decorators` → `langfuse`) 수정.
    2. **테스트 인증 오류**: `unittest` 실행 시 `.env` 미로딩 → 테스트 코드 상단에 `load_dotenv()` 명시.
    3. **로그 누락 (Short-lived Process)**: 비동기 전송 전 프로세스 종료 → `gemini_client`에 `langfuse.get_client().flush()` 강제 전송 로직 추가.

### 6. 대표 DayPlanId 혼선 (어제의 EXCLUDED 태스크 문제)
- **현상**: 플래너 생성 결과(`planner_records`)에 저장된 `day_plan_id`가 오늘 날짜가 아닌 과거(어제) 날짜의 ID로 기록되는 현상.
- **원인**: 요청 데이터에 "어제의 미완료 태스크(EXCLUDED)"와 "오늘의 신규 태스크(NOT_ASSIGNED)"가 섞여 있을 때, `planner_repository.py`가 리스트의 맨 첫 번째 태스크의 `dayPlanId`를 무조건 대표값으로 가져오기 때문. (정렬 순서상 과거 태스크가 먼저 오면 과거 ID가 저장됨)
- **해결**: `save_ai_draft` 함수에서 `state.request.schedules` 리스트 내의 모든 태스크 중 **가장 큰(Max) dayPlanId**를 찾아서 저장하도록 수정.
  - `dayPlanId`는 `BIGINT`로서 시간이 지날수록 커지므로, 가장 큰 값이 항상 "오늘(최신)"의 ID임을 보장함.

## 2026-01-29

### 1. LangSmith 설치 오류 (Python 3.9 호환성)
- **현상**: `pip install langsmith==0.6.6` 실행 시 `No matching distribution found` 에러 발생.
- **원인**: `langsmith` 0.5.0 이상 버전은 Python 3.10 이상을 요구함. 현재 프로젝트는 Python 3.9 환경.
- **해결**: 버전을 명시하지 않음(`langsmith`)으로써 `pip`가 Python 3.9와 호환되는 마지막 버전(0.4.x)을 자동으로 찾아서 설치하도록 변경.

### 2. Refactoring 중 __init__.py NameError
- **현상**: 파일 정리 후 검증 스크립트 실행 시 `NameError: name 'router' is not defined` 발생.
- **원인**: `app/api/v1/gemini_test_planners.py` 삭제 과정에서 `__init__.py`의 `router = APIRouter()` 초기화 라인을 실수로 함께 삭제함.
- **해결**: `APIRouter` 초기화 코드 및 누락된 `import` 문을 복구하여 해결.

### 3. LangSmith 데이터 전송 실패 (macOS LibreSSL 이슈)
- **현상**: 연결 테스트 스크립트 실행 시 `NotOpenSSLWarning`이 발생하며 대시보드에 로그가 보이지 않음.
- **원인**: macOS의 기본 `LibreSSL`과 `urllib3` v2 버전 간의 호환성 문제로 HTTPS 요청이 차단됨.
- **해결**: `requirements.txt`에 `urllib3<2`를 추가하여 네트워킹 라이브러리 버전을 다운그레이드.

### 4. API 호출 시 LangSmith 로그 누락
- **현상**: `test_langsmith.py`는 성공했으나, 실제 `uvicorn` 서버 실행 후 API 호출 시에는 로그가 남지 않음.
- **원인**: `app/main.py`에서 `langsmith` 관련 라이브러리가 임포트되거나 초기화되는 시점이 `load_dotenv()`보다 빨라서 환경 변수(`LANGCHAIN_TRACING_V2`)가 적용되지 않음.
- **해결**: `app/main.py` 최상단에 `load_dotenv()`를 명시적으로 호출하여 앱 시작과 동시에 환경 변수를 로드하도록 수정.

### 5. 불규칙한 FIXED 일정으로 인한 FLEX 배정 혼선
- **현상**: 사용자가 "09:03 ~ 10:17"과 같이 분 단위로 FIXED 일정을 설정할 경우, 남은 시간에 배정되는 FLEX 작업도 "10:17 ~ 10:47" 처럼 지저분하게 생성됨.
- **해결**: **Time Granularity Alignment (10분 단위)** 적용.
  - 가용 시간의 시작("09:03")은 "09:10"으로 올림(Ceiling).
  - 가용 시간의 종료("10:17")는 "10:10"으로 내림(Floor).
  - 결과적으로 FLEX 작업은 항상 10분 단위(XX:00, XX:10...)로 배정됨.

### 6. 부모 작업(Parent Task) 중복 노출 및 배정
- **현상**: `parentScheduleId`를 통해 참조되는 상위(Container) 작업이 플래너 결과 목록에 포함되어 실제 일정으로 배정됨.
- **원인**: API 엔드포인트 및 초기 상태(State) 생성 시, 하위 작업들이 참조하는 부모 ID를 수집하여 필터링하는 로직이 누락됨.
- **해결**: `app/services/planner/utils/task_utils.py`에 `filter_parent_tasks` 유틸리티를 구현. 다른 작업의 `parentScheduleId`로 사용된 ID를 가진 작업은 분석 및 배정 대상에서 제외하도록 수정.
  - 결과적으로 배정되지 않은 상태로 Node 5까지 도달하여 `EXCLUDED` 상태로 반환됨.

### 7. 새벽 시간대(Next Day) 입력 시 플래너 범위 혼선
- **현상**: 사용자가 `dayEndTime`을 "02:00" 등 새벽으로 설정할 경우, 플래너가 다음 날 새벽까지 무리하게 일정을 채우려 함. (현재 스펙상 당일 배정이 원칙)
- **원인**: `calculate_free_sessions`에서 종료 시간이 시작 시간보다 빠르면 단순히 24시간을 더해 처리했기 때문.
- **해결**: `session_utils.py`에서 `end_min` 계산 후 `min(end_min, 1440)`을 적용하여, 입력값에 상관없이 최대 24:00(자정)까지만 세션을 생성하도록 제한함. 새벽 시간대 지원은 차후 고도화 과제로 관리.

### 8. 클라우드 환경에서 Logfire 로그 미수집
- **현상**: AWS 등 클라우드 서버에 배포 후 애플리케이션은 정상 동작하나 Logfire 대시보드에 로그가 올라오지 않음.
- **원인**: `logfire.configure(send_to_logfire='if-token-present')` 설정에 의해, 인증 토큰이 없으면 자동으로 로깅이 비활성화됨. 로컬과 달리 서버 환경변수에는 토큰이 등록되지 않았기 때문.
- **해결**: **환경 변수 추가**.
  - 배포 환경(AWS Lambda, Docker 등)의 환경 변수 설정에 `LOGFIRE_TOKEN` 키로 프로젝트의 Write Token 값을 추가.
  - 앱 재시작 후 연결 확인.

### 9. 비동기 작업 스케줄링 실수 (NameError: background_tasks)
- **현상**: API 엔드포인트에서 `background_tasks.add_task(...)` 호출 시 `name 'background_tasks' is not defined` 500 에러 발생.
- **원인**: FastAPI 엔드포인트 함수 인자에 `background_tasks: BackgroundTasks` 의존성 주입을 누락함.
- **해결**: 함수 시그니처에 `background_tasks: BackgroundTasks` 파라미터 추가.

### 10. Pydantic 모델 필드 누락 (Validation Error)
- **현상**: DB 저장 로직 테스트 중 `pydantic_core._pydantic_core.ValidationError: Field required [type=missing]` 에러 발생.
- **원인**: `PlannerGraphState`나 `AssignmentResult`와 같은 Pydantic 모델을 수동으로 생성할 때, 필수 필드(`type`, `userId`, `dayPlanId` 등)를 빠뜨려서 발생.
- **해결**: 모델 정의(`app/models/...`)를 확인하여 필수 필드(`...` 또는 기본값이 없는 필드)를 모두 채워서 인스턴스 생성.

---

## 2026-01-28

### 1. 테스트 실행 시 과금 및 데이터 오염 문제
- **현상**: 로컬에서 개발 편의를 위해 `$ pytest`를 실행하면, 실제 Supabase DB에 더미 데이터가 쌓이거나 Gemini API 호출로 인한 비용이 발생하는 문제.
- **원인**: 테스트 코드(`tests/`)가 실제 DB 연결 및 LLM 호출을 포함하고 있었음.
- **해결**:
  - **테스트 폴더 이원화**: 
    - `tests/`: CI/CD 및 배포 직후 실행할 안전한 테스트 (Mock, Ping 등 비파괴적 검증).
    - `tests_local/`: 로컬 개발 전용 테스트 (Real DB Write, Real LLM Call).
  - **Mock 테스트 도입**: `tests/test_logic_mock.py`를 신설하여 LLM 비용 없이 파이프라인 로직 전체를 검증.

### 2. 파이프라인 디버깅의 어려움
- **현상**: Node 1~5로 이어지는 복잡한 LangGraph 파이프라인 실행 중 어디서 데이터가 잘못되었는지 추적하기 어려움.
- **원인**: 각 노드 내부의 입출력 데이터가 로그에 명확히 남지 않음.
- **해결**: **Logfire Manual Instrumentation** 적용.
  - 각 노드 진입/종료 시점에 `logfire.info("... Input", input=...)` 및 Result 로깅을 추가하여 데이터 흐름 시각화.

---

## 2026-01-27

### 1. Ingest API의 높은 네트워크 대기 시간 (Latency)
- **현상**: 일주일치 개인화 데이터(약 20개 작업)를 저장할 때 API 응답이 1초 이상 소요됨.
- **원인**: Repository 계층에서 loop를 돌며 `INSERT` 쿼리를 20번 이상 개별 호출 (`N+1` 문제와 유사).
- **해결**: **Batch Insert** 구현.
  - `planner_records`, `record_tasks` 등을 한 번의 트랜잭션 또는 리스트 형태로 묶어서 Bulk Insert 처리 (응답 속도 50% 이상 단축).

### 2. Swagger UI 라우터 중복 노출
- **현상**: `/ai/v1/planners` 등의 엔드포인트가 Swagger 문서상에서 두 개의 카테고리로 쪼개져서 보임.
- **원인**: `APIRouter`를 `include_router` 할 때와 라우터 정의 시 `tags` 속성을 중복으로 지정함.
- **해결**: `app/api/v1/gemini_test_planners.py` 내부의 `tags` 정의를 제거하거나 상위 라우터 통합 시점으로 일원화.

### 3. 중요도 점수의 스케일 혼동
- **현상**: LLM(Node 3)이 중요도(1~5점)를 절대적인 우선순위로 해석하지 못하거나, 입력된 점수 분포에 따라 편향된 결정을 내림.
- **원인**: 상대적인 중요도 차이가 데이터 스케일에 묻히는 문제.
- **해결**: **Min-Max Normalization** 적용.
  - 입력된 작업들의 중요도 점수를 `0.0` ~ `1.0` 사이 값으로 정규화하여 모델에 제공, 상대적 우위를 명확히 함.

---

## 2026-01-26

### 1. LLM의 불안정한 출력 (Hallucination)
- **현상**: Node 1(구조분석)이나 Node 3(체인생성)에서 가끔 JSON 형식이 깨지거나, 원본에 없는 `taskId`를 지어내는 현상 발생.
- **원인**: 프롬프트 인젝션 또는 모델의 일시적 성능 저하.
- **해결**:
  - **Strict Validation**: 존재하지 않는 `taskId`가 포함되면 즉시 Error 처리.
  - **Comprehensive Retry**: 단순 서버 에러(5xx) 뿐만 아니라 논리적 오류(Validation Error) 발생 시에도 최대 5회까지 재시도.

### 2. 잦은 재시도로 인한 서버 부하
- **현상**: 재시도 로직이 너무 빠르게 반복되어 모델 API Rate Limit에 걸리거나 실패가 반복됨.
- **해결**: **Exponential Backoff** (지수 백오프) 적용.
  - 재시도 대기 시간을 1초 → 2초 → 4초 → 8초로 점진적으로 늘려 시스템 안정성 확보.

### 3. 물리적으로 불가능한 일정 생성
- **현상**: 가용한 시간은 60분인데 90분짜리 작업을 배치하려는 시도.
- **해결**: Node 4(Chain Judgement)에 **Overflow Penalty** 도입.
  - 배정된 시간이 가용 시간의 120%를 초과하면 기하급수적인 페널티를 부여하여 해당 체인이 선택되지 않도록 차단.

---

## 2026-01-25

### 1. 터미널 한글 출력 깨짐
- **현상**: `pytest` 실행 결과나 로컬 로그에서 한글이 포함된 테이블의 줄이 맞지 않아 가독성이 떨어짐.
- **원인**: 한글(2byte/Wide Char)과 영문(1byte)의 터미널 표시 너비 차이를 `ljust`/`rjust`가 제대로 계산하지 못함.
- **해결**: `wcwidth` 라이브러리(또는 유사 로직)를 활용한 `get_display_width` 유틸리티 함수 구현.

### 2. API 장애 시 서비스 전체 중단 우려
- **현상**: Gemini API가 완전히 먹통일 경우 플래너 생성 자체가 안 됨.
- **해결**: **Fallback Strategy** 마련.
  - Node 3 실패 시, 복잡한 추론 대신 "중요도 점수가 높은 순서대로 빈 시간에 채워넣는" 단순 알고리즘(Deterministic)으로 결과를 반환하도록 안전장치 구현.

---

## 2026-01-24

### 1. API 버전 관리의 어려움
- **현상**: `main.py`에 모든 엔드포인트가 평면적으로 등록되어 있어, 추후 V2/V3 확장이 어려움.
- **해결**: **Router Hierarchy** 재설계.
  - `app/api/v1/__init__.py`를 생성하여 V1 관련 모든 라우터를 묶고, `main.py`에서는 `v1.router` 하나만 등록하도록 구조 변경.

### 2. FIXED 작업 시간 데이터 오류
- **현상**: 사용자가 설정한 고정 일정(FIXED)이 하루 시작 시간(`startArrange`)보다 이른 시간에 배치되어 로직 에러 발생.
- **원인**: 테스트 데이터 생성 시 시간 범위를 꼼꼼히 검증하지 않음.
- **해결**: 테스트 데이터(`test_request.json`) 수정 및 Pydantic 모델 Validator에서 시간 범위(`startArrange` ~ `dayEndTime`) 검증 강화.

---

## 2026-01-23 (LangGraph 설계 및 구현)

### 1. LLM의 임의 그룹핑 문제 (LangGraph Node 1)
- **현상**: LLM이 사용자가 설정하지 않은 그룹을 만들거나, 기존 그룹 구조를 무시하고 작업을 섞어버림.
- **해결**: **Strict Grouping (Parent Force)**.
  - 시스템에 저장된 상위 작업 ID(`parentScheduleId`)를 기준으로 그룹 정보를 강제 할당하도록 후처리 로직 강화.

### 2. Gibberish(무의미한 텍스트) 입력
- **현상**: "asdf", "ㅁㄴㅇㄹ" 같은 무의미한 작업명이 들어오면 LLM이 혼란을 겪음.
- **해결**: Node 1/2 단계에서 `Category=ERROR` 또는 `Meaningless` 분류를 추가하여 필터링.

### 3. 임베딩 비용 효율화
- **현상**: 플래너를 생성할 때마다 모든 작업에 대해 임베딩(Vector)을 생성하려니 속도가 느리고 비용이 낭비됨.
- **해결**: **Lazy Embedding Strategy**.
  - 플래너 '생성(Draft)' 단계에서는 임베딩을 하지 않고, 사용자가 결과를 확정하여 '저장(Ingest)'하는 시점에만 임베딩을 생성하도록 변경.

---

## 2026-01-20 (초기 설정)

### 1. 환경 변수 누락
- **현상**: 서버 실행 시 `GEMINI_API_KEY` Not Found 에러 발생.
- **해결**: `.env.example` 파일을 작성하여 필수 환경 변수 목록을 명시하고, `config.py`에서 로드 시 유효성 검사 수행.
