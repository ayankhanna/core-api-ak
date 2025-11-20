"""
Calendar service - Google Calendar sync operations
"""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from api.services.calendar.google_api_helpers import get_google_calendar_service

logger = logging.getLogger(__name__)


def sync_google_calendar(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Sync calendar events from Google Calendar
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
    """
    # Use authenticated Supabase client
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Google Calendar service
    service, connection_id = get_google_calendar_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        
        # Fetch events from Google Calendar (last 7 days to next 30 days)
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=7)).isoformat()
        time_max = (now + timedelta(days=30)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        synced_count = 0
        updated_count = 0
        
        for event in events:
            # Parse event data
            event_id = event.get('id')
            title = event.get('summary', 'Untitled Event')
            description = event.get('description')
            location = event.get('location')
            
            # Handle start/end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Check if all-day event
            is_all_day = 'date' in start
            
            if is_all_day:
                start_time = start.get('date') + 'T00:00:00Z'
                end_time = end.get('date') + 'T23:59:59Z'
            else:
                start_time = start.get('dateTime')
                end_time = end.get('dateTime')
            
            # Check if event already exists
            existing = auth_supabase.table('calendar_events')\
                .select('id')\
                .eq('user_id', user_id)\
                .eq('external_id', event_id)\
                .execute()
            
            event_data = {
                'user_id': user_id,
                'ext_connection_id': connection_id,
                'external_id': event_id,
                'title': title,
                'description': description,
                'location': location,
                'start_time': start_time,
                'end_time': end_time,
                'is_all_day': is_all_day,
                'status': event.get('status', 'confirmed'),
                'synced_at': datetime.now(timezone.utc).isoformat(),
                'raw_item': event  # Store full lossless Google Calendar event
            }
            
            if existing.data:
                # Update existing event
                auth_supabase.table('calendar_events')\
                    .update(event_data)\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
                updated_count += 1
            else:
                # Insert new event
                auth_supabase.table('calendar_events')\
                    .insert(event_data)\
                    .execute()
                synced_count += 1
        
        # Update last synced timestamp
        auth_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        logger.info(f"Successfully synced {synced_count} new and {updated_count} updated events for user {user_id}")
        
        return {
            "message": "Calendar sync completed successfully",
            "status": "completed",
            "user_id": user_id,
            "new_events": synced_count,
            "updated_events": updated_count,
            "total_events": synced_count + updated_count
        }
        
    except HttpError as e:
        logger.error(f"Google Calendar API error: {str(e)}")
        raise ValueError(f"Failed to sync with Google Calendar: {str(e)}")
    except Exception as e:
        logger.error(f"Error syncing calendar: {str(e)}")
        raise ValueError(f"Calendar sync failed: {str(e)}")

