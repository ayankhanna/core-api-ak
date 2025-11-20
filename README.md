# Core API

FastAPI backend for the productivity app.

## Quick Start

```bash
cd core-api
make start
```

**That's it!** The virtual environment auto-activates and the server starts.

API runs at `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

## Setup

### First Time Setup

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Then edit .env with your Supabase credentials
```

### Environment Variables

Create a `.env` file:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
API_ENV=development
```

## Project Structure

```
core-api/
├── api/
│   ├── index.py          # Main FastAPI app
│   ├── config.py         # Settings
│   ├── routers/          # HTTP endpoints (routing only)
│   │   ├── auth.py       # Auth endpoints
│   │   ├── tasks.py      # Task endpoints
│   │   └── calendar.py   # Calendar endpoints
│   └── services/         # Business logic (functional code)
│       ├── auth.py       # Auth operations
│       ├── tasks.py      # Task operations
│       └── calendar.py   # Calendar operations
├── lib/
│   └── supabase_client.py # Supabase client
├── tests/
├── requirements.txt
├── vercel.json
└── HOW_TO_START.md       # Simple startup guide
```

### Architecture

- **routers/**: HTTP layer - handles requests/responses, validation, HTTP status codes
- **services/**: Business logic layer - all functional operations, database interactions
- **lib/**: Shared utilities and clients

When adding new features:
1. Create service class in `api/services/` with business logic
2. Create router in `api/routers/` that calls the service
3. Register router in `api/index.py`

## Available Endpoints

### Core
- `GET /` - Health check
- `GET /api/health` - Detailed health status

### Authentication
- `POST /auth/users` - Create user
- `POST /auth/oauth-connections` - Store OAuth tokens
- `GET /auth/oauth-connections/{user_id}` - Get user connections

### Calendar
- `GET /api/calendar/events` - Get calendar events
- `POST /api/calendar/sync` - Sync from Google Calendar

### Tasks
- `GET /api/tasks/` - List tasks
- `POST /api/tasks/` - Create task
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task

## Development

```bash
# Run tests
pytest

# Run with auto-reload
python dev.py

# View logs
tail -f logs/api.log
```

## Deployment

Deploy to Vercel:

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

Set environment variables in Vercel dashboard:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

## Tech Stack

- **FastAPI** - Modern Python web framework
- **Supabase** - PostgreSQL database + auth
- **Pydantic** - Data validation
- **Mangum** - ASGI adapter for serverless
