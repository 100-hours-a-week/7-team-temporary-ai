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
