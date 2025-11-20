# Vercel Deployment Guide

## Environment Variables Required

Set these environment variables in your Vercel project dashboard (Settings → Environment Variables):

### Required Variables
- `SUPABASE_URL` - Your Supabase project URL (https://your-project.supabase.co)
- `SUPABASE_ANON_KEY` - Your Supabase anonymous/public key

### Optional Variables (for Google integration)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret

### Other Optional Variables
- `API_ENV` - Environment name (default: "development", set to "production" for prod)
- `DEBUG` - Debug mode (default: false)

## Deployment Steps

1. **Set Environment Variables**
   - Go to your Vercel project dashboard
   - Navigate to Settings → Environment Variables
   - Add all required variables listed above

2. **Deploy**
   ```bash
   vercel --prod
   ```

3. **Verify Deployment**
   - Visit `https://your-project.vercel.app/` - should return health status
   - Visit `https://your-project.vercel.app/api/health` - should return detailed health check

## Troubleshooting

### "Serverless function has crashed"
- Check that all required environment variables are set in Vercel dashboard
- Check deployment logs in Vercel dashboard
- Make sure Python version is compatible (3.11 or 3.12)

### CORS Issues
- The app is configured to allow all origins by default
- To restrict origins, modify `api/config.py` and redeploy

### Router/Import Errors
- The app now includes fallback error handling
- Check `/api/health` endpoint to see which routers loaded successfully

## Viewing Logs

See [VIEW_LOGS.md](./VIEW_LOGS.md) for instructions on viewing logs in Vercel.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python dev.py
# or
uvicorn api.index:app --reload --port 8000
```

