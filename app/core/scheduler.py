import asyncio
import logging
from datetime import datetime, timedelta

from app.services.embedding_service import sync_task_embeddings

logger = logging.getLogger(__name__)

async def run_embedding_scheduler():
    """
    매주 월요일 새벽 4시에 임베딩 동기화 작업을 실행하는 백그라운드 스케줄러
    """
    while True:
        try:
            now = datetime.now()
            
            # 다음 월요일 04:00:00 계산
            # weekday() 0: 월요일, 1: 화요일, 2: 수요일, 3: 목요일, ... 6: 일요일
            days_ahead = 0 - now.weekday()
            
            # 이미 오늘(월요일) 4시가 지났거나, 오늘이 월요일이 아니면 다음 주 월요일로 설정
            if days_ahead <= 0:
                if days_ahead == 0 and (now.hour < 4 or (now.hour == 4 and now.minute == 0)):
                    # 오늘이 월요일이고 아직 4시가 안됨 -> 오늘 4시에 실행
                    days_ahead = 0
                else:
                    # 다음 주 월요일로 
                    days_ahead += 7
            
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(hour=4, minute=0, second=0, microsecond=0)
            
            sleep_seconds = (next_run - now).total_seconds()
            
            logger.info(f"[Scheduler] Next embedding sync will run at {next_run} (in {sleep_seconds} seconds)")
            
            # 다음 실행 시간까지 대기
            await asyncio.sleep(sleep_seconds)
            
            # 실행
            logger.info("[Scheduler] Starting expected weekly embedding sync...")
            await sync_task_embeddings()
            logger.info("[Scheduler] Finished weekly embedding sync.")
            
        except asyncio.CancelledError:
            logger.info("[Scheduler] Embedding scheduler was cancelled.")
            break
        except Exception as e:
            logger.error(f"[Scheduler] Error in embedding scheduler: {e}")
            # 에러 발생 시 1시간 대기 후 다시 시도 (무한 루프 방지)
            await asyncio.sleep(3600)
