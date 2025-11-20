"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App metadata
    app_name: str = "Core Productivity API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # CORS settings
    allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",  # Vite dev server
        "https://*.vercel.app",
    ]
    
    # Supabase settings
    supabase_url: str = ""
    supabase_anon_key: str = ""
    
    # Google OAuth settings (required for Google Calendar sync)
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # Environment
    api_env: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


settings = Settings()
