# 챗봇 MCP(Model Context Protocol) 구축 가이드 - 상세 전략 (DB 스키마 맞춤형)

본 문서는 현재 구축된 데이터베이스 스키마(`DB_SCHEMA_AND_API.md`) 구조를 바탕으로, 날짜 기반 검색 및 임베딩 벡터 유사도 검색 기능을 갖춘 **챗봇 MCP(Model Context Protocol)** 를 개발하기 위한 상세 전략을 다룹니다.

---

## 1. 아키텍처 개요 및 사용 테이블 분석

AI 챗봇은 사용자의 질문 의도에 따라 알맞은 MCP Tool을 호출하여 Supabase(PostgreSQL) DB에서 데이터를 조회해야 합니다. 

**[주요 활용 테이블]**
*   **날짜/이력 검색용**: 
    *   `planner_records` (플래너 배치 날짜/통계 판별: `plan_date`, `start_arrange`, `day_end_time`)
    *   `record_tasks` (세부 작업 내용 및 배치 결과 확인: `created_date`, `title`, `category`, `assignment_status`)
    *   `schedule_histories` (사용자 행동 이력 조회: `created_date`, `event_type`)
    *   `weekly_reports` (주간 단위 통합 컨텍스트 조회: `base_date`, `content`)
*   **벡터/의미 검색용**: 
    *   `task_embeddings` (임베딩 텍스트 검색: `embedding`, `content`)

---

## 2. 날짜 기반 DB 검색 (Date-based Search) 전략

사용자가 *"이번 주에 완수한 일정을 보여줘"*, *"어제 무슨 운동을 했지?"* 와 같은 질문을 할 때 사용되는 검색 방식입니다.

### 2-1. 구현 대상 MCP Tool: `search_schedules_by_date`
날짜 범위와 특정 조건(카테고리, 상태 등)을 기반으로 스케줄 관련 데이터를 병합하여 반환합니다.

*   **입력 파라미터 (Input Schema)**
    *   `user_id` (Integer): 사용자 식별자.
    *   `start_date` (String): 검색 시작일 (YYYY-MM-DD 형식).
    *   `end_date` (String): 검색 종료일 (YYYY-MM-DD 형식).
    *   `target_table` (String, Optional): 조회할 타겟 테이블 (예: `tasks`, `reports`, `histories`). 지정하지 않으면 조인된 결과를 요약.
    *   `category` (String, Optional): 필터링할 특정 카테고리 (예: '운동', '업무' 등).

*   **실행 로직 (SQL Query 예시 - Python/asyncpg)**
    날짜 필드는 최근 스키마 마이그레이션으로 추가된 `plan_date`(planner_records)와 `created_date`(record_tasks)를 활용합니다.
    ```sql
    -- 예: 특정 기간의 특정 카테고리 작업 조회
    SELECT 
        pr.plan_date,
        rt.title,
        rt.category,
        rt.assignment_status,
        rt.start_at,
        rt.end_at
    FROM planner_records pr
    JOIN record_tasks rt ON pr.id = rt.record_id
    WHERE pr.user_id = $1
      AND pr.plan_date >= $2::date
      AND pr.plan_date <= $3::date
      AND rt.category = COALESCE($4, rt.category) -- Category가 주어지면 필터
    ORDER BY pr.plan_date, rt.start_at;
    ```

*   **출력 메타데이터 변환**
    조회된 DB Raw Data를 그대로 LLM에게 넘기기보다는, LLM이 이해하기 쉬운 **Markdown이나 JSON** 형태로 가공(요약)하여 Return 해야 컨텍스트 프롬프트 용량이 절약됩니다.

---

## 3. 임베딩 벡터 유사도 검색 (Semantic Search) 전략

사용자가 *"최근에 집중이 잘 안된다고 했던 날이 언제지?"*, *"건강이랑 관련된 계획 위주로 찾아봐"* 처럼 **키워드 일치가 아닌 의미적 유사도**가 필요한 경우 활용합니다.

### 3-1. 구현 대상 MCP Tool: `search_tasks_by_similarity`
HNSW 인덱스가 걸려있는 `task_embeddings` 테이블의 `embedding` (768차원) 컬럼과 `vector_cosine_ops`를 활용해 코사인 유사도 검색을 수행합니다.

*   **입력 파라미터 (Input Schema)**
    *   `user_id` (Integer): 사용자 식별자 (필수, 타인 데이터 침범 방지).
    *   `query` (String): 사용자가 검색하고자 하는 자연어 문장.
    *   `top_k` (Integer): 반환할 레코드 개수 (기본값: 5).
    *   `date_limit` (String, Optional): 특정 날짜 이후의 데이터만 찾고자 할 때 (`created_date` 기준).

*   **실행 로직**
    1.  **임베딩 생성**: 입력받은 `query` 문자열을 Gemini `text-embedding-004` (또는 동일한 768차원 모델) 서버 API에 전송하여 768차원의 float 배열(`query_vector`)을 얻어옵니다.
    2.  **벡터 검색 (SQL Query 예시 - pgvector)**
        ```sql
        SELECT 
            te.content,
            te.category,
            te.created_date,
            1 - (te.embedding <=> $2::vector) AS similarity_score
        FROM task_embeddings te
        WHERE te.user_id = $1
          -- 필요 시 date_limit 적용: AND te.created_date >= $4::date
        ORDER BY te.embedding <=> $2::vector -- 코사인 거리 기준 오름차순 (가장 유사한 것부터)
        LIMIT $3;
        ```

*   **고려 사항**
    *   벡터 유사도 검색 시 **사용자 격리(`user_id = ?`)가 1순위**로 이루어져야 합니다. 그 후 인덱스를 탈 수 있도록 쿼리 플랜을 확인해야 합니다.
    *   조회된 결과에서 `similarity_score`가 너무 낮다면 (예: 0.5 미만) LLM에게 "관련된 정보를 찾지 못했습니다"라고 알리는 Threshold 방어 로직이 서버 측에 구현되는 것이 좋습니다.

---

## 4. MCP 서버 구축 구현 단계 요약 (Python 기준)

### Step 1. MCP 및 데이터베이스 라이브러리 세팅
```bash
pip install mcp asyncpg pgvector pydantic google-generativeai python-dotenv
```

### Step 2. 서버 및 도구(Tools) 정의
`mcp` 라이브러리를 통해 데코레이터를 등록합니다.
```python
import mcp
from mcp.server import Server
from pydantic import BaseModel
import asyncpg
# ... (기타 임포트 생략)

app = Server("Planner-Chatbot-MCP")

# 1. 날짜 범위 검색 Tool
@app.tool("search_schedules_by_date", description="특정 기간 내의 일정, 플래시백 및 계획 데이터를 조회합니다.")
async def search_schedules_by_date(user_id: int, start_date: str, end_date: str) -> str:
    # DB 연결 (asyncpg) -> SQL 실행 -> JSON/String 결과 반환
    return result_string

# 2. 벡터 의미 기반 검색 Tool
@app.tool("search_tasks_by_similarity", description="자연어 쿼리를 기반으로 과거 스케줄 중 의미적으로 가장 유사한 기록을 검색합니다.")
async def search_tasks_by_similarity(user_id: int, query: str, top_k: int = 5) -> str:
    # 1. query -> Gemini 임베딩 API 호출 -> vector 획득 (768차원)
    # 2. DB 연결 (asyncpg) -> pgvector <=> 연산자 쿼리 실행 -> 매칭 상위 항목 반환 
    return matched_records_string
```

### Step 3. 클라이언트 연동 (챗봇 앱)
챗봇 엔진(LangGraph, LangChain 등) 초기화 시 구성한 MCP 서버를 tool_node로 바인딩합니다. 
챗봇 시스템 프롬프트에 다음과 같이 추가 지시를 명시합니다:
> *"사용자가 기간을 명시하면 'search_schedules_by_date'를 호출하고, 문맥적/의미적 검색이 필요하면 'search_tasks_by_similarity'를 호출하여 DB에서 근거를 찾은 후 대답하세요."*

---

## 5. 핵심 체크리스트 / 주의점
1. **Timezone 및 Date 파싱 통일**: DB에는 `TIMESTAMP` 및 `DATE` 타입으로 저장되므로, 챗봇이 API를 호출할 때 "오늘", "이번 주" 같은 상대적 단어를 어떻게 날짜(YYYY-MM-DD)로 변환해 MCP로 넘길지 챗봇 설계단에서 통제가 필요합니다.
2. **복합 쿼리 지원 (Hybrid Search)**: 필요하다면 먼저 임베딩 벡터로 `task_embeddings`를 검색하여 `record_task_id`를 알아낸 후, 이를 통해 `record_tasks`와 `planner_records` 테이블을 조인하여 구체적인 "해당 태스크 시행 당시의 맥락(피로도, 시작시간 등)"을 함께 가져오는 조합 쿼리를 작성하는 것이 데이터 품질을 높일 수 있습니다.
