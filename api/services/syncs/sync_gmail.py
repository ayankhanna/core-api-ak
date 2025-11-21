"""
Gmail sync service - Sync emails from Gmail to database
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from api.services.email.google_api_helpers import (
    get_gmail_service,
    parse_email_headers,
    decode_email_body,
    get_attachment_info
)

logger = logging.getLogger(__name__)


def sync_gmail(
    user_id: str,
    user_jwt: str,
    max_results: int = 100,
    sync_since: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sync emails from Gmail to database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of emails to sync (default 100)
        sync_since: Optional date to sync from (ISO format). If not provided, syncs last 20 days
        
    Returns:
        Dict with sync results
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Build query for recent emails
        if sync_since:
            # Use provided sync date
            query = f"after:{sync_since}"
        else:
            # Default to last 20 days
            since_date = (datetime.now(timezone.utc) - timedelta(days=20)).strftime('%Y/%m/%d')
            query = f"after:{since_date}"
        
        logger.info(f"🔄 Starting Gmail sync for user {user_id} with query: {query}")
        
        # Fetch message list
        messages_result = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = messages_result.get('messages', [])
        
        if not messages:
            logger.info(f"ℹ️ No new emails to sync for user {user_id}")
            return {
                "message": "No new emails to sync",
                "status": "completed",
                "user_id": user_id,
                "new_emails": 0,
                "updated_emails": 0,
                "total_emails": 0
            }
        
        synced_count = 0
        updated_count = 0
        error_count = 0
        
        logger.info(f"📧 Found {len(messages)} messages to sync")
        
        for msg in messages:
            try:
                # Get full message details
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='full'
                ).execute()
                
                # Parse headers
                headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
                
                # Decode body
                body = decode_email_body(full_msg.get('payload', {}))
                
                # Get metadata
                message_id = full_msg.get('id')
                thread_id = full_msg.get('threadId')
                snippet = full_msg.get('snippet', '')
                labels = full_msg.get('labelIds', [])
                internal_date = full_msg.get('internalDate')
                size_estimate = full_msg.get('sizeEstimate', 0)
                
                # Convert internal date
                if internal_date:
                    received_at = datetime.fromtimestamp(
                        int(internal_date) / 1000,
                        tz=timezone.utc
                    ).isoformat()
                else:
                    received_at = None
                
                # Check various flags
                is_unread = 'UNREAD' in labels
                is_starred = 'STARRED' in labels
                is_important = 'IMPORTANT' in labels
                is_draft = 'DRAFT' in labels
                
                # Get attachments
                attachments = get_attachment_info(full_msg.get('payload', {}))
                
                # Check if email already exists
                existing = auth_supabase.table('emails')\
                    .select('id')\
                    .eq('user_id', user_id)\
                    .eq('external_id', message_id)\
                    .execute()
                
                # Parse addresses into arrays
                to_addresses = [addr.strip() for addr in headers.get('to', '').split(',')] if headers.get('to') else []
                cc_addresses = [addr.strip() for addr in headers.get('cc', '').split(',')] if headers.get('cc') else []
                
                # Use plain text body, or HTML if plain not available
                body_content = body.get('plain') or body.get('html', '')
                
                email_data = {
                    'user_id': user_id,
                    'ext_connection_id': connection_id,
                    'external_id': message_id,
                    'thread_id': thread_id,
                    'subject': headers.get('subject', '(No Subject)'),
                    'from': headers.get('from', ''),
                    'to': to_addresses,
                    'cc': cc_addresses if cc_addresses else None,
                    'body': body_content,
                    'snippet': snippet,
                    'labels': labels,
                    'is_read': not is_unread,
                    'is_starred': is_starred,
                    'is_draft': is_draft,
                    'received_at': received_at,
                    'has_attachments': len(attachments) > 0,
                    'attachments': attachments,
                    'synced_at': datetime.now(timezone.utc).isoformat(),
                    'raw_item': full_msg  # Store full lossless Gmail message
                }
                
                if existing.data:
                    # Update existing email
                    auth_supabase.table('emails')\
                        .update(email_data)\
                        .eq('id', existing.data[0]['id'])\
                        .execute()
                    updated_count += 1
                else:
                    # Insert new email
                    auth_supabase.table('emails')\
                        .insert(email_data)\
                        .execute()
                    synced_count += 1
                
            except HttpError as e:
                logger.error(f"❌ Error syncing message {msg['id']}: {str(e)}")
                error_count += 1
                continue
            except Exception as e:
                logger.error(f"❌ Unexpected error syncing message {msg['id']}: {str(e)}")
                error_count += 1
                continue
        
        # Update last synced timestamp
        auth_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        total_synced = synced_count + updated_count
        
        logger.info(f"✅ Gmail sync completed for user {user_id}: {synced_count} new, {updated_count} updated, {error_count} errors")
        
        return {
            "message": "Gmail sync completed successfully",
            "status": "completed",
            "user_id": user_id,
            "new_emails": synced_count,
            "updated_emails": updated_count,
            "total_emails": total_synced,
            "errors": error_count
        }
        
    except HttpError as e:
        logger.error(f"❌ Gmail API error during sync: {str(e)}")
        raise ValueError(f"Failed to sync Gmail: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error syncing Gmail: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise ValueError(f"Gmail sync failed: {str(e)}")


def sync_gmail_incremental(
    user_id: str,
    user_jwt: str
) -> Dict[str, Any]:
    """
    Perform incremental Gmail sync based on last sync time
    Only syncs emails since the last successful sync
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Dict with sync results
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        # Get last sync time from connection
        connection_result = auth_supabase.table('ext_connections')\
            .select('id, last_synced')\
            .eq('user_id', user_id)\
            .eq('provider', 'google')\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not connection_result.data:
            raise ValueError("No active Google connection found")
        
        last_synced = connection_result.data.get('last_synced')
        
        # Determine sync date
        if last_synced:
            # Parse last sync date and subtract 1 hour buffer for safety
            last_sync_dt = datetime.fromisoformat(last_synced.replace('Z', '+00:00'))
            sync_since_dt = last_sync_dt - timedelta(hours=1)
            sync_since = sync_since_dt.strftime('%Y/%m/%d')
        else:
            # First sync - get last 20 days
            sync_since_dt = datetime.now(timezone.utc) - timedelta(days=20)
            sync_since = sync_since_dt.strftime('%Y/%m/%d')
        
        logger.info(f"🔄 Performing incremental sync since {sync_since}")
        
        return sync_gmail(
            user_id=user_id,
            user_jwt=user_jwt,
            max_results=200,
            sync_since=sync_since
        )
        
    except Exception as e:
        logger.error(f"❌ Error in incremental sync: {str(e)}")
        raise ValueError(f"Incremental sync failed: {str(e)}")


def sync_gmail_full(
    user_id: str,
    user_jwt: str,
    days_back: int = 20
) -> Dict[str, Any]:
    """
    Perform full Gmail sync for a specified number of days
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        days_back: Number of days to sync back (default 20)
        
    Returns:
        Dict with sync results
    """
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y/%m/%d')
    
    logger.info(f"🔄 Performing full sync for {days_back} days (since {since_date})")
    
    return sync_gmail(
        user_id=user_id,
        user_jwt=user_jwt,
        max_results=500,
        sync_since=since_date
    )


def process_gmail_history(
    user_id: str,
    user_jwt: str,
    start_history_id: str
) -> Dict[str, Any]:
    """
    Process Gmail changes using the history API (much more efficient than full sync)
    This is called when we receive a push notification from Google
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        start_history_id: The historyId to start fetching changes from
        
    Returns:
        Dict with sync results
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user")
    
    try:
        logger.info(f"📜 Processing Gmail history for user {user_id} from historyId {start_history_id}")
        
        # Fetch history changes
        history_result = service.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded', 'messageDeleted', 'labelAdded', 'labelRemoved']
        ).execute()
        
        history_records = history_result.get('history', [])
        new_history_id = history_result.get('historyId', start_history_id)
        
        if not history_records:
            logger.info(f"ℹ️ No history changes found for user {user_id}")
            return {
                "message": "No changes to sync",
                "status": "completed",
                "user_id": user_id,
                "new_emails": 0,
                "updated_emails": 0,
                "deleted_emails": 0,
                "new_history_id": new_history_id
            }
        
        logger.info(f"📊 Found {len(history_records)} history records")
        
        added_count = 0
        updated_count = 0
        deleted_count = 0
        
        # Process each history record
        for record in history_records:
            # Handle messages added
            if 'messagesAdded' in record:
                for msg_added in record['messagesAdded']:
                    try:
                        message = msg_added.get('message', {})
                        message_id = message.get('id')
                        
                        # Fetch full message details
                        full_msg = service.users().messages().get(
                            userId='me',
                            id=message_id,
                            format='full'
                        ).execute()
                        
                        # Parse and store (similar to regular sync)
                        headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
                        body = decode_email_body(full_msg.get('payload', {}))
                        
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
                        
                        # Check if exists
                        existing = auth_supabase.table('emails')\
                            .select('id')\
                            .eq('user_id', user_id)\
                            .eq('external_id', message_id)\
                            .execute()
                        
                        to_addresses = [addr.strip() for addr in headers.get('to', '').split(',')] if headers.get('to') else []
                        cc_addresses = [addr.strip() for addr in headers.get('cc', '').split(',')] if headers.get('cc') else []
                        
                        # Use plain text body, or HTML if plain not available
                        body_content = body.get('plain') or body.get('html', '')
                        
                        email_data = {
                            'user_id': user_id,
                            'ext_connection_id': connection_id,
                            'external_id': message_id,
                            'thread_id': thread_id,
                            'subject': headers.get('subject', '(No Subject)'),
                            'from': headers.get('from', ''),
                            'to': to_addresses,
                            'cc': cc_addresses if cc_addresses else None,
                            'body': body_content,
                            'snippet': snippet,
                            'labels': labels,
                            'is_read': not is_unread,
                            'is_starred': is_starred,
                            'is_draft': is_draft,
                            'received_at': received_at,
                            'has_attachments': len(attachments) > 0,
                            'attachments': attachments,
                            'synced_at': datetime.now(timezone.utc).isoformat(),
                            'raw_item': full_msg
                        }
                        
                        if existing.data:
                            auth_supabase.table('emails')\
                                .update(email_data)\
                                .eq('id', existing.data[0]['id'])\
                                .execute()
                            updated_count += 1
                        else:
                            auth_supabase.table('emails')\
                                .insert(email_data)\
                                .execute()
                            added_count += 1
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing added message: {str(e)}")
                        continue
            
            # Handle messages deleted
            if 'messagesDeleted' in record:
                for msg_deleted in record['messagesDeleted']:
                    try:
                        message = msg_deleted.get('message', {})
                        message_id = message.get('id')
                        
                        # Mark as deleted or remove from database
                        result = auth_supabase.table('emails')\
                            .delete()\
                            .eq('user_id', user_id)\
                            .eq('external_id', message_id)\
                            .execute()
                        
                        if result.data:
                            deleted_count += 1
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing deleted message: {str(e)}")
                        continue
            
            # Handle label changes
            if 'labelsAdded' in record or 'labelsRemoved' in record:
                # For label changes, we need to update the labels array
                try:
                    if 'labelsAdded' in record:
                        for label_change in record['labelsAdded']:
                            message_id = label_change.get('message', {}).get('id')
                            label_ids = label_change.get('labelIds', [])
                            
                            # Get current email
                            existing = auth_supabase.table('emails')\
                                .select('labels')\
                                .eq('user_id', user_id)\
                                .eq('external_id', message_id)\
                                .execute()
                            
                            if existing.data:
                                current_labels = existing.data[0].get('labels', [])
                                new_labels = list(set(current_labels + label_ids))
                                
                                # Update read/starred status based on labels
                                is_read = 'UNREAD' not in new_labels
                                is_starred = 'STARRED' in new_labels
                                
                                auth_supabase.table('emails')\
                                    .update({
                                        'labels': new_labels,
                                        'is_read': is_read,
                                        'is_starred': is_starred
                                    })\
                                    .eq('user_id', user_id)\
                                    .eq('external_id', message_id)\
                                    .execute()
                                updated_count += 1
                    
                    if 'labelsRemoved' in record:
                        for label_change in record['labelsRemoved']:
                            message_id = label_change.get('message', {}).get('id')
                            label_ids = label_change.get('labelIds', [])
                            
                            existing = auth_supabase.table('emails')\
                                .select('labels')\
                                .eq('user_id', user_id)\
                                .eq('external_id', message_id)\
                                .execute()
                            
                            if existing.data:
                                current_labels = existing.data[0].get('labels', [])
                                new_labels = [l for l in current_labels if l not in label_ids]
                                
                                is_read = 'UNREAD' not in new_labels
                                is_starred = 'STARRED' in new_labels
                                
                                auth_supabase.table('emails')\
                                    .update({
                                        'labels': new_labels,
                                        'is_read': is_read,
                                        'is_starred': is_starred
                                    })\
                                    .eq('user_id', user_id)\
                                    .eq('external_id', message_id)\
                                    .execute()
                                updated_count += 1
                                
                except Exception as e:
                    logger.error(f"❌ Error processing label changes: {str(e)}")
                    continue
        
        # Update last synced timestamp and history ID
        auth_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        # Update history ID in push subscription
        auth_supabase.table('push_subscriptions')\
            .update({
                'history_id': new_history_id,
                'last_notification_at': datetime.now(timezone.utc).isoformat()
            })\
            .eq('user_id', user_id)\
            .eq('provider', 'gmail')\
            .eq('is_active', True)\
            .execute()
        
        logger.info(f"✅ History sync completed: {added_count} added, {updated_count} updated, {deleted_count} deleted")
        
        return {
            "message": "History sync completed successfully",
            "status": "completed",
            "user_id": user_id,
            "new_emails": added_count,
            "updated_emails": updated_count,
            "deleted_emails": deleted_count,
            "new_history_id": new_history_id
        }
        
    except HttpError as e:
        logger.error(f"❌ Gmail API error during history sync: {str(e)}")
        raise ValueError(f"Failed to sync Gmail history: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error syncing Gmail history: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise ValueError(f"Gmail history sync failed: {str(e)}")

