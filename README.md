# MOLIP AI Server

MOLIP 프로젝트의 AI 기능 서버입니다.

## 작성자 : ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white) [swoo64](https://github.com/swoo64)

---

## 로컬 실행 방법

### 1. 가상환경 설정

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 필요한 값을 설정합니다.

```bash
cp .env.example .env
# .env 파일을 열어 GEMINI_API_KEY 등 필요한 값 설정
```

> **Note**: 환경 변수 상세 설명은 [.env.example](.env.example) 파일을 참고하세요.

### 5. 접속

- Swagger UI: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## LLM 설정 (Current Configuration)

현재 구현 단계(Step 3)에서는 다음과 같은 설정을 사용합니다. (추후 벤치마크 결과에 따라 모델이나 재시도 정책은 변경될 수 있습니다.)

- **Model**: `gemini-2.5-flash-lite` (Google GenAI)
- **Retry Policy**: Node 1(구조 분석)에서 LLM 응답 실패 시 **총 5회(1회 시도 + 4회 재시도)** 수행 후 Fallback 로직으로 전환합니다.

---




---

## 프로젝트 구조

```
MOLIP-AI/
├── app/
│   ├── __init__.py
│   ├── main.py                      # [Core] FastAPI 앱 진입점, 미들웨어(CORS) 설정, API 라우터(v1) 통합 등록
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py          # [API] V1 라우터 통합 (gemini_test_planners 등 포함)
│   │       └── gemini_test_planners.py  # [API] V1 Gemini 플래너 생성 엔드포인트 (POST /ai/v1/planners). 에러 핸들링 및 서비스 호출
│   ├── llm/                         # [LLM] LLM 연동 및 프롬프트 관리
│   │   ├── __init__.py
│   │   ├── gemini_client.py         # [Client] V1 Gemini(2.5-flash-lite) 클라이언트 래퍼
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── node1_prompt.py      # [Prompt] Node 1 (구조 분석)용 시스템 프롬프트 및 데이터 포맷팅
│   │       └── node3_prompt.py      # [Prompt] Node 3 (체인 생성)용 시스템 프롬프트 및 COT 유도
│   ├── models/
│   │   ├── __init__.py
│   │   ├── planner/                 # [Model] V1 AI 플래너 도메인 모델
│   │   │   ├── request.py           # [Req] API 요청 스키마 (ArrangementState, ScheduleItem 등) - 입력 검증
│   │   │   ├── response.py          # [Res] API 응답 스키마 (AssignmentResult 등) - 클라이언트 반환 
│   │   │   ├── internal.py          # [Inner] LangGraph State 모델 (PlannerGraphState, TaskFeature) - 노드 간 데이터 전달
│   │   │   ├── weights.py           # [Conf] 개인화 가중치 파라미터 모델 (WeightParams) - 중요도/피로도 산식 계수
│   │   │   └── errors.py            # [Err] 에러 코드(Enum) 및 예외 매핑 헬퍼 (PlannerErrorCode)
│   │   └── planner_test.py          # [Model] V1 테스트용 Pydantic 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── planner/                 # [Service] V1AI 플래너 LangGraph Nodes
│   │   │   └── utils/
│   │   │       ├── time_utils.py    # [Util] 시간 문자열 변환, TimeZone 계산 등 시간 처리 헬퍼
│   │   │       └── session_utils.py # [Util] 가용 시간(FreeSession) 계산 및 Capacity 산출 헬퍼
│   │   │   └── nodes/               # [Node] 파이프라인 개별 단계 구현
│   │   │       ├── node1_structure.py     # [Node 1] 구조 분석: LLM을 이용해 작업 분류(Category) 및 인지 부하(CogLoad) 분석
│   │   │       ├── node2_importance.py    # [Node 2] 중요도 산정: 규칙 기반(Rule-based) 중요도 및 피로도 점수 계산
│   │   │       └── node3_chain_generator.py # [Node 3] 체인 생성: LLM을 이용해 최적의 작업 배치 시나리오(Candidate) 생성
│   │   └── gemini_test_planner_service.py  # [Service] V1 플래너 테스트 (단순 Gemini 호출 및 응답 파싱)
│   ├── db/                          # [DB] 데이터베이스 연동
│   │   ├── __init__.py
│   │   └── supabase_client.py       # [DB] Supabase 클라이언트 설정 및 연결 관리
│   └── core/
│       ├── __init__.py
│       └── config.py                # [Config] Pydantic BaseSettings 기반 환경 변수 로드 (.env 관리)
├── requirements.txt                 # [Dependency] 프로젝트 의존성 패키지 목록 (fastapi, google-genai, langgraph 등)
├── .env                             # [Env] 로컬 실행용 환경 변수 파일 (API Key 등 보안 정보 포함)
├── .env.example                     # [Env] 환경 변수 템플릿 (필수 설정값 예시)
└── .env.production                  # [Env] 프로덕션 배포용 환경 변수
```

### V1 - 플래너 생성 Gemini API 테스트
1. `app/models/planner_test.py`
    - API의 Request/Response 스키마 정의
    - `PlannerGenerateRequestTest`, `PlannerGenerateResponseTest`
2. `app/services/gemini_test_planner_service.py`
    - Request를 통해 Gemini에 입력할 Prompt 정의
    - Gemini API 호출 및 응답 json 파싱    
3. `app/api/v1/gemini_test_planners.py`
    - API 엔드포인트 연결 `ai/v1/planners`
        - 백엔드 테스트용 API, 추후 LangGraph 완성 뒤 대체
    - Request를 통해 Gemini API 호출
    - 응답을 Response로 변환

---

### V1 - Node 1: 구조 분석
1. `app/llm/gemini_client.py`
    - Gemini Client 초기화
    - Gemini API 호출 및 응답 json 파싱
2. `app/llm/prompts/node1_prompt.py`
    - Node 1에 사용될 Prompt 정의
    - 입력에 필요한 정보만 추출하여 포멧에 맡게 변환
3. `app/models/planner/internal.py`
    - Node 1의 응답을 처리하기 위한 모델 정의
    - `PlannerGraphState` : LangGraph의 State, 모든 Node를 관통함
    - `TaskFeature` : Task의 Feature를 나타내는 모델, Node 1의 응답을 처리하여 생성
        - `taskId`, `dayPlanId`, `title`, `type`, `category`, `cognitiveLoad`, `groupId`, `groupLabel`, `orderInGroup`
4. `app/services/planner/nodes/node1_structure.py`
    - Node 1의 응답을 처리하여 `PlannerGraphState`를 업데이트
    - `TaskFeature`를 생성하고 `PlannerGraphState`에 저장
    - 재시도 횟수를 기록
5. `tests/data/test_request.json`
    - Node 1의 응답을 테스트하기 위한 Request 데이터
6. `tests/test_node1.py`
    - Node 1의 응답을 테스트하기 위한 테스트 코드
```bash
python -m unittest tests/test_node1.py
```
7. `tests/test_node1_fallback.py`
    - Node 1의 폴백(4회 재시도 실패)응답을 테스트하기 위한 테스트 코드
```bash
python -m unittest tests/test_node1_fallback.py
```
---

### V1 - Node 2: 중요도 산출
1. `app/llm/prompts/node2_importance.py`
    - Node 1의 결과를 토대로
    - 각 작업별 중요도, 피로도를 산출
    - 이때 개인별 가중치 파라미터가 곱해진다 (개인화 AI는 후에 구현 예정, 현재는 기본값) 
2. `tests/test_node2.py`
    - Node 2의 응답을 테스트하기 위한 테스트 코드
```bash
python -m unittest tests/test_node2.py
```
3. `tests/test_integration_node1_node2.py`
    - Node 1 -> Node 2 통합 테스트
```bash
python -m unittest tests/test_integration_node1_node2.py
```
---

### V1 - Node 3: 후보 체인 생성
1. `app/llm/prompts/node3_prompt.py`
    - Node 2의 결과와 시간대별 가용 용량(Capacity)을 입력으로 받아
    - 4~6개의 후보 체인(Chain Candidates)을 생성하는 프롬프트
2. `app/services/planner/utils/session_utils.py`
    - 자유 배치 세션(FreeSession)별 시간대의 가용 용량(Capacity)을 계산
3. `app/services/planner/nodes/node3_chain_generator.py`
    - LLM 호출 및 재시도(Retry 4회) 로직
    - 실패 시 Fallback(중요도 순 배치) 로직 포함
4. `tests/test_node3.py`
    - 정상 동작 테스트 (Capacity 계산, Real LLM 호출)
```bash
python -m unittest tests/test_node3.py
```
5. `tests/test_node3_fallback.py`
    - Fallback 로직 테스트 (Mocking을 통한 에러 상황 시뮬레이션)
```bash
python -m unittest tests/test_node3_fallback.py
```
6. `tests/test_integration_node1_to_node3.py`
    - Node 1 -> Node 2 -> Node 3 파이프라인 통합 테스트
```bash
python -m unittest tests/test_integration_node1_to_node3.py
```
---
## 참고 문서

- [api명세서.md](api명세서.md) - API 명세서
- [CHANGELOG.md](CHANGELOG.md) - 개발 진행 상황
- [CLAUDE.md](CLAUDE.md) - 개발 가이드
- [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) - 클라우드 배포 가이드
