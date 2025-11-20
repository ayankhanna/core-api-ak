from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from datetime import datetime
import os

# Initialize app first
app = FastAPI(
    title="Core Productivity API",
    description="FastAPI backend for the all-in-one productivity app",
    version="1.0.0",
    debug=False
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track router loading
routers_loaded = []
router_errors = []

# Try to load routers - but don't fail if they don't load
try:
    from api.routers import auth
    app.include_router(auth.router)
    routers_loaded.append("auth")
except Exception as e:
    router_errors.append(f"auth: {str(e)}")

try:
    from api.routers import tasks
    app.include_router(tasks.router)
    routers_loaded.append("tasks")
except Exception as e:
    router_errors.append(f"tasks: {str(e)}")

try:
    from api.routers import calendar
    app.include_router(calendar.router)
    routers_loaded.append("calendar")
except Exception as e:
    router_errors.append(f"calendar: {str(e)}")

try:
    from api.routers import email
    app.include_router(email.router)
    routers_loaded.append("email")
except Exception as e:
    router_errors.append(f"email: {str(e)}")

try:
    from api.routers import webhooks
    app.include_router(webhooks.router)
    routers_loaded.append("webhooks")
except Exception as e:
    router_errors.append(f"webhooks: {str(e)}")

try:
    from api.routers import cron
    app.include_router(cron.router)
    routers_loaded.append("cron")
except Exception as e:
    router_errors.append(f"cron: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Core Productivity API is running",
        "version": "1.0.0",
        "environment": os.getenv("VERCEL_ENV", "unknown")
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "core-api",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "routers_loaded": routers_loaded,
        "router_errors": router_errors if router_errors else None,
        "environment": {
            "VERCEL_ENV": os.getenv("VERCEL_ENV"),
            "VERCEL_REGION": os.getenv("VERCEL_REGION"),
            "HAS_SUPABASE_URL": bool(os.getenv("SUPABASE_URL")),
            "HAS_SUPABASE_KEY": bool(os.getenv("SUPABASE_ANON_KEY")),
        }
    }

# Vercel handler - must be at module level
handler = Mangum(app, lifespan="off")

