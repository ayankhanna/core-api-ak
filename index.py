"""
Vercel Serverless Function - Root Entry Point
This file MUST be at the project root for Vercel to find it
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fastapi import FastAPI
    from mangum import Mangum
    
    app = FastAPI()
    
    @app.get("/")
    def root():
        return {"status": "ok", "message": "Minimal FastAPI works on Vercel!"}
    
    @app.get("/api/health")
    def health():
        return {"status": "healthy"}
    
    # Vercel handler
    handler = Mangum(app, lifespan="off")
    
except Exception as e:
    import traceback
    print(f"ERROR: {e}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    raise

