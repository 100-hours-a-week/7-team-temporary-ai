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

### 7. `test_chat_service.py` (New)
- **목적**: 챗봇 API 스트리밍(SSE) 및 재시도(Fallback) 처리 검증
- **주요 기능**:
  - `unittest.mock`과 `asyncio.Queue`를 사용하여 LLM 스트리밍 응답 가상(Mock) 처리.
  - 503 에러 발생 시 지정된 횟수만큼 재시도 후 Fallback 모델(`gemini-2.5-flash`)로 전환되는 흐름 점검.
  - `POST` 세션 초기화, `GET` SSE 이벤트 포맷(`start`, `chunk`, `complete`, `error`), `DELETE` 진행 중인 태스크 취소 로직 검증.
- **실행**:
```bash
pytest tests/test_chat_service.py -v
```

### 8. `chat_test.html` (UI Test)
- **목적**: 브라우저 환경에서 SSE 스트리밍과 챗봇 응답이 원활히 동작하는지 시각적으로 테스트.
- **주요 기능**:
  - `fetch`를 이용하여 `userId: 999999`, `reportId: 9001`의 주간 레포트 데이터를 초기 로드.
  - 사용자 질문 전송(`POST /respond`) 및 `EventSource`를 통한 실시간 전송(`GET /stream`) 연동.
  - **Marked.js**를 사용해 LLM 응답을 마크다운으로 렌더링.
- **실행**:
1. 백엔드 서버를 구동합니다 (`python -m uvicorn app.main:app --reload`).
2. 브라우저에서 [http://localhost:8000/ai/v2/reports/9001/chat/test](http://localhost:8000/ai/v2/reports/9001/chat/test) 접속.

### 9. `test_mcp_server.py` (New)
- **목적**: MCP(Model Context Protocol) 서버의 도구(`search_schedules_by_date`) 로직 검증
- **주요 기능**:
  - `unittest.mock`을 사용하여 Supabase DB 호출을 가상(Mock)으로 대체.
  - 날짜 범위 검색에 따른 결과 Markdown 생성 로직의 정확성 확인.
  - 데이터 부재 시 혹은 DB 에러 발생 시 예외 처리 로직 점검.
- **실행**:
```bash
python -m pytest tests/test_mcp_server.py
```

---

## 실행 방법 (전체)

```bash
# 모든 Cloud-Safe 테스트 실행
pytest tests/
```
