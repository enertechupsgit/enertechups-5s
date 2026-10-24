from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    APP_NAME: str = "Enertech 5S Enterprise API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database: Defaults to SQLite for local development; switch to PostgreSQL/Supabase via env
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./digi5s.db")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-digi5s-industrial-key-2026")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8081",
        "http://127.0.0.1:5173"
    ]
    
    # Supabase / S3 (optional if using cloud storage)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "digi5s-evidence")

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
