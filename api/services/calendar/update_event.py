"""
Calendar service - Update event operations
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from lib.supabase_client import supabase, get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_google_calendar_service, convert_to_google_event_format

logger = logging.getLogger(__name__)


def update_event(
    event_id: str,
    event_data: Dict[str, Any],
    user_id: str = None,
    user_jwt: str = None
) -> Optional[Dict[str, Any]]:
    """
    Update an existing calendar event in both Supabase and Google Calendar (if synced)
    
    Args:
        event_id: Event ID in Supabase
        event_data: Updated event data
        user_id: Optional user ID for Google Calendar sync
        user_jwt: Optional user's Supabase JWT for Google Calendar sync
    """
    data = {
        'title': event_data.get('title'),
        'description': event_data.get('description'),
        'location': event_data.get('location'),
        'start_time': event_data.get('start_time'),
        'end_time': event_data.get('end_time'),
        'is_all_day': event_data.get('is_all_day', False),
        'status': event_data.get('status', 'confirmed')
    }
    
    google_updated = False
    
    # Check if event has a Google Calendar ID (was synced from Google)
    if user_id and user_jwt:
        try:
            # Get the existing event to check for external_id
            auth_supabase = get_authenticated_supabase_client(user_jwt)
            existing_event = auth_supabase.table('calendar_events')\
                .select('external_id, ext_connection_id')\
                .eq('id', event_id)\
                .single()\
                .execute()
            
            if existing_event.data and existing_event.data.get('external_id'):
                external_id = existing_event.data['external_id']
                
                # Try to update in Google Calendar
                service, _ = get_google_calendar_service(user_id, user_jwt)
                if service:
                    try:
                        # Get the current Google event
                        google_event = service.events().get(
                            calendarId='primary',
                            eventId=external_id
                        ).execute()
                        
                        # Update with new data
                        google_event_updates = convert_to_google_event_format(event_data)
                        google_event.update(google_event_updates)
                        
                        # Update in Google Calendar
                        updated_event = service.events().update(
                            calendarId='primary',
                            eventId=external_id,
                            body=google_event
                        ).execute()
                        
                        google_updated = True
                        data['synced_at'] = datetime.now(timezone.utc).isoformat()
                        data['raw_item'] = updated_event
                        
                        logger.info(f"Updated event in Google Calendar: {external_id}")
                        
                    except HttpError as e:
                        logger.error(f"Failed to update event in Google Calendar: {str(e)}")
                        # Continue to update locally even if Google sync fails
                        
        except Exception as e:
            logger.error(f"Error checking/updating Google Calendar: {str(e)}")
    
    # Update event in Supabase
    if user_jwt:
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        result = auth_supabase.table('calendar_events')\
            .update(data)\
            .eq('id', event_id)\
            .execute()
    else:
        result = supabase.table('calendar_events')\
            .update(data)\
            .eq('id', event_id)\
            .execute()
    
    if not result.data:
        return None
    
    logger.info(f"Updated calendar event {event_id} (Google sync: {google_updated})")
    
    return {
        "message": "Calendar event updated successfully",
        "event": result.data[0],
        "synced_to_google": google_updated
    }
