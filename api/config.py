"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App metadata
    app_name: str = "Core Productivity API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # CORS settings - Allow all origins by default, specific ones for security
    allowed_origins: List[str] = ["*"]
    
    # Supabase settings (optional - endpoints will fail gracefully if missing)
    supabase_url: str = ""
    supabase_anon_key: str = ""
    
    # Google OAuth settings (optional - will fail gracefully if missing)
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # Environment
    api_env: str = "development"
    
    class Config:
        # Don't require .env file (for Vercel deployment)
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


# Initialize settings with error handling
try:
    settings = Settings()
except Exception as e:
    print(f"Warning: Could not load settings from environment: {e}")
    # Create minimal fallback settings
    settings = Settings(
        app_name="Core Productivity API",
        app_version="1.0.0",
        debug=False,
        allowed_origins=["*"],
        api_env=os.getenv("VERCEL_ENV", "development")
    )
