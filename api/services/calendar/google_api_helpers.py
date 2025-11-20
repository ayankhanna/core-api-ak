"""
Google Calendar API helper functions
Shared utilities for interacting with Google Calendar API
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from lib.supabase_client import get_authenticated_supabase_client
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def get_google_calendar_service(user_id: str, user_jwt: str):
    """
    Get an authenticated Google Calendar API service instance
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Tuple of (service, connection_id) or (None, None) if no connection
    """
    try:
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        
        logger.info(f"🔍 Looking for Google connection for user {user_id}")
        
        # Get user's Google OAuth connection
        connection_result = auth_supabase.table('ext_connections')\
            .select('id, access_token, refresh_token, token_expires_at, metadata')\
            .eq('user_id', user_id)\
            .eq('provider', 'google')\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not connection_result.data:
            logger.warning(f"❌ No active Google connection found for user {user_id}")
            logger.info(f"💡 User needs to connect their Google Calendar via OAuth")
            return None, None
        
        connection_data = connection_result.data
        connection_data['user_id'] = user_id
        connection_id = connection_data['id']
        
        logger.info(f"✅ Found Google connection (ID: {connection_id})")
        
        # Get valid access token (refresh if needed)
        access_token = _refresh_google_token_if_needed(connection_data)
        
        if not access_token:
            logger.error(f"❌ Unable to get valid access token for user {user_id}")
            logger.error(f"💡 Token may be expired or invalid. User should re-authenticate.")
            return None, None
        
        logger.info(f"✅ Got valid access token")
        
        # Build Google Calendar API client
        credentials = Credentials(token=access_token)
        service = build('calendar', 'v3', credentials=credentials)
        
        logger.info(f"✅ Built Google Calendar API service")
        
        return service, connection_id
        
    except Exception as e:
        logger.error(f"❌ Error getting Google Calendar service: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None


def _refresh_google_token_if_needed(connection_data: Dict[str, Any]) -> Optional[str]:
    """
    Check if access token is expired and refresh if needed
    Returns the valid access token
    """
    token_expires_at = connection_data.get('token_expires_at')
    
    # If no expiry time, assume token is still valid
    if not token_expires_at:
        return connection_data.get('access_token')
    
    # Check if token is expired (with 5 minute buffer)
    expires_at = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    if expires_at > now + timedelta(minutes=5):
        # Token is still valid
        return connection_data.get('access_token')
    
    # Token expired, need to refresh
    refresh_token = connection_data.get('refresh_token')
    if not refresh_token:
        logger.error("No refresh token available")
        return None
    
    try:
        # Use Google's refresh flow
        from google.auth.transport.requests import Request
        from lib.supabase_client import supabase
        from api.config import settings
        
        # Get client credentials from metadata or fall back to settings
        metadata = connection_data.get('metadata', {})
        client_id = metadata.get('client_id') or settings.google_client_id
        client_secret = metadata.get('client_secret') or settings.google_client_secret
        
        if not client_id or not client_secret:
            logger.error("Missing Google OAuth client credentials (client_id or client_secret)")
            logger.error("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
            return None
        
        credentials = Credentials(
            token=connection_data.get('access_token'),
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret
        )
        
        credentials.refresh(Request())
        
        # Update tokens in database
        new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
        supabase.table('ext_connections')\
            .update({
                'access_token': credentials.token,
                'token_expires_at': new_expires_at.isoformat()
            })\
            .eq('user_id', connection_data.get('user_id'))\
            .eq('provider', 'google')\
            .execute()
        
        logger.info("Successfully refreshed Google access token")
        return credentials.token
        
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        return None


def convert_to_google_event_format(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert our event format to Google Calendar event format
    """
    google_event = {
        'summary': event_data.get('title', 'Untitled Event'),
    }
    
    # Add optional fields
    if event_data.get('description'):
        google_event['description'] = event_data['description']
    
    if event_data.get('location'):
        google_event['location'] = event_data['location']
    
    # Handle start/end times
    is_all_day = event_data.get('is_all_day', False)
    start_time = event_data.get('start_time')
    end_time = event_data.get('end_time')
    
    if is_all_day:
        # All-day events use 'date' field (YYYY-MM-DD format)
        if start_time:
            google_event['start'] = {'date': start_time[:10]}
        if end_time:
            google_event['end'] = {'date': end_time[:10]}
    else:
        # Timed events use 'dateTime' field with timezone
        if start_time:
            google_event['start'] = {'dateTime': start_time, 'timeZone': 'UTC'}
        if end_time:
            google_event['end'] = {'dateTime': end_time, 'timeZone': 'UTC'}
    
    # Add status
    if event_data.get('status'):
        google_event['status'] = event_data['status']
    
    return google_event

