"""
FastAPI application for Vercel
Vercel auto-detects and deploys FastAPI apps at index.py
NO vercel.json or Mangum needed!
"""
import sys
import os

# Add project root to path so we can import from api/ and lib/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from api.config import settings
from api.routers import tasks, auth, calendar, email, webhooks, cron, sync

# Create FastAPI app - Vercel will auto-detect this
app = FastAPI(
    title=settings.app_name,
    description="FastAPI backend for the all-in-one productivity app",
    version=settings.app_version,
    debug=settings.debug
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(calendar.router)
app.include_router(email.router)
app.include_router(webhooks.router)
app.include_router(cron.router)
app.include_router(sync.router)

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

