import sys
import os

# Add the project root directory to sys.path
# This ensures that 'api' and 'lib' modules can be imported correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from datetime import datetime

from api.config import settings
from api.routers import tasks, auth, calendar, email

app = FastAPI(
    title=settings.app_name,
    description="FastAPI backend for the all-in-one productivity app",
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(email.router)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Core Productivity API is running",
        "version": settings.app_version
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "core-api",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# Vercel handler
handler = Mangum(app)

