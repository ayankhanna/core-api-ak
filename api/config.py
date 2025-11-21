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
    supabase_service_role_key: str = ""  # Service role key for cron jobs and admin operations
    
    # Google OAuth settings (required for Google Calendar sync)
    google_client_id: str = ""
    google_client_secret: str = ""
    
    # Google Cloud Project settings (for push notifications)
    google_cloud_project_id: str = ""
    
    # Webhook URLs (set in production)
    webhook_base_url: str = "http://localhost:8000"  # Change to production URL
    
    # Cron job authentication
    cron_secret: str = ""  # Secret for authenticating cron job requests
    
    # Environment
    api_env: str = "development"
    
    class Config:
        # Load from .env file for local development
        # In production (Vercel), environment variables are set directly
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


# Initialize settings - will load from environment variables
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"❌ ERROR loading settings: {e}", file=sys.stderr, flush=True)
    import traceback
    traceback.print_exc(file=sys.stderr)
    # Re-raise to fail fast
    raise
