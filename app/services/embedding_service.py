import asyncio
import logging
from datetime import datetime, timedelta

import logfire
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.llm.get_gemini_client_v2 import get_gemini_client

logger = logging.getLogger(__name__)

async def sync_task_embeddings():
    """
    최대 8일 전의 USER_FINAL planner_records의 태스크들을 조회하여
    combined_embedding_text가 NULL인 경우 임베딩 값을 채워 넣습니다.
    """
    with logfire.span("Sync Task Embeddings") as span:
        try:
            gemini_client = get_gemini_client()
            
            now = datetime.now()
            start_date = (now - timedelta(days=8)).date()
            end_date = now.date()
            
            logger.info(f"[Embedding Service] Scanning records between {start_date} and {end_date}")
            
            async with AsyncSessionLocal() as session:
                # 1. USER_FINAL 레코드 ID 조회
                records_query = text("""
                    SELECT id FROM planner_records 
                    WHERE record_type = 'USER_FINAL' 
                      AND planner_date >= :start_date 
                      AND planner_date <= :end_date
                """)
                records_res = await session.execute(records_query, {
                    "start_date": start_date,
                    "end_date": end_date
                })
                record_ids = [row[0] for row in records_res]
                
                if not record_ids:
                    logger.info("[Embedding Service] No USER_FINAL records found.")
                    return
                
                # 2. 임베딩이 필요한 태스크 조회
                tasks_query = text("""
                    SELECT id, title FROM record_tasks 
                    WHERE record_id = ANY(:record_ids) 
                      AND assignment_status = 'ASSIGNED' 
                      AND combined_embedding_text IS NULL
                """)
                tasks_res = await session.execute(tasks_query, {"record_ids": record_ids})
                tasks = [dict(row._mapping) for row in tasks_res]
                
                if not tasks:
                    logger.info("[Embedding Service] No tasks require embedding updates.")
                    return
                
                logger.info(f"[Embedding Service] Found {len(tasks)} tasks to embed.")
                
                # 3. 임베딩 생성 및 업데이트
                updated_count = 0
                for task in tasks:
                    title = task.get("title")
                    if not title: continue
                    
                    try:
                        # Gemini 2.0 SDK (Google-Genai) usage
                        from google.genai import types
                        
                        def _do_embed():
                            return gemini_client.client.models.embed_content(
                                model="text-embedding-004", # Updated to latest
                                contents=title,
                                config=types.EmbedContentConfig(
                                    task_type="RETRIEVAL_QUERY", 
                                    output_dimensionality=768
                                )
                            )
                        
                        embed_result = await asyncio.to_thread(_do_embed)
                        
                        if embed_result.embeddings:
                            embedding_vector = embed_result.embeddings[0].values
                            
                            # SQL Update (pgvector expects [v1, v2, ...])
                            update_query = text("""
                                UPDATE record_tasks 
                                SET combined_embedding_text = :embedding 
                                WHERE id = :id
                            """)
                            await session.execute(update_query, {
                                "embedding": embedding_vector,
                                "id": task["id"]
                            })
                            updated_count += 1
                            await asyncio.sleep(0.05) # Brief pause
                    except Exception as e:
                        logger.error(f"[Embedding Service] Task {task['id']} failed: {e}")
                
                await session.commit()
                logger.info(f"[Embedding Service] Updated {updated_count} embeddings.")
                
        except Exception as e:
            logger.error(f"[Embedding Service] Sync process failed: {e}")
            raise e
