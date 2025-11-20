# 🚀 FINAL DEPLOYMENT INSTRUCTIONS

## Current State: READY TO DEPLOY

### ✅ What's Working Locally
- ✅ Minimal FastAPI (`index.py`) - 2 routes
- ✅ Full API (`index_full.py`) - 36 routes including auth, tasks, calendar, email
- ✅ All imports working
- ✅ Config loading from environment variables

---

## 🎯 DEPLOYMENT STRATEGY

### Option A: Test Minimal First (RECOMMENDED)

**Current setup - minimal FastAPI to verify Vercel works:**

```bash
# Current files:
# - index.py (minimal - 2 routes)
# - vercel.json (points to index.py)

# Deploy minimal
cd /Users/ark/Documents/10x/core-workspace/core-api
vercel --prod

# Test
curl https://your-deployment.vercel.app/
# Expected: {"status":"ok","message":"Minimal FastAPI works on Vercel!"}
```

**If minimal works, upgrade to full:**
```bash
# Replace minimal with full
mv index.py index_minimal.py
mv index_full.py index.py

# Deploy full API
vercel --prod

# Test
curl https://your-deployment.vercel.app/
# Expected: {"status":"healthy","message":"Core Productivity API is running"}
```

---

### Option B: Deploy Full API Directly (YOLO MODE)

**If you're confident, just deploy the full thing:**

```bash
cd /Users/ark/Documents/10x/core-workspace/core-api

# Replace minimal with full
mv index.py index_minimal.py
mv index_full.py index.py

# Deploy
vercel --prod

# Test all endpoints
curl https://your-deployment.vercel.app/
curl https://your-deployment.vercel.app/api/health
curl https://your-deployment.vercel.app/api/tasks/
```

---

## 📁 File Structure (Current)

```
core-api/
├── index.py              ← Minimal FastAPI (currently deployed)
├── index_full.py         ← Full API (ready to swap in)
├── vercel.json           ← Points to index.py
├── requirements.txt      ← All dependencies
├── api/
│   ├── __init__.py
│   ├── config.py        ← Fixed config (no .env requirement)
│   ├── dependencies.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── tasks.py
│   │   ├── calendar.py
│   │   └── email.py
│   └── services/
│       ├── auth.py
│       ├── tasks.py
│       ├── calendar/
│       ├── email/
│       └── syncs/
└── lib/
    └── supabase_client.py
```

---

## 🔧 Environment Variables (Set in Vercel)

**Go to:** Vercel Dashboard → Project → Settings → Environment Variables

### Required:
```bash
# These have defaults in code but should be set for production
SUPABASE_URL=https://ztnfztpquyvoipttozgz.supabase.co
SUPABASE_ANON_KEY=your_key_here
```

### Optional (for Google features):
```bash
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret

# For production CORS
ALLOWED_ORIGINS_ENV=https://your-frontend.vercel.app,https://yourdomain.com
```

---

## 🧪 Testing After Deployment

### Test Minimal (Current):
```bash
curl https://your-deployment.vercel.app/
# Expected: {"status":"ok","message":"Minimal FastAPI works on Vercel!"}

curl https://your-deployment.vercel.app/api/health
# Expected: {"status":"healthy"}
```

### Test Full (After Swap):
```bash
# Health check
curl https://your-deployment.vercel.app/
# Expected: {"status":"healthy","message":"Core Productivity API is running","version":"1.0.0"}

# API docs (should work)
open https://your-deployment.vercel.app/docs

# Test a protected endpoint (should need auth)
curl https://your-deployment.vercel.app/api/tasks/
# Expected: 401 or auth error

# Test auth endpoint
curl -X POST https://your-deployment.vercel.app/auth/users \
  -H "Content-Type: application/json" \
  -d '{"id":"test","email":"test@test.com"}'
```

---

## 🐛 Troubleshooting

### Issue: Minimal version still 500s

**Check:**
```bash
vercel logs --follow
```

Look for Python errors in stderr.

**Possible causes:**
- Missing `fastapi` or `mangum` in requirements.txt
- Python version incompatibility
- Vercel configuration issue

**Fix:**
```bash
# Verify requirements.txt has:
grep -E "fastapi|mangum" requirements.txt

# Should show:
# fastapi==0.115.0
# mangum==0.18.0
```

---

### Issue: Full version fails but minimal works

**This means your app code has an import error.**

**Check logs:**
```bash
vercel logs

# Look for the STARTUP ERROR message
# It will tell you which import failed
```

**Common issues:**
- Missing dependency in requirements.txt
- Import path issue (api.routers, api.services)
- Config validation error (missing env vars)

---

### Issue: Getting CORS errors

**Set CORS origins in Vercel:**
```bash
# In Vercel dashboard, add:
ALLOWED_ORIGINS_ENV=https://your-frontend.vercel.app
```

Then redeploy:
```bash
vercel --prod
```

---

## ✅ Success Checklist

- [ ] Minimal version deploys without 500 error
- [ ] Can curl the root endpoint and get JSON response
- [ ] Swap to full version
- [ ] Full version deploys successfully
- [ ] All 36 routes are accessible
- [ ] `/docs` shows API documentation
- [ ] Environment variables set in Vercel
- [ ] CORS working with frontend

---

## 🚀 DEPLOY NOW

**Start with minimal:**
```bash
cd /Users/ark/Documents/10x/core-workspace/core-api
vercel --prod
```

**Once it works, upgrade to full:**
```bash
mv index.py index_minimal.py
mv index_full.py index.py
vercel --prod
```

---

## 📊 Key Changes Made

1. **Moved handler to project root** (`index.py` instead of `api/index.py`)
   - Vercel prefers root-level entry points
   
2. **Simplified vercel.json** to bare minimum:
   ```json
   {
     "builds": [{"src": "index.py", "use": "@vercel/python"}],
     "routes": [{"src": "/(.*)", "dest": "index.py"}]
   }
   ```

3. **Fixed api/config.py** - No .env file requirement

4. **Added proper error handling** - Errors print to stderr for Vercel logs

5. **Created incremental deployment strategy** - Test minimal first, then full

---

**You're ready. Deploy the minimal version and let me know if you see the success JSON!** 🎉

