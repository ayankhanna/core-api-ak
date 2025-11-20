#!/usr/bin/env python3
"""
Test script to verify all imports work
Run this locally before deploying to Vercel
"""
import sys
import os

print("🧪 Testing imports locally...")
print(f"Python: {sys.version}")
print(f"CWD: {os.getcwd()}")

try:
    print("\n1️⃣ Testing api.index import...")
    from api.index import handler, app
    print("   ✅ api.index imported successfully")
    print(f"   ✅ handler: {handler}")
    print(f"   ✅ app: {app}")
    
    print("\n2️⃣ Testing routes...")
    print(f"   Routes: {[route.path for route in app.routes]}")
    
    print("\n3️⃣ Testing config...")
    from api.config import settings
    print(f"   ✅ App name: {settings.app_name}")
    print(f"   ✅ Version: {settings.app_version}")
    print(f"   ✅ Environment: {settings.api_env}")
    print(f"   ✅ Allowed origins: {settings.get_allowed_origins}")
    
    print("\n4️⃣ Testing routers...")
    from api.routers import auth, tasks, calendar, email
    print(f"   ✅ Auth router: {auth.router.prefix}")
    print(f"   ✅ Tasks router: {tasks.router.prefix}")
    print(f"   ✅ Calendar router: {calendar.router.prefix}")
    print(f"   ✅ Email router: {email.router.prefix}")
    
    print("\n✅ All imports successful!")
    print("\n🚀 Ready to deploy to Vercel!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Import failed!")
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

