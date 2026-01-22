# 개발 진행 상황

날짜별 개발 진행 상황을 기록합니다.

---

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
