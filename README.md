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
│   │       ├── gemini_test_planners.py  # [API] V1 Gemini 플래너 생성 엔드포인트 (POST /ai/v1/planners)
│   │       └── endpoints/           # [API] 주제별 엔드포인트 구현 (v1)
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
│   │   └── planner_test.py          # [Model] 테스트용 Pydantic 모델
│   ├── services/
│   │   ├── __init__.py
│   │   ├── personalization_service.py # [Service] 개인화 데이터 처리 서비스
│   │   ├── gemini_test_planner_service.py # [Service] V1 플래너 테스트 서비스
│   │   └── planner/                 # [Service] AI 플래너 LangGraph Nodes
│   │       ├── utils/
│   │       │   ├── time_utils.py    # [Util] 시간 처리 헬퍼
│   │       │   └── session_utils.py # [Util] 가용 시간 계산 헬퍼
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
├── tests/                           # [Test] 단위 및 통합 테스트 코드
│   ├── data/                        # [Data] 테스트용 샘플 JSON 데이터
│   └── ...                          # [Test] 테스트 코드
├── requirements.txt                 # [Dependency] 프로젝트 의존성
├── .env.example                     # [Env] 환경 변수 템플릿
└── README.md                        # 프로젝트 설명서
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
7. `tests/test_node3_normalization.py`
    - Node 3 중요도 점수 정규화 로직(0~1) 테스트
```bash
python -m unittest tests/test_node3_normalization.py
```

### V1 - Node 4: 체인 평가 (Chain Judgement)
1. `app/services/planner/nodes/node4_chain_judgement.py`
    - Node 3에서 생성된 후보 체인 중 최적의 체인을 선택
    - **Closure 강제**: 그룹 순서 위반 작업 제거
    - **Overflow Penalty**: 시간대별 가용량 초과 시 페널티 부과
    - **Scoring**: 포함/제외 효용, 피로도, 집중 시간대 정렬 등을 종합 평가
2. `tests/test_node4.py`
    - Node 4 로직 검증을 위한 단위 테스트
```bash
python -m unittest tests/test_node4.py
```
3. `tests/test_integration_node1_to_node4.py`
    - Node 1 -> Node 2 -> Node 3 -> Node 4 파이프라인 통합 테스트
```bash
python -m unittest tests/test_integration_node1_to_node4.py
```

### V1 - Node 5: 시간 배정 (Time Assignment)
1. `app/services/planner/nodes/node5_time_assignment.py`
    - Node 4가 선택한 최적 체인의 대기열을 받아 실제 시간(Start/End)을 확정
    - **Logic V1**: Gap 휴식(10분), 세션 경계 분할(Splitting on boundary), 단일 자식 평탄화(Flattening) 적용
    - *참고: MaxChunk 강제 분할 및 작업 도중 휴식은 V2로 연기됨*
2. `tests/test_node5.py`
    - Node 5 분할 및 배정 로직 단위 테스트
```bash
python -m unittest tests/test_node5.py
```
3. `tests/test_integration_node1_to_node5.py`
    - Node 1 -> Node 5 전체 파이프라인 통합 테스트 (시간 배정 및 분할 검증)
```bash
python -m unittest tests/test_integration_node1_to_node5.py
```

---

### V1 - 개인화 데이터 수집 (Personalization Ingest)
1. `app/api/v1/endpoints/personalization.py`
    - `POST /ai/v1/personalizations/ingest`
    - 백엔드로부터 사용자의 최종 플래너 및 수정 이력을 수신하여 DB에 저장
2. `tests/test_personalization_ingest.py`
    - API 엔드포인트 동작 검증
```bash
python -m unittest tests/test_personalization_ingest.py
```
3. **Swagger UI 테스트**:
    - 서버 실행 후 `/docs` 접속
    - `POST /ai/v1/personalizations/ingest` 클릭
    - **Example Value**가 일주일치 샘플 데이터로 자동 채워짐
    - **Execute** 버튼 클릭으로 즉시 테스트 가능


---
## 참고 문서

- [api명세서.md](api명세서.md) - API 명세서
- [CHANGELOG.md](CHANGELOG.md) - 개발 진행 상황
- [CLAUDE.md](CLAUDE.md) - 개발 가이드
- [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) - 클라우드 배포 가이드
