"""
Calendar service - Fetch operations for calendar events
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from lib.supabase_client import supabase, get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


def get_events(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Fetch calendar events for a user with optional date filtering
    """
    query = supabase.table('calendar_events')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('start_time', desc=False)\
        .limit(limit)
    
    if start_date:
        query = query.gte('start_time', start_date)
    
    if end_date:
        query = query.lte('start_time', end_date)
    
    result = query.execute()
    
    return {
        "events": result.data,
        "count": len(result.data)
    }


def get_upcoming_events(user_id: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get upcoming calendar events for a user
    """
    now = datetime.utcnow().isoformat() + "Z"
    
    result = supabase.table('calendar_events')\
        .select('*')\
        .eq('user_id', user_id)\
        .gte('start_time', now)\
        .order('start_time', desc=False)\
        .limit(limit)\
        .execute()
    
    return {
        "events": result.data,
        "count": len(result.data)
    }


def get_all_events(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Get all calendar events for a user.
    Smart caching: Tries DB first, falls back to Google Calendar API if empty.
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
    """
    from datetime import timedelta
    from googleapiclient.errors import HttpError
    from api.services.calendar.google_api_helpers import get_google_calendar_service
    
    # Use authenticated Supabase client
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Try fetching from database first
    result = auth_supabase.table('calendar_events')\
        .select('*')\
        .eq('user_id', user_id)\
        .order('start_time', desc=False)\
        .execute()
    
    # If we have events in DB, return them
    if result.data and len(result.data) > 0:
        logger.info(f"✅ Found {len(result.data)} cached events")
        return {
            "events": result.data,
            "count": len(result.data),
            "source": "cache"
        }
    
    # Otherwise, try to fetch from Google Calendar API
    logger.info(f"📦 No cached events found, fetching from Google Calendar API")
    
    try:
        service, connection_id = get_google_calendar_service(user_id, user_jwt)
        
        if not service or not connection_id:
            # No Google connection, return empty
            return {
                "events": [],
                "count": 0,
                "source": "none"
            }
        
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
        
        # Parse and save events to database for caching
        parsed_events = []
        synced_count = 0
        updated_count = 0
        
        for event in events:
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
            
            # Check if event already exists in DB
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
                'raw_item': event  # Store full Google Calendar event
            }
            
            # Insert or update in database
            if existing.data:
                # Update existing event
                result = auth_supabase.table('calendar_events')\
                    .update(event_data)\
                    .eq('id', existing.data[0]['id'])\
                    .execute()
                updated_count += 1
                db_event = result.data[0] if result.data else None
            else:
                # Insert new event
                result = auth_supabase.table('calendar_events')\
                    .insert(event_data)\
                    .execute()
                synced_count += 1
                db_event = result.data[0] if result.data else None
            
            # Add to parsed_events list with DB id if available
            if db_event:
                parsed_events.append(db_event)
            else:
                # Fallback if DB operation failed
                parsed_events.append({
                    'id': event_id,
                    'external_id': event_id,
                    'user_id': user_id,
                    'title': title,
                    'description': description,
                    'location': location,
                    'start_time': start_time,
                    'end_time': end_time,
                    'is_all_day': is_all_day,
                    'status': event.get('status', 'confirmed')
                })
        
        # Update last synced timestamp on connection
        auth_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        logger.info(f"✅ Fetched and synced {len(parsed_events)} events from Google Calendar API (new: {synced_count}, updated: {updated_count})")
        
        return {
            "events": parsed_events,
            "count": len(parsed_events),
            "source": "google_api_synced",
            "synced_count": synced_count,
            "updated_count": updated_count
        }
        
    except HttpError as e:
        logger.error(f"Google Calendar API error: {str(e)}")
        # Return empty on error
        return {
            "events": [],
            "count": 0,
            "source": "error",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error fetching from Google Calendar: {str(e)}")
        # Return empty on error
        return {
            "events": [],
            "count": 0,
            "source": "error",
            "error": str(e)
        }


def get_today_events(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Get today's calendar events for a user
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
    """
    # Use authenticated Supabase client
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get today's date range in UTC
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    result = auth_supabase.table('calendar_events')\
        .select('*')\
        .eq('user_id', user_id)\
        .gte('start_time', start_of_day.isoformat())\
        .lte('start_time', end_of_day.isoformat())\
        .order('start_time', desc=False)\
        .execute()
    
    return {
        "events": result.data,
        "count": len(result.data),
        "date": start_of_day.date().isoformat()
    }


def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific calendar event by ID
    """
    result = supabase.table('calendar_events')\
        .select('*')\
        .eq('id', event_id)\
        .single()\
        .execute()
    
    return result.data if result.data else None

