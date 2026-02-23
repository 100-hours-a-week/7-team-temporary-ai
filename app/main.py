"""
MOLIP AI Server - Main Application

FastAPI 애플리케이션 진입점
"""

import logging
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# .env 파일 로드
load_dotenv()

from app.core.config import settings
from app.api import v1
import logfire

# Logfire 설정 (관측성)
logfire.configure(token=settings.logfire_token, send_to_logfire='if-token-present')

VERSION = "26.02.10 - V2 runpod 원격 구동 & Lifespan 일정 시간 작업 반복 테스트"

# 로깅 설정
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING, # 지정한 디버그 모드
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # 날짜, 이름, 레벨, 메세지
)
logger = logging.getLogger(__name__)


# 스케줄러 작업 정의
def log_every_5_minutes():
    """매 5분마다 실행되는 작업"""
    message = "⏰ 5분 플래그 생성"
    logger.info(message)
    logfire.info(message)


def log_hourly_specific_times():
    """매 시간 특정 분에 실행되는 작업"""
    message = "⏰ 매 시간 특정 분 플래그 생성 (03, 13, 27, 37, 41, 48, 56분)"
    logger.info(message)
    logfire.info(message)


# Lifespan Context Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    logger.info(f"🚀 Starting {settings.app_name}")
    logger.info(f"📍 Backend URL: {settings.backend_url}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    logger.info(f"🌐 CORS origins: {settings.cors_origins}")

    # 스케줄러 설정 및 시작
    scheduler = AsyncIOScheduler()
    
    # 1. 매 5분 마다
    scheduler.add_job(
        log_every_5_minutes, 
        IntervalTrigger(minutes=5), 
        id="every_5_mins", 
        replace_existing=True
    )
    
    # 2. 매 시간 특정 분 (Asia/Seoul 기준)
    scheduler.add_job(
        log_hourly_specific_times, 
        CronTrigger(
            minute='3,13,27,37,41,48,56', 
            hour='0-23', 
            timezone=ZoneInfo("Asia/Seoul")
        ), 
        id="hourly_specific", 
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    yield
    
    # 종료 시 실행
    logger.info(f"🛑 Shutting down {settings.app_name}")
    scheduler.shutdown()
    logger.info("zz Scheduler shut down")

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.app_name, # 지정한 애플리케이션 이름
    description="MOLIP AI 기능 서버",
    version=VERSION,
    debug=settings.debug,
    lifespan=lifespan,
)

# Logfire FastAPI Instrumentation
logfire.instrument_fastapi(app)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins, # 지정한 모든 도메인 접근 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
## 외부 파일에 정의된 API 경로들을 앱에 포함
app.include_router(v1.router, prefix="/ai/v1") # v1 통합 라우터 등록

# Health Check 엔드포인트
## 서버가 정상적으로 실행 중인지 확인
@app.get("/health", tags=["Health"])
async def health_check():
    """
    서버 상태 확인

    Returns:
        dict: 서버 상태 정보
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": VERSION,
        "debug": settings.debug,
    }


# Root 엔드포인트
## 루트 경로에 접속했을 때 기본 정보를 반환
@app.get("/", tags=["Root"])
async def root():
    """
    API 루트

    Returns:
        dict: API 기본 정보
    """
    return {
        "message": "MOLIP AI Server",
        "docs": "/docs",
        "health": "/health",
    }



# 애플리케이션 실행
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", # 애플리케이션 진입점
        host=settings.host,
        port=settings.port,
        reload=settings.debug, # 디버그 모드일 경우 코드가 수정될 때마다 서버 자동 재시작
    )
