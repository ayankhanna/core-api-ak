"""
Calendar router - HTTP endpoints for calendar operations
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from api.services.calendar import (
    get_all_events,
    get_today_events,
    create_event,
    update_event,
    delete_event,
    sync_google_calendar
)
from api.dependencies import get_current_user_jwt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("/events")
async def get_all_events_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Get all calendar events for a specific user.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📅 Fetching all events for user {user_id}")
        result = get_all_events(user_id, user_jwt)
        logger.info(f"✅ Found {len(result.get('events', []))} total events")
        return result
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching events: {error_str}")
        
        # Check if it's a JWT expiration error
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {error_str}"
        )


@router.get("/events/today")
async def get_today_events_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Get calendar events for today for a specific user.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📅 Fetching today's events for user {user_id}")
        result = get_today_events(user_id, user_jwt)
        logger.info(f"✅ Found {len(result.get('events', []))} events for today")
        return result
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching today's events: {error_str}")
        
        # Check if it's a JWT expiration error
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch today's events: {error_str}"
        )


@router.post("/events")
async def create_event_endpoint(
    user_id: str,
    event_data: dict,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Create a new calendar event (syncs to Google Calendar if connected).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📅 Creating event for user {user_id}")
        result = create_event(user_id, event_data, user_jwt)
        logger.info(f"✅ Event created (Google sync: {result.get('synced_to_google', False)})")
        return result
    except Exception as e:
        logger.error(f"❌ Error creating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create event: {str(e)}"
        )


@router.put("/events/{event_id}")
async def update_event_endpoint(
    event_id: str,
    user_id: str,
    event_data: dict,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Update an existing calendar event (syncs to Google Calendar if connected).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📅 Updating event {event_id} for user {user_id}")
        result = update_event(event_id, event_data, user_id, user_jwt)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        logger.info(f"✅ Event updated (Google sync: {result.get('synced_to_google', False)})")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update event: {str(e)}"
        )


@router.delete("/events/{event_id}")
async def delete_event_endpoint(
    event_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Delete a calendar event (syncs to Google Calendar if connected).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📅 Deleting event {event_id} for user {user_id}")
        result = delete_event(event_id, user_id, user_jwt)
        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )
        logger.info(f"✅ Event deleted (Google sync: {result.get('synced_to_google', False)})")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting event: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}"
        )


@router.post("/sync")
async def sync_google_calendar_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Sync calendar events from Google Calendar for a user.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🔄 Syncing Google Calendar for user {user_id}")
        result = sync_google_calendar(user_id, user_jwt)
        logger.info(f"✅ Sync completed for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error syncing calendar: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync calendar: {str(e)}"
        )

