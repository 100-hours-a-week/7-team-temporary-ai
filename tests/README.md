# Cloud-Safe Tests (`tests/`)

이 디렉토리는 **CI/CD 파이프라인**이나 **배포 환경(Cloud)**에서 안전하게 실행할 수 있는 테스트 코드들을 포함합니다.

## 특징
- **No Cost**: 유료 API(Gemini)를 실제로 호출하지 않습니다.
- **No Side-Effects**: 실제 DB에 데이터를 쓰거나 수정하지 않습니다.
- **Fast**: Mocking을 활용하여 매우 빠르게 실행됩니다.

---

## 파일별 역할

### 1. `test_connectivity.py`
- **목적**: 외부 서비스 연결 상태 점검 (Health Check)
- **주요 기능**:
  - **Gemini API**: 단순 모델 목록 조회 등을 통해 API 키 유효성 및 연결 확인.
  - **Supabase DB**: 인증 확인 및 간단한 Select 쿼리로 DB 연결 확인.
- **실행**:
```bash
python -m unittest tests/test_connectivity.py
```

### 2. `test_logic_mock.py`
- **목적**: 개별 노드(Node 1~5) 단위 로직 검증 (Legacy)
- **주요 기능**:
  - `unittest.mock`을 사용하여 LLM 응답을 가상(Mock)으로 대체.
  - 각 노드 함수의 단독 실행 및 결과 검증.
- **실행**:
```bash
python -m unittest tests/test_logic_mock.py
```

### 4. `test_duration_constraints.py`
- **목적**: 작업 시간 제약 조건 및 분할 로직 검증
- **주요 기능**:
  - `MINUTE_UNDER_30`이 30-40분으로 설정되었는지 확인.
  - 세션이 30분보다 짧을 때 배정이 차단되는지 확인.
  - 분할 시 남은 조각이 30분 미만이면 분할을 방지하는지 확인.
- **실행**:
```bash
python -m unittest tests/test_duration_constraints.py
```

### 5. `test_personalization_ingest_api.py` (New)
- **목적**: `/ai/v1/personalizations/ingest` API 엔드포인트 검증
- **주요 기능**:
  - `userIds`와 `targetDate`를 포함한 유효한 요청에 대해 200 OK 응답 확인.
  - 필수 필드 누락 시 422 에러 반환 확인.
- **실행**:
```bash
python -m pytest tests/test_personalization_ingest_api.py
```

### 6. `test_weekly_report.py` (New)
- **목적**: `POST /ai/v2/reports/weekly` 주간 레포트 생성 파이프라인(배치 처리 및 무한 재시도 로직) 검증
- **주요 기능**:
  - `unittest.mock`을 사용하여 DB 조회/저장 및 Gemini API 호출(`gemini-3-flash-preview`, `gemini-2.5-flash`)을 가상(Mock)으로 대체.
  - 503 에러 발생 시 지정된 횟수만큼 재시도 후 Fallback 모델로 무한 재시도하는 로직이 정상 작동하는지 검증.
- **실행**:
```bash
pytest tests/test_weekly_report.py -v
```

---

## 실행 방법 (전체)

```bash
# 모든 Cloud-Safe 테스트 실행
pytest tests/
```
