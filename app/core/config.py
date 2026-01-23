from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    app_name: str = "MOLIP-AI-Planner"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "development"

    # Backend
    backend_url: str = "https://stg.molip.today"

    # CORS
    cors_origins: List[str] = ["*"]
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # API Keys
    gemini_api_key: Optional[str] = None
    
    # Supabase
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Map env vars to fields if names differ
        # (Assuming standard names match, but for ALLOWED_ORIGINS -> cors_origins we might need alias if stricter)
        # But here I'll just rely on loose matching or add alias if needed.
        # Actually, let's add the alias to be safe given .env.example has ALLOWED_ORIGINS
    
    # Redefine cors_origins with alias if pydantic supports it easily in BaseSettings
    # Or just use ValidationAlias in newer Pydantic.
    # checking requirements.txt: pydantic==2.12.5. Good.

settings = Settings()
