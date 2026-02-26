import asyncio
import logging
from datetime import datetime, timedelta

import logfire
from google.genai import types
from app.db.supabase_client import get_supabase_client
from app.llm.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

async def sync_task_embeddings():
    """
    최대 8일 전의 USER_FINAL planner_records의 태스크들을 조회하여
    combined_embedding_text가 NULL인 경우 임베딩 값을 채워 넣습니다.
    (fastapi lifespan 스케줄러에서 매주 월요일 새벽 호출)
    """
    with logfire.span("Sync Task Embeddings") as span:
        try:
            supabase = get_supabase_client()
            gemini_client = get_gemini_client()
            
            # 1. 최대 8일 전부터 현재까지 필터링 (MCP 로직 동일 방식 적용)
            now = datetime.now()
            start_date = (now - timedelta(days=8)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            
            logger.info(f"[Embedding Service] Scanning records between {start_date} and {end_date} (up to 8 days)")
            span.set_attribute("search.start_date", start_date)
            span.set_attribute("search.end_date", end_date)
            
            # planner_records 테이블에서 USER_FINAL이고 plan_date가 지난 8일 사이인 레코드 검색
            response = supabase.table("planner_records")\
                .select("id")\
                .eq("record_type", "USER_FINAL")\
                .gte("plan_date", start_date)\
                .lte("plan_date", end_date)\
                .execute()
                
            records = response.data
            if not records:
                logger.info("[Embedding Service] No USER_FINAL records found in the last 8 days.")
                return
                
            record_ids = [r["id"] for r in records]
            
            # 2. record_tasks에서 해당하는 task들 조회 
            # (assignment_status == ASSIGNED, combined_embedding_text IS NULL)
            tasks_response = supabase.table("record_tasks")\
                .select("id, title")\
                .in_("record_id", record_ids)\
                .eq("assignment_status", "ASSIGNED")\
                .is_("combined_embedding_text", "null")\
                .execute()
                
            tasks = tasks_response.data
            if not tasks:
                logger.info("[Embedding Service] No tasks require embedding updates.")
                span.set_attribute("status", "No tasks to embed")
                return
                
            logger.info(f"[Embedding Service] Found {len(tasks)} tasks to embed.")
            span.set_attribute("tasks.found", len(tasks))
            
            # 3. 각 task에 대해 임베딩 생성 및 DB 업데이트
            updated_count = 0
            
            for task in tasks:
                title = task.get("title")
                if not title:
                    continue
                    
                try:
                    # Gemini 임베딩 API 호출 (백그라운드 스레드에서 차단 방지)
                    def _do_embed():
                        return gemini_client.client.models.embed_content(
                            model="gemini-embedding-001",
                            contents=title,
                            config=types.EmbedContentConfig(
                                task_type="SEMANTIC_SIMILARITY", 
                                output_dimensionality=768
                            )
                        )
                    
                    embed_result = await asyncio.to_thread(_do_embed)
                    
                    if embed_result.embeddings and len(embed_result.embeddings) > 0:
                        embedding_vector = embed_result.embeddings[0].values
                        
                        # DB 업데이트 (vector 자료형에 리스트 형태 전달)
                        supabase.table("record_tasks")\
                            .update({"combined_embedding_text": embedding_vector})\
                            .eq("id", task["id"])\
                            .execute()
                        
                        updated_count += 1
                        
                        # Rate limit 방지를 위해 짧은 대기
                        await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"[Embedding Service] Failed to embed task {task['id']}: {e}")
                    logfire.error(f"Failed to embed task {task['id']}: {e}")
                        
            logger.info(f"[Embedding Service] Successfully updated embeddings for {updated_count} tasks.")
            span.set_attribute("tasks.updated", updated_count)
            span.set_attribute("status", f"Successfully processed {updated_count} out of {len(tasks)} tasks")
            
        except Exception as e:
            logger.error(f"[Embedding Service] Sync process failed: {e}")
            logfire.error(f"Sync process failed: {e}")
            span.record_exception(e)
            raise e
