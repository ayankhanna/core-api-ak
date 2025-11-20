"""
Calendar service - Delete event operations
"""
from typing import Dict, Any, Optional
from lib.supabase_client import supabase, get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_google_calendar_service

logger = logging.getLogger(__name__)


def delete_event(
    event_id: str,
    user_id: str = None,
    user_jwt: str = None
) -> Dict[str, Any]:
    """
    Delete a calendar event from both Supabase and Google Calendar (if synced)
    Returns dict with success status and sync info
    
    Args:
        event_id: Event ID in Supabase
        user_id: Optional user ID for Google Calendar sync
        user_jwt: Optional user's Supabase JWT for Google Calendar sync
    """
    google_deleted = False
    
    # Check if event has a Google Calendar ID (was synced from Google)
    if user_id and user_jwt:
        try:
            # Get the existing event to check for external_id
            auth_supabase = get_authenticated_supabase_client(user_jwt)
            existing_event = auth_supabase.table('calendar_events')\
                .select('external_id')\
                .eq('id', event_id)\
                .single()\
                .execute()
            
            if existing_event.data and existing_event.data.get('external_id'):
                external_id = existing_event.data['external_id']
                
                # Try to delete from Google Calendar
                service, _ = get_google_calendar_service(user_id, user_jwt)
                if service:
                    try:
                        service.events().delete(
                            calendarId='primary',
                            eventId=external_id
                        ).execute()
                        
                        google_deleted = True
                        logger.info(f"Deleted event from Google Calendar: {external_id}")
                        
                    except HttpError as e:
                        if e.resp.status == 404:
                            logger.warning(f"Event not found in Google Calendar: {external_id}")
                        else:
                            logger.error(f"Failed to delete event from Google Calendar: {str(e)}")
                        # Continue to delete locally even if Google sync fails
                        
        except Exception as e:
            logger.error(f"Error checking/deleting from Google Calendar: {str(e)}")
    
    # Delete event from Supabase
    if user_jwt:
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        result = auth_supabase.table('calendar_events')\
            .delete()\
            .eq('id', event_id)\
            .execute()
    else:
        result = supabase.table('calendar_events')\
            .delete()\
            .eq('id', event_id)\
            .execute()
    
    if not result.data:
        return {
            "success": False,
            "message": "Event not found",
            "synced_to_google": False
        }
    
    logger.info(f"Deleted calendar event {event_id} (Google sync: {google_deleted})")
    
    return {
        "success": True,
        "message": "Calendar event deleted successfully",
        "synced_to_google": google_deleted
    }
