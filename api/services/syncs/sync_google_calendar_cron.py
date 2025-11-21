"""
Calendar sync for cron jobs - bypasses RLS using service role
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def sync_google_calendar_cron(
    calendar_service,
    connection_id: str,
    user_id: str,
    service_supabase,
    days_past: int = 30,
    days_future: int = 90
) -> Dict[str, Any]:
    """
    Sync calendar events from Google Calendar for cron jobs.
    Uses service role Supabase client to bypass RLS.
    
    Args:
        calendar_service: Google Calendar API service
        connection_id: External connection ID
        user_id: User's ID
        service_supabase: Service role Supabase client (bypasses RLS)
        days_past: Number of days in the past to sync (default 30)
        days_future: Number of days in the future to sync (default 90)
    
    Returns:
        Dict with sync results
    """
    try:
        # Fetch events from Google Calendar with expanded time range
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=days_past)).isoformat()
        time_max = (now + timedelta(days=days_future)).isoformat()
        
        synced_count = 0
        updated_count = 0
        page_token = None
        total_fetched = 0
        
        # Handle pagination to get ALL events in the time range
        while True:
            logger.info(f"📥 Fetching events page (token: {page_token[:20] if page_token else 'first page'})")
            
            events_result = calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=250,  # Max allowed by API
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            
            events = events_result.get('items', [])
            total_fetched += len(events)
            
            logger.info(f"📦 Processing {len(events)} events from this page (total so far: {total_fetched})")
            
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
                
                # Check if event already exists (using service role - bypasses RLS)
                existing = service_supabase.table('calendar_events')\
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
                    service_supabase.table('calendar_events')\
                        .update(event_data)\
                        .eq('id', existing.data[0]['id'])\
                        .execute()
                    updated_count += 1
                else:
                    # Insert new event
                    service_supabase.table('calendar_events')\
                        .insert(event_data)\
                        .execute()
                    synced_count += 1
            
            # Check if there are more pages
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        
        # Update last synced timestamp
        service_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        logger.info(f"✅ Calendar sync complete: {synced_count} new, {updated_count} updated (total fetched: {total_fetched})")
        
        return {
            "status": "success",
            "new_events": synced_count,
            "updated_events": updated_count,
            "total_events": synced_count + updated_count,
            "total_fetched": total_fetched
        }
        
    except HttpError as e:
        logger.error(f"❌ Google Calendar API error: {str(e)}")
        return {
            "status": "error",
            "error": f"Google Calendar API error: {str(e)}",
            "new_events": synced_count,
            "updated_events": updated_count
        }
    except Exception as e:
        logger.error(f"❌ Error syncing calendar: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "status": "error",
            "error": str(e),
            "new_events": synced_count,
            "updated_events": updated_count
        }

