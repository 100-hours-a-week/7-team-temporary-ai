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

## Observability (Logfire)

MOLIP AI 서버는 [Logfire](https://logfire.pydantic.dev)를 통해 전체 API 요청 및 LLM 실행 흐름을 추적합니다.

### 🌟 주요 기능
1. **Web Server Metrics**: API 응답 속도, 에러율 자동 수집 (`logfire.instrument_fastapi`)
2. **LLM Analytics**: 토큰 사용량(비용), 프롬프트/응답 디버깅 (`logfire.span`)
3. **Structured Logging**: SQL 질의 가능한 형태의 로그 저장

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

