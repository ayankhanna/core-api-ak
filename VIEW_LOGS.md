# How to View API Logs

## Where Are the Logs?

API logs appear **in your terminal** where you run `make start`.

## Step-by-Step

### 1. Open a Terminal for the API

```bash
cd /Users/ark/Documents/10x/core-workspace/core-api
```

### 2. Start the API

```bash
make start
```

You'll see:
```
🚀 Starting Core API...
INFO:     Will watch for changes in these directories: ['/Users/ark/Documents/10x/core-workspace/core-api']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 3. Watch for Requests

When someone hits your API, you'll see logs like:

```
INFO:     127.0.0.1:52134 - "POST /auth/complete-oauth HTTP/1.1" 200 OK
=== COMPLETE OAUTH FLOW START ===
User ID: 47102dcd-b482-4d2d-8a5e-ba25b2c554a7
Email: ayan@buzzedapp.com
Name: Ayan Khanna
Provider: google
Has access token: True
Has refresh token: True
✅ OAuth flow completed successfully
=== COMPLETE OAUTH FLOW END ===
```

### 4. Watch for Errors

If something fails, you'll see:

```
❌ Error in complete_oauth_flow: ...
Error type: ValueError
Traceback: ...
```

## Multiple Terminals Setup

You should have **TWO terminals open**:

### Terminal 1: Backend API
```bash
cd core-api
make start
```
Shows: API request logs

### Terminal 2: Frontend Dev Server
```bash
cd core-web
npm run local
```
Shows: Vite dev server logs

## Common Log Messages

### Successful User Creation
```
INFO:     127.0.0.1:52134 - "POST /auth/complete-oauth HTTP/1.1" 200 OK
=== COMPLETE OAUTH FLOW START ===
User ID: xxx
Email: xxx@example.com
✅ OAuth flow completed successfully
```

### CORS Preflight (Normal)
```
INFO:     127.0.0.1:52134 - "OPTIONS /auth/complete-oauth HTTP/1.1" 200 OK
```

### Database Error
```
❌ Error in complete_oauth_flow: ...
psycopg2.errors.UniqueViolation: duplicate key value...
```

### Network/Connection Error
```
❌ Error in complete_oauth_flow: ...
requests.exceptions.ConnectionError: ...
```

## Debugging Tips

### Increase Log Verbosity

Edit `core-api/api/index.py` and add:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### View Full Request Body

Add to any router endpoint:

```python
logger.info(f"Request body: {request.dict()}")
```

### Check Database Queries

Add to service methods:

```python
logger.info(f"Querying: {query}")
logger.info(f"Result: {result.data}")
```

## Viewing Logs in Production

### Vercel Logs

```bash
cd core-api
vercel logs
```

### Filter by Function

```bash
vercel logs --output json | grep "POST /auth"
```

## Log Locations

- **Local Dev**: Terminal output (ephemeral)
- **Production (Vercel)**: `vercel logs` command
- **Custom**: Add file logging if needed

## Need More Logs?

### Add Logging to Any File

```python
import logging

logger = logging.getLogger(__name__)

# In your code:
logger.info("Something happened")
logger.warning("Something might be wrong")
logger.error("Something failed")
logger.debug("Detailed debugging info")
```

### Example: Add Logging to Service

```python
# In api/services/auth.py

def complete_oauth_flow(oauth_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"Creating user: {oauth_data.get('email')}")
    
    # ... code ...
    
    logger.info(f"User created successfully")
    return result
```

## Quick Reference

| What | Where | Command |
|------|-------|---------|
| **API Logs** | Terminal 1 | `make start` |
| **Frontend Logs** | Terminal 2 | `npm run local` |
| **Browser Console** | Chrome DevTools | F12 → Console tab |
| **Network Requests** | Chrome DevTools | F12 → Network tab |
| **Vercel Logs** | CLI | `vercel logs` |

---

**TL;DR**: Just look at the terminal where you ran `make start` - that's where all API logs appear! 🎯

