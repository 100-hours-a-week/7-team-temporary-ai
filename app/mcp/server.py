import asyncio
import os
import json
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP
from app.db.supabase_client import get_supabase_client
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
    end_date: Optional[str] = None, 
    category: Optional[str] = None
) -> str:
    """
    사용자의 과거 일정(플래너) 기록을 특정 날짜 범위로 검색합니다.
    
    Args:
        user_id: 조회할 사용자의 고유 ID (예: 777777)
        start_date: 검색 시작 날짜 (YYYY-MM-DD 형식)
        end_date: 검색 종료 날짜 (YYYY-MM-DD 형식, 제공되지 않으면 오늘 날짜 사용)
        category: 선택적 카테고리 필터링 (미구현시 무시됨)
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    client = get_supabase_client()
    
    try:
        # 1. planner_records 조회 (record_type이 'USER_FINAL'인 것만, 지정된 날짜 범위 내)
        response = client.table("planner_records") \
            .select("id, start_arrange, day_end_time, focus_time_zone, planner_date") \
            .eq("user_id", user_id) \
            .eq("record_type", "USER_FINAL") \
            .gte("planner_date", start_date) \
            .lte("planner_date", end_date) \
            .execute()
            
        planner_data = response.data
        if not planner_data:
            return f"[{start_date} ~ {end_date}] 기간 동안 완료된 플래너 기록이 없습니다."

        record_ids = [record["id"] for record in planner_data]
        
        # 2. planner_records의 id (record_id)를 사용하여 관련된 record_tasks를 조회
        tasks_response = client.table("record_tasks") \
            .select("*") \
            .in_("record_id", record_ids) \
            .eq("assignment_status", "ASSIGNED") \
            .execute()
            
        tasks_data = tasks_response.data
        
        # 3. 데이터 조립 및 Markdown 포맷팅
        result_md = f"## 📅 일정 검색 결과 ({start_date} ~ {end_date})\n\n"
        result_md += "> **메타데이터 가이드**\n"
        result_md += "> - **status**: `TODO`(미완료) / `DONE`(완료)\n"
        result_md += "> - **focus_level**: 1~10 (작업 몰입도/피로도)\n"
        result_md += "> - **is_urgent**: True/False (긴급 여부)\n"
        result_md += "> - **focus_time_zone**: 사용자의 의도된 집중 시간대\n\n"
        
        for record in planner_data:
            result_md += f"### 🗓️ {record['planner_date']} (기상: {record['start_arrange']}, 취침: {record['day_end_time']}, 집중시간대: {record['focus_time_zone']})\n"
            
            # 현재 레코드에 속한 작업들 필터링
            matched_tasks = [t for t in tasks_data if t["record_id"] == record["id"]]
            
            if not matched_tasks:
                result_md += "- 등록된 세부 작업이 없습니다.\n\n"
                continue
                
            for task in matched_tasks:
                # 상태 이모지
                status_emoji = "✅" if task.get("status") == "DONE" else "⏳"
                urgent_badge = "🚨 [긴급]" if task.get("is_urgent") else ""
                focus_lvl = task.get("focus_level", "N/A")
                
                result_md += f"- {status_emoji} {urgent_badge} **{task.get('title', '제목 없음')}**\n"
                result_md += f"  - 시간: {task.get('start_at', '미정')} ~ {task.get('end_at', '미정')}\n"
                result_md += f"  - 몰입요구도: {focus_lvl}/10, 상태: {task.get('status', 'TODO')}\n"
            
            result_md += "\n"
            
        return result_md
        
    except Exception as e:
        return f"데이터베이스 조회 중 오류가 발생했습니다: {str(e)}"

@mcp.tool()
@logfire.instrument("mcp.tool.search_tasks_by_similarity")
async def search_tasks_by_similarity(
    user_id: int, 
    embedding_vector: List[float], 
    top_k: int = 5
) -> str:
    """
    임베딩 벡터를 사용하여 사용자의 과거 태스크 중 의미적으로 가장 유사한 기록을 검색합니다.
    
    Args:
        user_id: 조회할 사용자의 고유 ID
        embedding_vector: 쿼리 문장을 임베딩한 768차원 Float 배열
        top_k: 반환할 가장 유사한 태스크 개수 (기본값: 5)
    """
    client = get_supabase_client()
    
    try:
        # Supabase RPC(Stored Procedure)를 호출하여 DB 내부(pgvector)에서 코사인 유사도 연산 및 JOIN 수행
        # 파라미터는 p_user_id, query_embedding, match_count
        response = client.rpc(
            "match_record_tasks",
            {
                "p_user_id": user_id,
                "query_embedding": json.dumps(embedding_vector), # 벡터 리스트를 Text로 전송하여 DB에서 변환
                "match_count": top_k
            }
        ).execute()
        
        tasks_data = response.data
        if not tasks_data:
            return "유사한 태스크를 찾을 수 없습니다."
            
        # 출력 Markdown 조립 (검색 메타데이터 가이드라인 적용)
        result_md = "## 🔍 의미 체계 기반(Semantic) 유사 스케줄 검색 결과\n\n"
        result_md += "> **메타데이터 가이드**\n"
        result_md += "> - **`status` (태스크 완료 여부)**\n"
        result_md += ">   - `TODO` : 계획은 했으나 실행하지 못한(완료하지 못한) 일입니다.\n"
        result_md += ">   - `DONE` : 성공적으로 완료한 일입니다.\n"
        result_md += "> - **`focus_level` (집중도 및 중요도)**\n"
        result_md += ">   - 1 ~ 10까지의 정수값으로, 10에 가까울수록 집중도가 매우 필요한 고강도의 태스크를 의미합니다.\n"
        result_md += "> - **`is_urgent` (긴급 여부)**\n"
        result_md += ">   - `False` : 급하지 않은 일.\n"
        result_md += ">   - `True` : 기한이 임박하여 급하게 처리해야 하는 일.\n"
        result_md += "> - **`focus_time_zone` (플래너 정보)**\n"
        result_md += ">   - 사용자가 당일 가장 집중하려 했던 시간대(MORNING, AFTERNOON, NIGHT 등)를 의미합니다.\n\n"
        
        for idx, task in enumerate(tasks_data, 1):
            score = task.get("similarity", 0.0)
            plan_date = task.get("planner_date", "알수없음")
            time_zone = task.get("focus_time_zone", "N/A")
            
            status_emoji = "✅" if task.get("status") == "DONE" else "⏳"
            urgent_badge = "🚨 [긴급]" if task.get("is_urgent") else ""
            focus_lvl = task.get("focus_level", "N/A")
            
            result_md += f"### {idx}. {status_emoji} {urgent_badge} **{task.get('title', '제목 없음')}** (유사도: {score:.3f})\n"
            result_md += f"- **실행일**: {plan_date} (해당일 집중시간대: {time_zone})\n"
            result_md += f"- **진행시간**: {task.get('start_at', '미정')} ~ {task.get('end_at', '미정')}\n"
            result_md += f"- **태스크 속성**: 집중도({focus_lvl}/10), 긴급도({task.get('is_urgent')}), 카테고리({task.get('category', '미지정')}), 완료상태({task.get('status', 'TODO')})\n"
            result_md += "\n"
            
        return result_md
        
    except Exception as e:
        logfire.error(f"유사도 검색 중 에러 발생: {e}")
        return f"데이터베이스 (RPC) 조회 및 유사도 비교 중 오류가 발생했습니다: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')
