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
    ]
    
    # Vercel deployments - set via environment variable
    # e.g., ALLOWED_ORIGINS=https://yourapp.vercel.app,https://yourdomain.com
    allowed_origins_env: str = ""
    
    @property
    def get_allowed_origins(self) -> List[str]:
        """Get combined allowed origins from defaults and environment"""
        origins = self.allowed_origins.copy()
        if self.allowed_origins_env:
            origins.extend([o.strip() for o in self.allowed_origins_env.split(",")])
        return origins
    
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
