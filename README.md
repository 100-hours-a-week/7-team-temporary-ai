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

### 4. 접속

- Swagger UI: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## 프로젝트 구조

```
MOLIP-AI/
├── app/
│   ├── main.py           # FastAPI 애플리케이션 진입점
│   ├── api/v1/           # API 엔드포인트 (버전별 라우터)
│   ├── models/           # Pydantic 모델 (Request/Response 스키마)
│   ├── services/         # 비즈니스 로직
│   └── core/             # 환경 설정, 공통 유틸리티
├── requirements.txt      # 패키지 목록
└── .env                  # 환경 변수
```

---

## 참고 문서

- [api명세서.md](api명세서.md) - API 명세서
- [CHANGELOG.md](CHANGELOG.md) - 개발 진행 상황
- [CLAUDE.md](CLAUDE.md) - 개발 가이드
- [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) - 클라우드 배포 가이드
