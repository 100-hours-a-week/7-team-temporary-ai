# MOLIP AI Server

MOLIP 프로젝트의 AI 기능 서버입니다.

## 작성자 : ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white) [max.ji](https://github.com/Max-JI64/)

---

## 로컬 실행 방법

### 1. 가상환경 설정

```bash
# 기존 가상환경 삭제

## 가상환경 확인
ls -d */

## 가상환경 삭제
rm -rf venv
```

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

### 3. 테스트 진행
```bash
# 약 3초 소요
pytest tests/
```

### 4. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 필요한 값을 설정합니다.

```bash
cp .env.example .env
```

> **Note**: 환경 변수 상세 설명은 [.env.example](.env.example) 파일을 참고하세요.

### 5. 서버 실행

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 접속

- Swagger UI: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## LLM 설정 (Current Configuration)

현재 구현 단계(Step 3)에서는 다음과 같은 설정을 사용합니다. (추후 벤치마크 결과에 따라 모델이나 재시도 정책은 변경될 수 있습니다.)

- **Model**: `gemini-2.5-flash-lite` (Google GenAI)
- **Retry Policy**: Node 1(구조 분석)에서 LLM 응답 실패 시 **총 5회(1회 시도 + 4회 재시도)** 수행 후 Fallback 로직으로 전환합니다.

---

## 주요 플래너 로직 (Core Planner Logic)

MOLIP AI 플래너는 정교한 스케줄링을 위해 다음과 같은 세부 로직을 포함합니다.

1. **부모 작업(Container) 자동 필터링**
   - 하위 작업(Sub-tasks)이 존재하는 부모 작업은 실제 수행 시간이 필요한 실무 작업이 아닌 '컨테이너(그룹)'로 간주합니다.
   - 플래너 내부 분석(Node 1~4) 및 최종 시간 배정(Node 5) 단계에서 자동으로 필터링되어 결과에 중복 노출되지 않습니다.

2. **비정상 작업(ERROR) 처리**
   - Node 1(구조 분석)에서 "ERROR" 카테고리로 분류된 작업(예: "asdf", "ㅁㄴㅇㄹ" 등 무의미한 입력)은 스케줄링 엔진에 의해 무시됩니다.
   - 하지만 사용자가 입력한 데이터의 누락을 방지하기 위해, 최종 API 응답에는 `EXCLUDED` 상태로 포함되어 반환됩니다.

3. **최소 작업 시간 (Minimum Duration) 강제**
   - 모든 AI 배정 작업(FLEX)의 최소 시간은 **30분**으로 설정됩니다.
   - `MINUTE_UNDER_30` 옵션의 범위는 기존 10~30분에서 **30~40분**으로 조정되었습니다.
   - 작업 분할(Splitting) 시에도, 남은 자투리 시간이 30분 미만이면 분할하지 않고 해당 세션에 배정을 포기합니다. (프론트엔드 렌더링 이슈 방지)

---

## Observability (Logfire & LangSmith)

MOLIP AI 서버는 복잡한 LLM 파이프라인의 가시성을 위해 **Logfire**와 **LangSmith**를 동시에 활용합니다.

### 1. Logfire (Application Tracing)
- **Role**: API 요청 전체 흐름, Python 함수 실행 시간, 에러 추적.
- **Integration**: `logfire.instrument_fastapi` 및 `@logfire.instrument`.
- **Dashboard**: [Logfire Console](https://logfire.pydantic.dev)

### 2. LangSmith (LLM Workflow Tracing)
- **Role**: **LangGraph** 기반의 플래너 생성 로직(Node 1~5)의 상태 전이(State Transition)와 재시도(Retry) 과정을 시각화.
- **Integration**: `.env`에 `LANGCHAIN_TRACING_V2=true` 설정 시 자동 활성화.
- **Dashboard**: [LangSmith Console](https://smith.langchain.com)
- **Key Features**:
  - **Cycle Visualization**: Loop로 구현된 재시도 로직을 그래프 형태로 직관적으로 확인.
  - **State Inspection**: 각 노드 사이를 이동하는 `PlannerGraphState` 데이터 변화 추적.


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
│   │       ├── __init__.py          # [API] V1 라우터 통합 (endpoints 하위 라우터들 포함)
│   │       └── endpoints/           # [API] 주제별 엔드포인트 구현 (v1)
│   │           ├── planners.py        # [API] V1 플래너 생성 (POST /ai/v1/planners)
│   │           └── personalization.py # [API] 개인화 데이터 수집 (POST /ai/v1/personalizations/ingest)
│   ├── llm/                         # [LLM] LLM 연동 및 프롬프트 관리
│   │   ├── __init__.py
│   │   ├── gemini_client.py         # [Client] V1 Gemini(2.5-flash-lite) 클라이언트 래퍼
│   │   └── prompts/
│   │       ├── __init__.py
│   │       ├── node1_prompt.py      # [Prompt] Node 1 (구조 분석)용 프롬프트
│   │       └── node3_prompt.py      # [Prompt] Node 3 (체인 생성)용 프롬프트
│   ├── models/
│   │   ├── __init__.py
│   │   ├── personalization.py        # [Model] 개인화 데이터 수집 요청/응답 모델
│   │   ├── planner/                 # [Model] AI 플래너 도메인 모델
│   │   │   ├── request.py           # [Req] API 요청 스키마
│   │   │   ├── response.py          # [Res] API 응답 스키마
│   │   │   ├── internal.py          # [Inner] LangGraph State 모델
│   │   │   ├── weights.py           # [Conf] 개인화 가중치 파라미터 모델
│   │   │   └── errors.py            # [Err] 에러 코드 및 예외 매핑
│   ├── services/
│   │   ├── __init__.py
│   │   ├── personalization_service.py # [Service] 개인화 데이터 처리 서비스
│   │   └── planner/                 # [Service] AI 플래너 LangGraph Nodes
│   │       ├── utils/
│   │       │   ├── time_utils.py    # [Util] 시간 처리 헬퍼
│   │       │   ├── session_utils.py # [Util] 가용 시간 계산 헬퍼
│   │       │   └── task_utils.py    # [Util] 부모 작업 필터링 등 태스크 기반 유틸리티
│   │       └── nodes/               # [Node] 파이프라인 개별 단계 구현
│   │           ├── node1_structure.py       # [Node 1] 구조 분석
│   │           ├── node2_importance.py      # [Node 2] 중요도 산정
│   │           ├── node3_chain_generator.py # [Node 3] 체인 생성
│   │           ├── node4_chain_judgement.py # [Node 4] 체인 평가 (최적해 선택)
│   │           └── node5_time_assignment.py # [Node 5] 시간 배정 (최종 확정 - V1: Flattening applied)
│   ├── db/                          # [DB] 데이터베이스 연동
│   │   ├── __init__.py
│   │   ├── supabase_client.py       # [DB] Supabase 클라이언트 설정
│   │   └── repositories/            # [DB] 저장소 레이어
│   │       └── personalization_repository.py # [DB] 개인화 데이터 저장소
│   └── core/
│       ├── __init__.py
│       └── config.py                # [Config] 환경 변수 로드
├── tests/                           # [Test] CI/CD 환경용 단위/통합 테스트 (Mock 기반, Cloud-Safe)
│   ├── data/                        # [Data] 테스트용 샘플 JSON 데이터
│   └── ...                          # [Test] 테스트 코드
├── tests_local/                     # [TestLocal] 로컬 개발용 테스트 (Real DB/LLM 연동)
│   ├── test_planner_repository.py   # [DB] 플래너 저장 리포지토리 테스트
│   ├── reproduce_db_save.py         # [Script] DB 저장 로직 재현 스크립트
│   └── ...
├── requirements.txt                 # [Dependency] 프로젝트 의존성
├── .env.example                     # [Env] 환경 변수 템플릿
└── README.md                        # 프로젝트 설명서

---

## DB Integration (Supabase)

MOLIP AI는 Supabase(PostgreSQL)와 연동하여 AI가 생성한 플래너 초안(`AI_DRAFT`)과 사용자 최종 데이터(`USER_FINAL`)를 관리합니다.

### 주요 기능
1. **비동기 저장**: API 응답 지연 없이 `BackgroundTasks`를 통해 DB에 저장.
2. **분할 작업(Split Task) 지원**: 작업이 시간 부족으로 분할될 경우, `is_split=True`인 부모 레코드와 `is_split=False`인 자식 레코드로 나누어 저장.
3. **통계 자동 산출**: 플래너 생성 시점의 가동률(Fill Rate), 배정된 작업 수 등을 자동으로 계산하여 메타데이터에 포함.

### 로컬 DB 테스트
실제 DB 연결이 필요한 테스트는 `tests_local/` 디렉토리에서 수행합니다.

```bash
# DB 저장 재현 스크립트 실행
python tests_local/reproduce_db_save.py
```
```

