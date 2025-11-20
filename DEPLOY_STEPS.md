# 🚀 Vercel Deployment - Step by Step

## What We're Doing

Testing incrementally to find what breaks:

### Step 1: Minimal FastAPI (CURRENT)
- File: `index.py` at root
- Just FastAPI + 2 routes
- **Deploy this first, verify it works**

### Step 2: Add Config
- Import api.config
- Test config loading

### Step 3: Add One Router
- Add just the tasks router
- Verify routing works

### Step 4: Add All Routers
- Add auth, calendar, email
- Full API restored

---

## 🧪 Test Each Step

After each deploy:

```bash
# Deploy
vercel --prod

# Test
curl https://your-deployment.vercel.app/
curl https://your-deployment.vercel.app/api/health

# Check logs
vercel logs --follow
```

---

## 📝 Current State: Step 1

**Files:**
- `index.py` - Minimal FastAPI at root
- `vercel.json` - Points to index.py
- `requirements.txt` - Has all dependencies

**Deploy now:**
```bash
cd /Users/ark/Documents/10x/core-workspace/core-api
vercel --prod
```

**Expected result:**
```json
{"status":"ok","message":"Minimal FastAPI works on Vercel!"}
```

If this works, we'll add the rest incrementally.

