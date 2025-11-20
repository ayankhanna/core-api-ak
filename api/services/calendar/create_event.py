"""
Calendar service - Create event operations
"""
from typing import Dict, Any
from datetime import datetime, timezone
from lib.supabase_client import supabase, get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_google_calendar_service, convert_to_google_event_format

logger = logging.getLogger(__name__)


def create_event(user_id: str, event_data: Dict[str, Any], user_jwt: str = None) -> Dict[str, Any]:
    """
    Create a new calendar event in both Supabase and Google Calendar (if connected)
    
    Args:
        user_id: User's ID
        event_data: Event data to create
        user_jwt: Optional user's Supabase JWT for Google Calendar sync
    """
    data = {
        'user_id': user_id,
        'title': event_data.get('title'),
        'description': event_data.get('description'),
        'location': event_data.get('location'),
        'start_time': event_data.get('start_time'),
        'end_time': event_data.get('end_time'),
        'is_all_day': event_data.get('is_all_day', False),
        'status': event_data.get('status', 'confirmed')
    }
    
    google_event_id = None
    connection_id = None
    
    # Try to create in Google Calendar if user has a connection
    sync_error = None
    if user_jwt:
        try:
            logger.info(f"🔄 Attempting to sync event to Google Calendar for user {user_id}")
            service, conn_id = get_google_calendar_service(user_id, user_jwt)
            
            if service:
                connection_id = conn_id
                logger.info(f"✅ Got Google Calendar service, connection ID: {conn_id}")
                
                # Convert to Google Calendar format
                google_event = convert_to_google_event_format(event_data)
                logger.info(f"📅 Converted event to Google format: {google_event.get('summary')}")
                
                # Create event in Google Calendar
                created_event = service.events().insert(
                    calendarId='primary',
                    body=google_event
                ).execute()
                
                google_event_id = created_event.get('id')
                logger.info(f"✅ Created event in Google Calendar with ID: {google_event_id}")
                
                # Store additional data from Google
                data['external_id'] = google_event_id
                data['ext_connection_id'] = connection_id
                data['synced_at'] = datetime.now(timezone.utc).isoformat()
                data['raw_item'] = created_event
            else:
                sync_error = "No active Google Calendar connection found"
                logger.warning(f"⚠️ {sync_error} for user {user_id}")
                
        except HttpError as e:
            sync_error = f"Google Calendar API error: {str(e)}"
            logger.error(f"❌ Failed to create event in Google Calendar: {str(e)}")
            logger.error(f"❌ Response: {e.content if hasattr(e, 'content') else 'No response content'}")
            # Continue to create locally even if Google sync fails
        except Exception as e:
            sync_error = f"Error syncing to Google Calendar: {str(e)}"
            logger.error(f"❌ {sync_error}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    else:
        sync_error = "No user JWT provided"
        logger.info(f"ℹ️ No user JWT provided, skipping Google Calendar sync")
    
    # Create event in Supabase
    if user_jwt:
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        result = auth_supabase.table('calendar_events').insert(data).execute()
    else:
        result = supabase.table('calendar_events').insert(data).execute()
    
    logger.info(f"Created calendar event for user {user_id} (Google sync: {google_event_id is not None})")
    
    response = {
        "message": "Calendar event created successfully",
        "event": result.data[0],
        "synced_to_google": google_event_id is not None
    }
    
    # Add sync error details if present
    if sync_error:
        response["sync_error"] = sync_error
        logger.warning(f"⚠️ Event created locally but not synced to Google: {sync_error}")
    
    return response
