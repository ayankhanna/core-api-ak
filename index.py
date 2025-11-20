"""
Root-level handler for Vercel deployment
This file is at the root so Vercel can easily find and execute it
"""
print("Loading root index.py...", flush=True)

try:
    # Import the handler from api/index.py
    from api.index import handler, app
    print("✓ Successfully imported handler from api.index", flush=True)
except Exception as e:
    print(f"✗ Error importing from api.index: {e}", flush=True)
    import traceback
    traceback.print_exc()
    
    # Create emergency fallback
    from fastapi import FastAPI
    from mangum import Mangum
    
    app = FastAPI()
    
    @app.get("/")
    def emergency():
        return {
            "status": "error",
            "message": f"Failed to load main app: {str(e)}"
        }
    
    handler = Mangum(app, lifespan="off")

print("✓ Root index.py loaded successfully", flush=True)

