from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from datetime import datetime
import os

# Import config with error handling
try:
    from api.config import settings
except Exception as e:
    print(f"Error loading config: {e}")
    # Create a minimal fallback settings object
    class FallbackSettings:
        app_name = "Core Productivity API"
        app_version = "1.0.0"
        debug = False
        allowed_origins = ["*"]  # Allow all origins in fallback mode
    settings = FallbackSettings()

# Import routers with error handling
try:
    from api.routers import tasks, auth, calendar, email, webhooks, cron
    routers_loaded = True
except Exception as e:
    print(f"Error loading routers: {e}")
    routers_loaded = False

app = FastAPI(
    title=settings.app_name,
    description="FastAPI backend for the all-in-one productivity app",
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers only if they loaded successfully
if routers_loaded:
    try:
        app.include_router(auth.router)
        app.include_router(tasks.router)
        app.include_router(calendar.router)
        app.include_router(email.router)
        app.include_router(webhooks.router)
        app.include_router(cron.router)
    except Exception as e:
        print(f"Error including routers: {e}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Core Productivity API is running",
        "version": settings.app_version,
        "environment": os.getenv("VERCEL_ENV", "unknown")
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "core-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "routers_loaded": routers_loaded
    }

# Vercel handler - this is the entry point
handler = Mangum(app, lifespan="off")

