"""
MOLIP AI Server - Main Application

FastAPI 애플리케이션 진입점
"""

import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# .env 파일 로드
load_dotenv()

from app.core.config import settings
from app.api import v1
import logfire

# Logfire 설정 (관측성)
logfire.configure(token=settings.logfire_token, send_to_logfire='if-token-present')

VERSION = "26.02.09 - V1 MVP 구현 완료 & 개인화 AI 엔드포인트 수정"

# 로깅 설정
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING, # 지정한 디버그 모드
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # 날짜, 이름, 레벨, 메세지
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.app_name, # 지정한 애플리케이션 이름
    description="MOLIP AI 기능 서버",
    version=VERSION,
    debug=settings.debug,
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


# 애플리케이션 시작 이벤트
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info(f"🚀 Starting {settings.app_name}")
    logger.info(f"📍 Backend URL: {settings.backend_url}")
    logger.info(f"🔧 Debug mode: {settings.debug}")
    logger.info(f"🌐 CORS origins: {settings.cors_origins}")


# 애플리케이션 종료 이벤트
@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info(f"🛑 Shutting down {settings.app_name}")


# 애플리케이션 실행
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", # 애플리케이션 진입점
        host=settings.host,
        port=settings.port,
        reload=settings.debug, # 디버그 모드일 경우 코드가 수정될 때마다 서버 자동 재시작
    )
