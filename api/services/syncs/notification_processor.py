"""
Notification Processor - Handles incoming Google push notifications
Processes Gmail and Calendar notifications efficiently using incremental sync
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from lib.supabase_client import get_authenticated_supabase_client, get_supabase_client
import logging
import os
from googleapiclient.errors import HttpError
from api.services.email.google_api_helpers import (
    get_gmail_service,
    parse_email_headers,
    decode_email_body,
    get_attachment_info
)
from api.services.calendar.google_api_helpers import get_google_calendar_service

logger = logging.getLogger(__name__)


def process_gmail_notification(channel_id: str, resource_state: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Gmail push notification
    
    Gmail notifications contain a historyId. We fetch only the changes
    since the last known historyId, making this very efficient.
    
    Args:
        channel_id: The watch channel ID
        resource_state: State of the resource (sync, exists, not_exists)
        data: Notification payload from Google
        
    Returns:
        Dict with processing results
    """
    logger.info(f"📬 Processing Gmail notification for channel: {channel_id}, state: {resource_state}")
    
    # Ignore sync messages (initial verification)
    if resource_state == 'sync':
        logger.info("ℹ️ Sync message received (initial verification)")
        return {'success': True, 'message': 'Sync message processed'}
    
    supabase = get_supabase_client()
    
    try:
        # Find subscription by channel_id
        subscription = supabase.table('push_subscriptions')\
            .select('*, ext_connections!inner(user_id, access_token, refresh_token)')\
            .eq('channel_id', channel_id)\
            .eq('provider', 'gmail')\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not subscription.data:
            logger.warning(f"⚠️ No active subscription found for channel: {channel_id}")
            return {'success': False, 'error': 'Subscription not found'}
        
        sub_data = subscription.data
        user_id = sub_data['ext_connections']['user_id']
        last_history_id = sub_data.get('history_id')
        
        logger.info(f"📧 Processing Gmail changes for user {user_id} since historyId: {last_history_id}")
        
        # Get user's JWT for authenticated operations
        # In production, you'd generate a service JWT or use admin credentials
        # For now, we'll use a simplified approach
        
        # Process the history changes
        result = process_gmail_history_changes(
            user_id=user_id,
            start_history_id=last_history_id,
            connection_id=sub_data['connection_id']
        )
        
        # Update subscription with new historyId and notification count
        new_history_id = data.get('historyId') or result.get('latest_history_id')
        if new_history_id:
            supabase.table('push_subscriptions')\
                .update({
                    'history_id': new_history_id,
                    'last_notification_at': datetime.now(timezone.utc).isoformat(),
                    'notification_count': sub_data.get('notification_count', 0) + 1,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('id', sub_data['id'])\
                .execute()
        
        logger.info(f"✅ Gmail notification processed: {result.get('changes_processed', 0)} changes")
        
        return {
            'success': True,
            'user_id': user_id,
            'changes_processed': result.get('changes_processed', 0),
            'new_history_id': new_history_id
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing Gmail notification: {str(e)}")
        return {'success': False, 'error': str(e)}


def process_gmail_history_changes(
    user_id: str,
    start_history_id: str,
    connection_id: str
) -> Dict[str, Any]:
    """
    Fetch and process Gmail history changes using the History API
    This is much more efficient than fetching all messages
    
    Args:
        user_id: User's ID
        start_history_id: Starting history ID
        connection_id: Connection ID
        
    Returns:
        Dict with processing results
    """
    from lib.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    
    try:
        # Get connection details
        connection = supabase.table('ext_connections')\
            .select('*')\
            .eq('id', connection_id)\
            .single()\
            .execute()
        
        if not connection.data:
            raise ValueError("Connection not found")
        
        # Build Gmail service
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials(
            token=connection.data['access_token'],
            refresh_token=connection.data['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
        )
        
        service = build('gmail', 'v1', credentials=creds)
        
        # Fetch history
        logger.info(f"📜 Fetching Gmail history since {start_history_id}")
        
        history_response = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
        ).execute()
        
        history_records = history_response.get('history', [])
        latest_history_id = history_response.get('historyId')
        
        if not history_records:
            logger.info("ℹ️ No history changes found")
            return {
                'changes_processed': 0,
                'latest_history_id': latest_history_id
            }
        
        changes_count = 0
        
        # Process each history record
        for history in history_records:
            # Messages added
            for msg_added in history.get('messagesAdded', []):
                message = msg_added.get('message', {})
                message_id = message.get('id')
                
                # Fetch full message details
                full_msg = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                
                # Store in database (similar to sync_gmail logic)
                store_email_from_message(supabase, user_id, connection_id, full_msg)
                changes_count += 1
            
            # Messages deleted
            for msg_deleted in history.get('messagesDeleted', []):
                message_id = msg_deleted.get('message', {}).get('id')
                
                # Delete from database
                supabase.table('emails')\
                    .delete()\
                    .eq('user_id', user_id)\
                    .eq('external_id', message_id)\
                    .execute()
                changes_count += 1
            
            # Labels changed
            for label_added in history.get('labelsAdded', []):
                message_id = label_added.get('message', {}).get('id')
                labels = label_added.get('labelIds', [])
                
                # Update labels in database
                update_email_labels(supabase, user_id, message_id, labels, action='add')
                changes_count += 1
            
            for label_removed in history.get('labelsRemoved', []):
                message_id = label_removed.get('message', {}).get('id')
                labels = label_removed.get('labelIds', [])
                
                # Update labels in database
                update_email_labels(supabase, user_id, message_id, labels, action='remove')
                changes_count += 1
        
        logger.info(f"✅ Processed {changes_count} Gmail history changes")
        
        return {
            'changes_processed': changes_count,
            'latest_history_id': latest_history_id
        }
        
    except HttpError as e:
        logger.error(f"❌ Gmail API error processing history: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error processing history changes: {str(e)}")
        raise


def store_email_from_message(supabase, user_id: str, connection_id: str, full_msg: Dict) -> None:
    """Helper function to store email from Gmail message"""
    from api.services.email.google_api_helpers import (
        parse_email_headers,
        decode_email_body,
        get_attachment_info
    )
    
    # Parse message
    headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
    body = decode_email_body(full_msg.get('payload', {}))
    
    message_id = full_msg.get('id')
    thread_id = full_msg.get('threadId')
    snippet = full_msg.get('snippet', '')
    labels = full_msg.get('labelIds', [])
    internal_date = full_msg.get('internalDate')
    size_estimate = full_msg.get('sizeEstimate', 0)
    
    if internal_date:
        received_at = datetime.fromtimestamp(
            int(internal_date) / 1000,
            tz=timezone.utc
        ).isoformat()
    else:
        received_at = None
    
    is_unread = 'UNREAD' in labels
    is_starred = 'STARRED' in labels
    is_important = 'IMPORTANT' in labels
    is_draft = 'DRAFT' in labels
    
    attachments = get_attachment_info(full_msg.get('payload', {}))
    
    # Parse addresses
    to_addresses = [addr.strip() for addr in headers.get('to', '').split(',')] if headers.get('to') else []
    cc_addresses = [addr.strip() for addr in headers.get('cc', '').split(',')] if headers.get('cc') else []
    
    email_data = {
        'user_id': user_id,
        'ext_connection_id': connection_id,
        'external_id': message_id,
        'thread_id': thread_id,
        'subject': headers.get('subject', '(No Subject)'),
        'from_address': headers.get('from', ''),
        'to_addresses': to_addresses,
        'cc_addresses': cc_addresses if cc_addresses else None,
        'body_text': body.get('plain', ''),
        'body_html': body.get('html', ''),
        'snippet': snippet,
        'labels': labels,
        'is_read': not is_unread,
        'is_starred': is_starred,
        'received_at': received_at,
        'metadata': {
            'is_important': is_important,
            'is_draft': is_draft,
            'size_estimate': size_estimate,
            'has_attachments': len(attachments) > 0,
            'attachments': attachments,
            'raw_item': full_msg
        },
        'synced_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert email
    existing = supabase.table('emails')\
        .select('id')\
        .eq('user_id', user_id)\
        .eq('external_id', message_id)\
        .execute()
    
    if existing.data:
        supabase.table('emails')\
            .update(email_data)\
            .eq('id', existing.data[0]['id'])\
            .execute()
    else:
        supabase.table('emails')\
            .insert(email_data)\
            .execute()


def update_email_labels(supabase, user_id: str, message_id: str, labels: list, action: str) -> None:
    """Helper function to update email labels"""
    email = supabase.table('emails')\
        .select('id, labels')\
        .eq('user_id', user_id)\
        .eq('external_id', message_id)\
        .single()\
        .execute()
    
    if not email.data:
        return
    
    current_labels = email.data.get('labels', [])
    
    if action == 'add':
        new_labels = list(set(current_labels + labels))
    else:  # remove
        new_labels = [l for l in current_labels if l not in labels]
    
    # Update is_read and is_starred based on labels
    is_read = 'UNREAD' not in new_labels
    is_starred = 'STARRED' in new_labels
    
    supabase.table('emails')\
        .update({
            'labels': new_labels,
            'is_read': is_read,
            'is_starred': is_starred,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })\
        .eq('id', email.data['id'])\
        .execute()


def process_calendar_notification(channel_id: str, resource_state: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Calendar push notification
    
    Calendar notifications indicate that events have changed.
    We use sync tokens for incremental updates.
    
    Args:
        channel_id: The watch channel ID
        resource_state: State of the resource
        data: Notification payload from Google
        
    Returns:
        Dict with processing results
    """
    logger.info(f"📅 Processing Calendar notification for channel: {channel_id}, state: {resource_state}")
    
    # Ignore sync messages
    if resource_state == 'sync':
        logger.info("ℹ️ Sync message received (initial verification)")
        return {'success': True, 'message': 'Sync message processed'}
    
    supabase = get_supabase_client()
    
    try:
        # Find subscription
        subscription = supabase.table('push_subscriptions')\
            .select('*, ext_connections!inner(user_id, access_token, refresh_token)')\
            .eq('channel_id', channel_id)\
            .eq('provider', 'calendar')\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not subscription.data:
            logger.warning(f"⚠️ No active subscription found for channel: {channel_id}")
            return {'success': False, 'error': 'Subscription not found'}
        
        sub_data = subscription.data
        user_id = sub_data['ext_connections']['user_id']
        sync_token = sub_data.get('sync_token')
        
        logger.info(f"📆 Processing Calendar changes for user {user_id}")
        
        # Process calendar changes using sync token
        result = process_calendar_sync(
            user_id=user_id,
            connection_id=sub_data['connection_id'],
            sync_token=sync_token
        )
        
        # Update subscription
        new_sync_token = result.get('next_sync_token')
        if new_sync_token:
            supabase.table('push_subscriptions')\
                .update({
                    'sync_token': new_sync_token,
                    'last_notification_at': datetime.now(timezone.utc).isoformat(),
                    'notification_count': sub_data.get('notification_count', 0) + 1,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('id', sub_data['id'])\
                .execute()
        
        logger.info(f"✅ Calendar notification processed: {result.get('changes_processed', 0)} changes")
        
        return {
            'success': True,
            'user_id': user_id,
            'changes_processed': result.get('changes_processed', 0)
        }
        
    except Exception as e:
        logger.error(f"❌ Error processing Calendar notification: {str(e)}")
        return {'success': False, 'error': str(e)}


def process_calendar_sync(
    user_id: str,
    connection_id: str,
    sync_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sync calendar events using sync token for incremental updates
    
    Args:
        user_id: User's ID
        connection_id: Connection ID
        sync_token: Optional sync token for incremental sync
        
    Returns:
        Dict with sync results
    """
    from lib.supabase_client import get_supabase_client
    import os
    
    supabase = get_supabase_client()
    
    try:
        # Get connection
        connection = supabase.table('ext_connections')\
            .select('*')\
            .eq('id', connection_id)\
            .single()\
            .execute()
        
        if not connection.data:
            raise ValueError("Connection not found")
        
        # Build Calendar service
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        creds = Credentials(
            token=connection.data['access_token'],
            refresh_token=connection.data['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET')
        )
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Fetch events using sync token if available
        request_params = {
            'calendarId': 'primary',
            'singleEvents': True
        }
        
        if sync_token:
            request_params['syncToken'] = sync_token
        else:
            # First sync - get events from past 7 days to future 30 days
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            request_params['timeMin'] = (now - timedelta(days=7)).isoformat()
            request_params['timeMax'] = (now + timedelta(days=30)).isoformat()
        
        events_result = service.events().list(**request_params).execute()
        
        events = events_result.get('items', [])
        next_sync_token = events_result.get('nextSyncToken')
        
        changes_count = 0
        
        for event in events:
            # Store or update event
            store_calendar_event(supabase, user_id, connection_id, event)
            changes_count += 1
        
        logger.info(f"✅ Processed {changes_count} calendar events")
        
        return {
            'changes_processed': changes_count,
            'next_sync_token': next_sync_token
        }
        
    except HttpError as e:
        logger.error(f"❌ Calendar API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error syncing calendar: {str(e)}")
        raise


def store_calendar_event(supabase, user_id: str, connection_id: str, event: Dict) -> None:
    """Helper function to store calendar event"""
    event_id = event.get('id')
    title = event.get('summary', 'Untitled Event')
    description = event.get('description')
    location = event.get('location')
    status = event.get('status', 'confirmed')
    
    # Handle deleted events
    if status == 'cancelled':
        supabase.table('calendar_events')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('external_id', event_id)\
            .execute()
        return
    
    # Handle start/end times
    start = event.get('start', {})
    end = event.get('end', {})
    
    is_all_day = 'date' in start
    
    if is_all_day:
        start_time = start.get('date') + 'T00:00:00Z'
        end_time = end.get('date') + 'T23:59:59Z'
    else:
        start_time = start.get('dateTime')
        end_time = end.get('dateTime')
    
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
        'status': status,
        'synced_at': datetime.now(timezone.utc).isoformat(),
        'raw_item': event
    }
    
    # Upsert event
    existing = supabase.table('calendar_events')\
        .select('id')\
        .eq('user_id', user_id)\
        .eq('external_id', event_id)\
        .execute()
    
    if existing.data:
        supabase.table('calendar_events')\
            .update(event_data)\
            .eq('id', existing.data[0]['id'])\
            .execute()
    else:
        supabase.table('calendar_events')\
            .insert(event_data)\
            .execute()

