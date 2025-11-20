import sys
import os

# Add error logging
def log_error(msg):
    """Log errors to stdout so they appear in Vercel logs"""
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)
    print(f"[ERROR] {msg}", flush=True)

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from mangum import Mangum
    from datetime import datetime
    
    log_error("Successfully imported base dependencies")
    
    # Import config with error handling
    try:
        from api.config import settings
        log_error("Successfully loaded config")
    except Exception as e:
        log_error(f"Error loading config: {e}")
        # Create a minimal fallback settings object
        class FallbackSettings:
            app_name = "Core Productivity API"
            app_version = "1.0.0"
            debug = False
            allowed_origins = ["*"]
        settings = FallbackSettings()
        log_error("Using fallback settings")
    
    # Create app
    app = FastAPI(
        title=settings.app_name,
        description="FastAPI backend for the all-in-one productivity app",
        version=settings.app_version,
        debug=settings.debug
    )
    
    log_error("FastAPI app created")
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    log_error("CORS middleware added")
    
    # Import routers with error handling - do this AFTER app creation
    routers_loaded = False
    router_errors = []
    
    try:
        from api.routers import tasks, auth, calendar, email, webhooks, cron
        
        # Try to include each router individually
        for router_name, router_module in [
            ("auth", auth),
            ("tasks", tasks),
            ("calendar", calendar),
            ("email", email),
            ("webhooks", webhooks),
            ("cron", cron),
        ]:
            try:
                app.include_router(router_module.router)
                log_error(f"✓ Loaded {router_name} router")
            except Exception as e:
                error_msg = f"✗ Failed to load {router_name} router: {e}"
                log_error(error_msg)
                router_errors.append(error_msg)
        
        routers_loaded = True
        log_error("All routers processed")
        
    except Exception as e:
        error_msg = f"Error importing routers: {e}"
        log_error(error_msg)
        router_errors.append(error_msg)
    
    @app.get("/")
    async def root():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "message": "Core Productivity API is running",
            "version": settings.app_name if hasattr(settings, 'app_version') else "1.0.0",
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
    
    log_error("Routes registered successfully")
    
    # Vercel handler - this is the entry point
    handler = Mangum(app, lifespan="off")
    
    log_error("Mangum handler created successfully")

except Exception as e:
    log_error(f"CRITICAL ERROR during module initialization: {e}")
    import traceback
    log_error(f"Traceback: {traceback.format_exc()}")
    
    # Create a minimal emergency handler
    from fastapi import FastAPI
    from mangum import Mangum
    
    emergency_app = FastAPI()
    
    @emergency_app.get("/")
    @emergency_app.get("/api/health")
    async def emergency_health():
        return {
            "status": "error",
            "message": f"API failed to initialize: {str(e)}"
        }
    
    handler = Mangum(emergency_app, lifespan="off")

