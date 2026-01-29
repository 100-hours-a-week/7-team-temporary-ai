from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    app_name: str = "MOLIP-AI-Planner" # 애플리케이션 이름
    debug: bool = True # 개발 모드
    host: str = "0.0.0.0" # 서버 호스트
    port: int = 8000 # 서버 포트
    environment: str = "development" # 환경

    # Backend
    backend_url: str = "https://stg.molip.today" # 백엔드 URL

    # CORS
    cors_origins: List[str] = ["*"] # 모든 도메인 접근 허용
    
    # Logging
    log_level: str = "INFO" # 로그의 상세 수준
    logfire_token: Optional[str] = None # Logfire 토큰

    # 환경 변수에서 콤마로 구분된 문자열이 들어오면 파이썬 리스트 형태로 변환
    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # API Keys
    gemini_api_key: Optional[str] = None # Gemini API 키
    
    # Supabase
    supabase_url: Optional[str] = None # Supabase URL
    supabase_key: Optional[str] = None # Supabase API 키

    class Config:
        env_file = ".env" # 환경 변수 파일
        case_sensitive = False # 대소문자 구분 하지 않음
        extra = "ignore" # Settings 클래스에 정의되지 않은 환경 변수가 있더라고 에러를 내지 않음

#인스턴스 생성
settings = Settings()
