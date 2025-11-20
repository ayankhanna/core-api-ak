"""
Sync services for external providers (Google Calendar, Gmail, etc.)
"""
from .sync_google_calendar import sync_google_calendar
from .sync_gmail import sync_gmail, sync_gmail_incremental, process_gmail_history
from .watch_manager import (
    start_gmail_watch,
    start_calendar_watch,
    stop_gmail_watch,
    stop_calendar_watch,
    renew_watch,
    get_expiring_subscriptions,
    setup_watches_for_user
)

__all__ = [
    'sync_google_calendar',
    'sync_gmail',
    'sync_gmail_incremental',
    'process_gmail_history',
    'start_gmail_watch',
    'start_calendar_watch',
    'stop_gmail_watch',
    'stop_calendar_watch',
    'renew_watch',
    'get_expiring_subscriptions',
    'setup_watches_for_user'
]

