"""
MOLIP AI Server - Main Application

FastAPI 애플리케이션 진입점
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import gemini_test_planners

# 로깅 설정
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI 앱 초기화
app = FastAPI(
    title=settings.app_name,
    description="MOLIP AI 기능 서버 - AI 플래너 생성 및 기타 AI 기능",
    version="0.1.0 (TEST)",
    debug=settings.debug,
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(gemini_test_planners.router)

# Health Check 엔드포인트
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
        "version": "0.1.0 (TEST)",
        "debug": settings.debug,
    }


# Root 엔드포인트
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
