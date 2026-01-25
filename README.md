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
│   ├── main.py                      # FastAPI 애플리케이션 진입점, 라우터 등록, CORS 설정
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py          # V1 통합 라우터
│   │       └── gemini_test_planners.py  # [V1] Gemini AI 플래너 생성 테스트 API 엔드포인트
│   ├── llm/                         # [NEW] LLM 관련 (Client, Prompts)
│   │   ├── __init__.py
│   │   ├── gemini_client.py         # Google GenAI (Gemini) 클라이언트 (v2.5)
│   │   └── prompts/
│   │       ├── __init__.py
│   │       └── node1_prompt.py      # Node 1 (구조 분석) 프롬프트
│   ├── models/
│   │   ├── __init__.py
│   │   ├── planner/                 # [NEW] AI 플래너 V2 모델
│   │   │   ├── request.py           # API 요청 모델
│   │   │   ├── response.py          # API 응답 모델
│   │   │   ├── internal.py          # 내부 처리용 모델
│   │   │   └── weights.py           # 가중치 설정 모델
│   │   └── planner_test.py          # [V1] Gemini 플래너 생성 Pydantic 모델 (Request/Response 스키마, 검증 로직)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── planner/                 # [NEW] AI 플래너 V2 서비스로직
│   │   │   └── utils/
│   │   │       ├── time_utils.py    # 시간 계산 유틸리티
│   │   │       └── session_utils.py # 세션 계산 유틸리티
│   │   │   └── nodes/               # [NEW] LangGraph 노드 로직
│   │   │       └── node1_structure.py # Node 1: 구조 분석 (분류, 그룹핑)
│   │   │       └── node2_importance.py # Node 2: 중요도 산정 및 필터링
│   │   └── gemini_test_planner_service.py  # [V1] Gemini 플래너 생성 API 호출
│   ├── db/                          # [NEW] 데이터베이스 관련
│   │   ├── __init__.py
│   │   └── supabase_client.py       # Supabase 클라이언트
│   └── core/
│       ├── __init__.py
│       └── config.py                # 환경 변수 설정 (.env 파일 설정 로드)
├── requirements.txt                 # Python 패키지 의존성
├── .env                             # 환경 변수 (로컬용, Git 미포함)
├── .env.example                     # 환경 변수 예시 파일
└── .env.production                  # 프로덕션 환경 변수 (Git 미포함)
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
## 참고 문서

- [api명세서.md](api명세서.md) - API 명세서
- [CHANGELOG.md](CHANGELOG.md) - 개발 진행 상황
- [CLAUDE.md](CLAUDE.md) - 개발 가이드
- [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) - 클라우드 배포 가이드
