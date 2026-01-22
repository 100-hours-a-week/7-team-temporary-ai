"""
Application Configuration

환경 변수 로드 및 애플리케이션 설정 관리
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    애플리케이션 설정

    .env 파일에서 환경 변수를 자동으로 로드합니다.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "MOLIP-AI-Planner"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"  # development, staging, production

    # Backend
    backend_url: str = "https://stg.molip.today"

    # CORS
    allowed_origins: str = "https://stg.molip.today"

    # API Keys (향후 AI 로직 구현 시 사용)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # GEMINI TEST용

    # Database (향후 개인화 데이터 저장 시 사용)
    database_url: Optional[str] = None

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> List[str]:
        """CORS allowed origins를 리스트로 변환"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """프로덕션 환경 여부"""
        return self.environment.lower() == "production"

    @property
    def is_staging(self) -> bool:
        """스테이징 환경 여부"""
        return self.environment.lower() == "staging"

    @property
    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.environment.lower() == "development"


# 싱글톤 인스턴스
settings = Settings()
