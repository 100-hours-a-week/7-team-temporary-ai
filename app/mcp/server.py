import os
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.core.config import settings
import logfire

# Logfire 설정
logfire.configure(token=settings.logfire_token, send_to_logfire='if-token-present')

# FastMCP 서버 인스턴스 생성
mcp = FastMCP("MOLIP Scheduler")

@mcp.tool()
@logfire.instrument("mcp.tool.search_schedules_by_date")
async def search_schedules_by_date(
    user_id: int, 
    start_date: str, 
    end_date: Optional[str] = None
) -> str:
    """사용자의 과거 일정(플래너) 기록을 특정 날짜 범위로 검색합니다."""
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    try:
        async with AsyncSessionLocal() as session:
            # 1. planner_records 조회
            records_query = text("""
                SELECT id, start_arrange, day_end_time, focus_time_zone, planner_date 
                FROM planner_records 
                WHERE user_id = :user_id 
                  AND record_type = 'USER_FINAL' 
                  AND planner_date >= :start_date 
                  AND planner_date <= :end_date
            """)
            records_res = await session.execute(records_query, {
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date
            })
            planner_data = [dict(row._mapping) for row in records_res]
            
            if not planner_data:
                return f"[{start_date} ~ {end_date}] 기간 동안 완료된 플래너 기록이 없습니다."

            record_ids = [r["id"] for r in planner_data]
            
            # 2. record_tasks 조회
            tasks_query = text("""
                SELECT * FROM record_tasks 
                WHERE record_id = ANY(:record_ids) 
                  AND assignment_status = 'ASSIGNED'
            """)
            tasks_res = await session.execute(tasks_query, {"record_ids": record_ids})
            tasks_data = [dict(row._mapping) for row in tasks_res]
            
            # 3. Markdown Formatting
            result_md = f"## 📅 일정 검색 결과 ({start_date} ~ {end_date})\n\n"
            for record in planner_data:
                result_md += f"### 🗓️ {record['planner_date']} (기상: {record['start_arrange']}, 취침: {record['day_end_time']}, 집중시간대: {record['focus_time_zone']})\n"
                matched_tasks = [t for t in tasks_data if t["record_id"] == record["id"]]
                if not matched_tasks:
                    result_md += "- 등록된 세부 작업이 없습니다.\n\n"
                    continue
                for task in matched_tasks:
                    status_emoji = "✅" if task.get("status") == "DONE" else "⏳"
                    urgent_badge = "🚨 [긴급]" if task.get("is_urgent") else ""
                    result_md += f"- {status_emoji} {urgent_badge} **{task.get('title', '제목 없음')}**\n"
                    result_md += f"  - 시간: {task.get('start_at', '미정')} ~ {task.get('end_at', '미정')}\n"
                result_md += "\n"
            return result_md
    except Exception as e:
        return f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"

from app.llm.get_gemini_client_v2 import get_gemini_client

@mcp.tool()
@logfire.instrument("mcp.tool.search_tasks_by_similarity")
async def search_tasks_by_similarity(
    user_id: int, 
    query: str,
    top_k: int = 5
) -> str:
    """사용자의 과거 태스크 중 입력된 텍스트(query)와 의미적으로 가장 유사한 기록을 검색합니다."""
    try:
        gemini_client = get_gemini_client()
        # Google-Genai usage
        from google.genai import types
        def _do_embed():
            return gemini_client.client.models.embed_content(
                model="text-embedding-004",
                contents=query,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
            )
        embed_response = await asyncio.to_thread(_do_embed)
        embedding_vector = embed_response.embeddings[0].values

        async with AsyncSessionLocal() as session:
            # RPC match_record_tasks 호출 (PostgreSQL 함수 직접 실행)
            # match_record_tasks(p_user_id, query_embedding, match_count)
            similarity_query = text("""
                SELECT * FROM match_record_tasks(
                    :user_id, 
                    :embedding::vector, 
                    :top_k
                )
            """)
            result = await session.execute(similarity_query, {
                "user_id": user_id,
                "embedding": embedding_vector,
                "top_k": top_k
            })
            tasks_data = [dict(row._mapping) for row in result]
            
            if not tasks_data:
                return "유사한 태스크를 찾을 수 없습니다."
                
            result_md = "## 🔍 의미 체계 기반(Semantic) 유사 스케줄 검색 결과\n\n"
            for idx, task in enumerate(tasks_data, 1):
                score = task.get("similarity", 0.0)
                status_emoji = "✅" if task.get("status") == "DONE" else "⏳"
                result_md += f"### {idx}. {status_emoji} **{task.get('title', '제목 없음')}** (유사도: {score:.3f})\n"
                result_md += f"- **실행일**: {task.get('planner_date')} ({task.get('start_at')} ~ {task.get('end_at')})\n\n"
            return result_md
    except Exception as e:
        logfire.error(f"유사도 검색 중 에러 발생: {e}")
        return f"유사도 검색 중 오류가 발생했습니다: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
