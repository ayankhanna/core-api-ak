import traceback
import sys

# Track import progress for debugging
print("=" * 50, file=sys.stderr)
print("🔍 Starting import process...", file=sys.stderr)

try:
    print("📦 Importing FastAPI...", file=sys.stderr)
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ FastAPI imported", file=sys.stderr)
    
    print("📦 Importing Mangum...", file=sys.stderr)
    from mangum import Mangum
    print("✅ Mangum imported", file=sys.stderr)
    
    print("📦 Importing datetime...", file=sys.stderr)
    from datetime import datetime
    print("✅ datetime imported", file=sys.stderr)
    
    print("📦 Importing config...", file=sys.stderr)
    from api.config import settings
    print("✅ Config imported", file=sys.stderr)
    
    print("📦 Importing routers...", file=sys.stderr)
    from api.routers import tasks, auth, calendar, email
    print("✅ Routers imported", file=sys.stderr)

    print("🏗️  Creating FastAPI app...", file=sys.stderr)
    app = FastAPI(
        title=settings.app_name,
        description="FastAPI backend for the all-in-one productivity app",
        version=settings.app_version,
        debug=settings.debug
    )
    print("✅ FastAPI app created", file=sys.stderr)

    # Configure CORS for Next.js frontend
    # Note: "https://*.vercel.app" patterns need to be handled with allow_origin_regex
    print("🔧 Configuring CORS...", file=sys.stderr)
    allowed_origins_list = [
        origin for origin in settings.allowed_origins 
        if not origin.startswith("https://*.vercel.app")
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins_list,
        allow_origin_regex=r"https://.*\.vercel\.app",  # Handles *.vercel.app pattern
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("✅ CORS configured", file=sys.stderr)

    # Include routers
    print("🔧 Including routers...", file=sys.stderr)
    app.include_router(auth.router)
    app.include_router(tasks.router)
    app.include_router(calendar.router)
    app.include_router(email.router)
    print("✅ Routers included", file=sys.stderr)

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

    # Vercel handler - MUST be at module level
    print("🎯 Creating Mangum handler...", file=sys.stderr)
    handler = Mangum(app)
    print("✅ Handler created successfully!", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

except Exception as e:
    print("=" * 50, file=sys.stderr)
    print(f"❌ ERROR DURING IMPORT: {type(e).__name__}", file=sys.stderr)
    print(f"❌ Error message: {str(e)}", file=sys.stderr)
    print("❌ Full traceback:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    
    # Create a fallback app that shows the error
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    from mangum import Mangum
    
    app = FastAPI()
    error_details = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "traceback": traceback.format_exc().split("\n")
    }
    
    @app.get("/{full_path:path}")
    async def error_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Failed to initialize API",
                **error_details
            }
        )
    
    handler = Mangum(app)
    print("⚠️  Created fallback error handler", file=sys.stderr)
