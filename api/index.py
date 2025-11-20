#!/usr/bin/env python3
"""
Vercel Serverless Function Entry Point
"""
import sys
import os
import traceback
import logging

# Configure logging to stdout for Vercel
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

logger.info("🚀 Starting Python serverless function initialization...")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python executable: {sys.executable}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"sys.path: {sys.path}")

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
logger.info(f"Current dir: {current_dir}")
logger.info(f"Project root: {project_root}")

if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"✅ Added project root to sys.path")

try:
    logger.info("📦 Importing FastAPI...")
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    logger.info("✅ FastAPI imported")
    
    logger.info("📦 Importing Mangum...")
    from mangum import Mangum
    logger.info("✅ Mangum imported")
    
    logger.info("📦 Importing datetime...")
    from datetime import datetime
    logger.info("✅ datetime imported")

    logger.info("📦 Importing api.config...")
    from api.config import settings
    logger.info("✅ api.config imported")
    logger.info(f"Settings: app_name={settings.app_name}, debug={settings.debug}")
    
    logger.info("📦 Importing routers...")
    from api.routers import tasks, auth, calendar, email
    logger.info("✅ All routers imported")

    logger.info("🏗️ Creating FastAPI app...")
    app = FastAPI(
        title=settings.app_name,
        description="FastAPI backend for the all-in-one productivity app",
        version=settings.app_version,
        debug=settings.debug
    )
    logger.info("✅ FastAPI app created")

    logger.info("🔐 Configuring CORS...")
    allowed_origins = settings.get_allowed_origins
    logger.info(f"Allowed origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS configured")

    logger.info("🔌 Including routers...")
    app.include_router(auth.router)
    logger.info("  ✅ auth router")
    app.include_router(tasks.router)
    logger.info("  ✅ tasks router")
    app.include_router(calendar.router)
    logger.info("  ✅ calendar router")
    app.include_router(email.router)
    logger.info("  ✅ email router")

    @app.get("/")
    async def root():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "message": "Core Productivity API is running",
            "version": settings.app_version,
            "environment": settings.api_env
        }

    @app.get("/api/health")
    async def health_check():
        """Detailed health check"""
        return {
            "status": "healthy",
            "service": "core-api",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "python_version": sys.version,
            "environment": settings.api_env
        }
    
    @app.get("/debug/info")
    async def debug_info():
        """Debug endpoint to check environment"""
        return {
            "python_version": sys.version,
            "sys_path": sys.path,
            "cwd": os.getcwd(),
            "env_vars": {
                "SUPABASE_URL": settings.supabase_url[:30] + "..." if settings.supabase_url else "NOT SET",
                "GOOGLE_CLIENT_ID": "SET" if settings.google_client_id else "NOT SET",
                "API_ENV": settings.api_env
            }
        }

    logger.info("🔧 Creating Mangum handler...")
    # Vercel handler - must be at module level for Vercel to find it
    handler = Mangum(app, lifespan="off")
    logger.info("✅ Mangum handler created")
    logger.info("🎉 Initialization complete!")

except Exception as e:
    # Fallback app for debugging startup errors
    error_msg = str(e)
    trace = traceback.format_exc()
    
    logger.error("=" * 80)
    logger.error("❌ FATAL ERROR DURING INITIALIZATION")
    logger.error("=" * 80)
    logger.error(f"Error: {error_msg}")
    logger.error(f"Error type: {type(e).__name__}")
    logger.error("Full traceback:")
    logger.error(trace)
    logger.error("=" * 80)
    
    # Print to stderr as well
    print(f"❌ FATAL ERROR: {error_msg}", file=sys.stderr)
    print(trace, file=sys.stderr)
    
    # Create fallback app that shows the error
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    
    app = FastAPI()

    @app.get("/{path:path}")
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Startup failed - check Vercel logs for details",
                "error": error_msg,
                "error_type": type(e).__name__,
                "traceback": trace.split("\n")
            }
        )
    
    # Ensure handler is available even on error
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
    logger.error("⚠️ Created fallback handler")
