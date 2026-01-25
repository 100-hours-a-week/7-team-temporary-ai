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

## 테스트 방법 (단위 테스트)

**주의사항**: `tests` 경로를 인식하기 위해 모듈 실행 방식(`-m`)을 권장합니다.
( `.env`에 `GEMINI_API_KEY`가 설정되어 있어야 실제 API 연동 테스트가 가능합니다. )

### Node 1 (구조 분석) 테스트

**1. 실제 AI 연동 테스트 (Integration)**
```bash
python -m unittest tests/test_node1.py
```
- **기능**: Gemini 실제 연동을 통해 카테고리 분류, 그룹핑(System Enforcement), 에러 처리를 검증합니다.
- **데이터**: 대학교 4학년 시나리오 (논문, 취업, 졸업프로젝트 등)

**2. 재시도 및 폴백 테스트 (Retry/Fallback)**
```bash
python -m unittest tests/test_node1_fallback.py
```
- **기능**: AI 호출이 연속적으로 실패할 경우, 시스템이 자가적으로 '기타' 카테고리 및 시간 기반 인지부하를 할당하는지 검증합니다.
- **방법**: Mock을 사용하여 5회 연속 실패를 시뮬레이션합니다.
83: 
84: ### Node 2 (중요도/필터링) 및 통합 테스트
85: 
86: **1. Node 2 단위 테스트**
87: ```bash
88: python -m unittest tests/test_node2.py
89: ```
90: - **기능**: 중요도(Importance) 및 피로도(Fatigue) 수식의 정확성 검증. `ERROR` 카테고리 필터링 동작 확인.
91: 
92: **2. Node 1 -> Node 2 통합 테스트 (Integration)**
93: ```bash
94: python -m unittest tests/test_integration_node1_node2.py
95: ```
96: - **기능**: LLM이 분석한 결과를 Node 2가 받아 처리하는 전체 파이프라인 흐름을 검증합니다.


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
│   │       ├── __init__.py
│   │       └── gemini_test_planners.py  # AI 플래너 생성 API 엔드포인트 (Gemini TEST)
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
│   │   └── planner_test.py          # Pydantic 모델 (Request/Response 스키마, 검증 로직)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── planner/                 # [NEW] AI 플래너 V2 서비스로직
│   │   │   └── utils/
│   │   │       ├── time_utils.py    # 시간 계산 유틸리티
│   │   │       └── session_utils.py # 세션 계산 유틸리티
│   │   │   └── nodes/               # [NEW] LangGraph 노드 로직
│   │   │       └── node1_structure.py # Node 1: 구조 분석 (분류, 그룹핑)
│   │   │       └── node2_importance.py # Node 2: 중요도 산정 및 필터링
│   │   └── gemini_test_planner_service.py  # Gemini API 호출 및 플래너 생성 비즈니스 로직
│   ├── db/                          # [NEW] 데이터베이스 관련
│   │   ├── __init__.py
│   │   └── supabase_client.py       # Supabase 클라이언트
│   └── core/
│       ├── __init__.py
│       └── config.py                # 환경 변수 설정 (Settings 클래스)
├── requirements.txt                 # Python 패키지 의존성
├── .env                             # 환경 변수 (로컬용, Git 미포함)
├── .env.example                     # 환경 변수 예시 파일
└── .env.production                  # 프로덕션 환경 변수 (Git 미포함)
```

---

## 참고 문서

- [api명세서.md](api명세서.md) - API 명세서
- [CHANGELOG.md](CHANGELOG.md) - 개발 진행 상황
- [CLAUDE.md](CLAUDE.md) - 개발 가이드
- [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) - 클라우드 배포 가이드
