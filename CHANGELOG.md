# 개발 진행 상황

날짜별 개발 진행 상황을 기록합니다.

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
