# MOLIP AI Server

MOLIP 프로젝트의 AI 기능 서버입니다. 여러 AI 기능들이 이 저장소에서 개발됩니다.

## 최종 수정일 : 2026년 1월 20일
> 수정 이력
> - 26.01.20 AI 플래너 생성 TEST API 개발 (Phase 1-4 완료)
>   - Phase 1: Python 환경 설정 및 프로젝트 구조 생성
>   - Phase 2: Pydantic 모델 구현 (TEST 버전)
>   - Phase 3: FastAPI 엔드포인트 구현 (TEST 버전)
>   - Phase 4: 로컬 서버 실행 및 테스트 완료, 백엔드 연동 가이드 작성

## 작성자 : ![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=GitHub&logoColor=white) [swoo64](https://github.com/swoo64)

---

# 목차

> [프로젝트 개요](#프로젝트-개요)
>
> [AI 기능 목록](#AI-기능-목록)
> &nbsp;&nbsp;&nbsp;&nbsp;1. [AI 플래너 생성 (POST /ai/v1/planners)](#1-AI-플래너-생성-POST-aiv1planners)
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- [개요](#개요)
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- [개발 진행 상황](#개발-진행-상황)
>
> [설치 및 실행](#설치-및-실행)
> &nbsp;&nbsp;&nbsp;&nbsp;1. [가상환경 설정](#1-가상환경-설정)
> &nbsp;&nbsp;&nbsp;&nbsp;2. [패키지 설치](#2-패키지-설치)
> &nbsp;&nbsp;&nbsp;&nbsp;3. [환경 변수 설정](#3-환경-변수-설정)
> &nbsp;&nbsp;&nbsp;&nbsp;4. [서버 실행](#4-서버-실행)
>
> [프로젝트 구조](#프로젝트-구조)
>
> [개발 문서](#개발-문서)
>
> [클라우드 배포 (클라우드팀용)](#클라우드-배포-클라우드팀용)
>
> [기여 가이드](#기여-가이드)
> &nbsp;&nbsp;&nbsp;&nbsp;- [Git 워크플로우](#Git-워크플로우)
> &nbsp;&nbsp;&nbsp;&nbsp;- [코딩 컨벤션](#코딩-컨벤션)
>
> [라이센스](#라이센스)
>
> [팀 정보](#팀-정보)

---

## 프로젝트 개요
### **↑** [목차로 돌아가기](#목차)

- **기술 스택**: FastAPI + Python 3.13
- **스테이징 서버**: https://stg.molip.today/
- **프로덕션 서버**: https://molip.today/
- **개발 환경**: macOS
- **배포**: 클라우드팀이 관리 (이 저장소는 AI 소스 코드만 제공)

---

## AI 기능 목록
### **↑** [목차로 돌아가기](#목차)

### 1. AI 플래너 생성 (POST /ai/v1/planners)

#### 개요
### **↑** [목차로 돌아가기](#목차)
- **담당 파트**: AI 플래너 생성
- **API 엔드포인트**: `POST /ai/v1/planners`
- **목적**: 백엔드로부터 Todo list + 사용자 프로필 + 배치 기준 시간을 받아 플래너 배정 결과 생성

#### 개발 진행 상황
### **↑** [목차로 돌아가기](#목차)

##### 2026-01-20 (Phase 1-5.5 완료)

**Phase 1: 환경 설정 및 프로젝트 초기화**
- [x] Python 3.13.5 환경 확인
- [x] 가상환경 생성 (`venv/`)
- [x] requirements.txt 작성
  - FastAPI, Uvicorn, Pydantic, python-dotenv 등
- [x] 프로젝트 디렉토리 구조 생성
  ```
  app/
  ├── __init__.py
  ├── api/v1/
  ├── models/
  ├── services/
  └── core/
  ```
- [x] .env 파일 생성 (환경 변수 설정)
- [x] .gitignore 정리

**Phase 2: Pydantic 모델 구현 (TEST 버전)**
- [x] 기본 타입 정의 (`TimeHHMM`, `BigInt64`)
- [x] Enum 클래스 구현
  - `FocusTimeZone`, `TaskType`, `EstimatedTimeRange`, `AssignedBy`, `AssignmentStatus`
- [x] Request Models (Test 버전)
  - `PlannerUserContextTest`: 사용자 컨텍스트
  - `PlannerScheduleInputTest`: 작업 입력 (validator 포함)
  - `PlannerGenerateRequestTest`: 전체 요청 바디
- [x] Response Models (Test 버전)
  - `PlannerScheduleResultTest`: 작업별 배치 결과
  - `PlannerGenerateResponseTest`: 전체 응답 바디

**파일 위치**: [app/models/planner_test.py](app/models/planner_test.py)

**TEST 로직 사양**:
```
목적: 백엔드 연동 확인을 위한 단순 에코(echo) 응답

규칙:
1. 그대로 반환: taskId, dayPlanId, title, type, startAt, endAt
2. 조건부 생성:
   - assignedBy: FIXED → "USER", FLEX → "AI"
   - assignmentStatus: FIXED → "ASSIGNED", FLEX → "EXCLUDED"
```

**Phase 3: FastAPI 엔드포인트 구현 (TEST 버전)**
- [x] 서비스 로직 구현
  - [app/services/planner_service_test.py](app/services/planner_service_test.py): TEST 비즈니스 로직
- [x] API 라우터 구현
  - [app/api/v1/planners_test.py](app/api/v1/planners_test.py): `POST /ai/v1/planners` 엔드포인트
- [x] 환경 설정
  - [app/core/config.py](app/core/config.py): Pydantic Settings로 환경 변수 관리
- [x] FastAPI 애플리케이션
  - [app/main.py](app/main.py): 메인 애플리케이션, CORS 설정, 라우터 등록
  - Health check 엔드포인트 (`GET /health`)
  - Root 엔드포인트 (`GET /`)

**Phase 4: 로컬 서버 실행 및 테스트**
- [x] 패키지 설치 완료
  - FastAPI 0.128.0, Uvicorn 0.40.0, Pydantic 2.12.5 등
- [x] 서버 시작 성공
  - http://0.0.0.0:8000 에서 실행
  - CORS 설정 정상 작동 (스테이징 서버 허용)
- [x] 엔드포인트 테스트 완료
  - ✅ `GET /health`: 서버 상태 정상
  - ✅ `GET /`: API 정보 반환
  - ✅ `POST /ai/v1/planners`: TEST 로직 정상 작동
    - FIXED 작업 → assignedBy="USER", assignmentStatus="ASSIGNED"
    - FLEX 작업 → assignedBy="AI", assignmentStatus="EXCLUDED"
- [x] 로깅 확인
  - 요청/응답 로그 정상 출력
  - [test_request.json](test_request.json): 테스트용 샘플 데이터

**테스트 결과 (Phase 4)**:
```json
// 입력: 3개 작업 (FIXED 2개, FLEX 1개)
// 출력: TEST 로직에 따라 정확히 변환됨
{
  "schedules": [
    {"taskId": 1, "type": "FIXED", "assignedBy": "USER", "assignmentStatus": "ASSIGNED", ...},
    {"taskId": 2, "type": "FLEX", "assignedBy": "AI", "assignmentStatus": "EXCLUDED", ...},
    {"taskId": 3, "type": "FIXED", "assignedBy": "USER", "assignmentStatus": "ASSIGNED", ...}
  ]
}
```

**확장 테스트 결과 (Phase 5.5)**:
```json
// 입력: 8개 작업 (FIXED 4개, FLEX 4개)
// 다양한 시간대 및 estimatedTimeRange 조합 테스트 성공
// - FIXED: 아침 운동(07:00), 팀 회의(10:00), 점심(12:00), 저녁(18:30)
// - FLEX: 통계학 과제(2-4시간), 코딩(30-60분), 영어(1-2시간), 독서(4시간+)
// 모든 케이스 정상 작동 확인
```

**Swagger UI 테스트**
- [x] Swagger UI 자동 예시 추가
  - Pydantic 모델에 `json_schema_extra` 추가
  - 버튼만 클릭해도 8개 task 예시 자동 입력
  - 복붙 없이 "Execute" 버튼만으로 테스트 가능

**로컬 개발 환경**:
```bash
# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Swagger UI 접속
http://localhost:8000/docs

# Health Check
http://localhost:8000/health
```

**다음 단계**: 백엔드 연동 테스트 및 실제 AI 로직 구현

---

## 설치 및 실행
### **↑** [목차로 돌아가기](#목차)

### 1. 가상환경 설정
### **↑** [목차로 돌아가기](#목차)

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate

# 가상환경 활성화 (Windows)
venv\Scripts\activate
```

### 2. 패키지 설치
### **↑** [목차로 돌아가기](#목차)

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
### **↑** [목차로 돌아가기](#목차)

**중요: 모든 URL과 설정은 .env 파일로 관리됩니다 (하드코딩 없음)**

환경별 파일:
- `.env` - 개발용 (이미 생성됨)
- `.env.staging` - 스테이징용 (https://stg.molip.today)
- `.env.production` - 프로덕션용 (https://molip.today)

개발 환경은 기본 `.env` 파일을 사용하면 됩니다:

```env
APP_NAME=MOLIP-AI-Planner
DEBUG=True
ENVIRONMENT=development
BACKEND_URL=https://stg.molip.today
ALLOWED_ORIGINS=https://stg.molip.today,http://localhost:3000
```

**배포 시 환경 변수 교체 방법:**
```bash
# 스테이징 배포
cp .env.staging .env

# 프로덕션 배포
cp .env.production .env
```

### 4. 서버 실행
### **↑** [목차로 돌아가기](#목차)

```bash
# 개발 서버 실행 (hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 Python으로 직접 실행
python -m app.main
```

**접속 가능한 엔드포인트**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health
- Root: http://localhost:8000/

---

## 프로젝트 구조
### **↑** [목차로 돌아가기](#목차)

```
MOLIP-AI/
├── app/
│   ├── __init__.py
│   ├── main.py                      # ✅ FastAPI 애플리케이션 진입점
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── planners_test.py     # ✅ AI 플래너 엔드포인트 (TEST)
│   ├── models/
│   │   ├── __init__.py
│   │   └── planner_test.py          # ✅ Pydantic 모델 (TEST 버전)
│   ├── services/
│   │   ├── __init__.py
│   │   └── planner_service_test.py  # ✅ 비즈니스 로직 (TEST)
│   └── core/
│       ├── __init__.py
│       └── config.py                # ✅ 환경 설정
├── venv/                            # 가상환경 (gitignore)
├── .env                             # ✅ 환경 변수 개발용 (gitignore)
├── .env.staging                     # ✅ 환경 변수 스테이징용 (gitignore)
├── .env.production                  # ✅ 환경 변수 프로덕션용 (gitignore)
├── .env.example                     # ✅ 환경 변수 예시 (Git 포함)
├── .gitignore
├── requirements.txt                 # ✅ 패키지 목록
├── CLOUD_DEPLOYMENT_INFO.md         # ✅ 클라우드 배포 가이드 (클라우드팀용)
├── api명세서.md                     # API 명세서
└── README.md                        # 이 파일
```

---

## 개발 문서
### **↑** [목차로 돌아가기](#목차)

- **API 명세서**: [api명세서.md](api명세서.md)
- **개발 가이드**: [claude.md](claude.md)
  - 단계별 개발 계획
  - TEST 로직 상세 사양
  - 체크리스트
- **클라우드 배포 가이드**: [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md)
  - 클라우드팀 전달용
  - 환경 변수 설정
  - Docker/systemd/PM2 배포 방법

---

## 클라우드 배포 (클라우드팀용)
### **↑** [목차로 돌아가기](#목차)

**이 저장소는 AI 기능 소스 코드만 제공합니다. 실제 서버 배포는 클라우드팀이 관리합니다.**

### 클라우드팀에 전달할 파일
```
✅ 필수:
- app/ (전체 소스 코드)
- requirements.txt (패키지 목록)
- .env.example (환경 변수 예시)

📖 참고:
- CLOUD_DEPLOYMENT_INFO.md (배포 상세 가이드)
- ENV_GUIDE.md (환경 변수 설명)
```

### 서버 실행 방법 (요약)
```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 환경 변수 설정 (.env 파일 또는 클라우드 환경 변수)
BACKEND_URL=https://stg.molip.today  # 스테이징
ALLOWED_ORIGINS=https://stg.molip.today

# 3. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**상세 내용**: [CLOUD_DEPLOYMENT_INFO.md](CLOUD_DEPLOYMENT_INFO.md) 참고

---

## 기여 가이드
### **↑** [목차로 돌아가기](#목차)

### Git 워크플로우
### **↑** [목차로 돌아가기](#목차)

```bash
# 현재 브랜치
git branch  # feature/api

# 변경사항 확인
git status

# 커밋
git add .
git commit -m "feat: Add Pydantic models for AI planner (TEST version)"

# 푸시
git push origin feature/api
```

### 코딩 컨벤션
### **↑** [목차로 돌아가기](#목차)

- Python: PEP 8 스타일 가이드 준수
- 모델명: 명확하고 일관된 네이밍 (예: `PlannerUserContextTest`)
- 주석: 복잡한 로직에는 한글 주석 권장

---

## 라이센스
### **↑** [목차로 돌아가기](#목차)

TBD

---

## 팀 정보
### **↑** [목차로 돌아가기](#목차)

- **프로젝트**: MOLIP (7팀)
- **개발 기간**: 2026-01 ~
- **연락처**: TBD
