# 트러블슈팅 가이드 (Troubleshooting History)

MOLIP AI 서버 개발 과정에서 발생했던 이슈들과 해결 과정을 날짜별로 기록한 문서입니다. `CHANGELOG.md`와 연계하여 참조하시기 바랍니다.

---


## 2026-01-29

### 1. LangSmith 설치 오류 (Python 3.9 호환성)
- **현상**: `pip install langsmith==0.6.6` 실행 시 `No matching distribution found` 에러 발생.
- **원인**: `langsmith` 0.5.0 이상 버전은 Python 3.10 이상을 요구함. 현재 프로젝트는 Python 3.9 환경.
- **해결**: 버전을 명시하지 않음(`langsmith`)으로써 `pip`가 Python 3.9와 호환되는 마지막 버전(0.4.x)을 자동으로 찾아서 설치하도록 변경.

### 2. Refactoring 중 __init__.py NameError
- **현상**: 파일 정리 후 검증 스크립트 실행 시 `NameError: name 'router' is not defined` 발생.
- **원인**: `app/api/v1/gemini_test_planners.py` 삭제 과정에서 `__init__.py`의 `router = APIRouter()` 초기화 라인을 실수로 함께 삭제함.
- **해결**: `APIRouter` 초기화 코드 및 누락된 `import` 문을 복구하여 해결.

### 2. LangSmith 데이터 전송 실패 (macOS LibreSSL 이슈)
- **현상**: 연결 테스트 스크립트 실행 시 `NotOpenSSLWarning`이 발생하며 대시보드에 로그가 보이지 않음.
- **원인**: macOS의 기본 `LibreSSL`과 `urllib3` v2 버전 간의 호환성 문제로 HTTPS 요청이 차단됨.
- **해결**: `requirements.txt`에 `urllib3<2`를 추가하여 네트워킹 라이브러리 버전을 다운그레이드.

### 3. API 호출 시 LangSmith 로그 누락
- **현상**: `test_langsmith.py`는 성공했으나, 실제 `uvicorn` 서버 실행 후 API 호출 시에는 로그가 남지 않음.
- **원인**: `app/main.py`에서 `langsmith` 관련 라이브러리가 임포트되거나 초기화되는 시점이 `load_dotenv()`보다 빨라서 환경 변수(`LANGCHAIN_TRACING_V2`)가 적용되지 않음.
- **해결**: `app/main.py` 최상단에 `load_dotenv()`를 명시적으로 호출하여 앱 시작과 동시에 환경 변수를 로드하도록 수정.

### 4. 불규칙한 FIXED 일정으로 인한 FLEX 배정 혼선
- **현상**: 사용자가 "09:03 ~ 10:17"과 같이 분 단위로 FIXED 일정을 설정할 경우, 남은 시간에 배정되는 FLEX 작업도 "10:17 ~ 10:47" 처럼 지저분하게 생성됨.
- **해결**: **Time Granularity Alignment (10분 단위)** 적용.
  - 가용 시간의 시작("09:03")은 "09:10"으로 올림(Ceiling).
  - 가용 시간의 종료("10:17")는 "10:10"으로 내림(Floor).
  - 결과적으로 FLEX 작업은 항상 10분 단위(XX:00, XX:10...)로 배정됨.



### 1. 클라우드 환경에서 Logfire 로그 미수집
- **현상**: AWS 등 클라우드 서버에 배포 후 애플리케이션은 정상 동작하나 Logfire 대시보드에 로그가 올라오지 않음.
- **원인**: `logfire.configure(send_to_logfire='if-token-present')` 설정에 의해, 인증 토큰이 없으면 자동으로 로깅이 비활성화됨. 로컬과 달리 서버 환경변수에는 토큰이 등록되지 않았기 때문.
- **해결**: **환경 변수 추가**.
  - 배포 환경(AWS Lambda, Docker 등)의 환경 변수 설정에 `LOGFIRE_TOKEN` 키로 프로젝트의 Write Token 값을 추가.
  - 앱 재시작 후 연결 확인.

### 2. 비동기 작업 스케줄링 실수 (NameError: background_tasks)
- **현상**: API 엔드포인트에서 `background_tasks.add_task(...)` 호출 시 `name 'background_tasks' is not defined` 500 에러 발생.
- **원인**: FastAPI 엔드포인트 함수 인자에 `background_tasks: BackgroundTasks` 의존성 주입을 누락함.
- **해결**: 함수 시그니처에 `background_tasks: BackgroundTasks` 파라미터 추가.

### 3. Pydantic 모델 필드 누락 (Validation Error)
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
