import sys
import os

# Add the project root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
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

    # Configure CORS
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
    handler = Mangum(app, lifespan="off")

except Exception as e:
    # Fallback for debugging
    import traceback
    error_msg = str(e)
    trace = traceback.format_exc()
    
    # Print to stderr for Vercel logs
    print(f"STARTUP ERROR: {error_msg}", file=sys.stderr, flush=True)
    print(trace, file=sys.stderr, flush=True)
    
    # Create error app
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from mangum import Mangum
    
    app = FastAPI()

    @app.get("/{path:path}")
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Startup failed",
                "message": error_msg,
                "traceback": trace.split("\n")
            }
        )
    
    handler = Mangum(app, lifespan="off")
