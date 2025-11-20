#!/usr/bin/env python3
"""
Development server runner for local testing
Run with: python dev.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "index:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )



