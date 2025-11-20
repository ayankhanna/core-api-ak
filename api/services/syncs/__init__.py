"""
Sync services for external providers (Google Calendar, Gmail, etc.)
"""

# Try to import with error handling to prevent crashes
try:
    from .sync_google_calendar import sync_google_calendar
except Exception as e:
    print(f"Warning: Could not import sync_google_calendar: {e}")
    sync_google_calendar = None

try:
    from .sync_gmail import sync_gmail, sync_gmail_incremental
except Exception as e:
    print(f"Warning: Could not import sync_gmail: {e}")
    sync_gmail = None
    sync_gmail_incremental = None

try:
    from .watch_manager import (
        start_gmail_watch,
        start_calendar_watch,
        stop_watch,
        renew_watch,
        get_expiring_subscriptions,
        setup_watches_for_user
    )
except Exception as e:
    print(f"Warning: Could not import watch_manager: {e}")
    start_gmail_watch = None
    start_calendar_watch = None
    stop_watch = None
    renew_watch = None
    get_expiring_subscriptions = None
    setup_watches_for_user = None

__all__ = [
    'sync_google_calendar',
    'sync_gmail',
    'sync_gmail_incremental',
    'start_gmail_watch',
    'start_calendar_watch',
    'stop_watch',
    'renew_watch',
    'get_expiring_subscriptions',
    'setup_watches_for_user'
]
