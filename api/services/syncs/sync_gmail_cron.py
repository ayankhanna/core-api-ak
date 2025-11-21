"""
Gmail sync for cron jobs - bypasses RLS using service role
"""
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def sync_gmail_cron(
    gmail_service,
    connection_id: str,
    user_id: str,
    service_supabase,
    days_back: int = 7
) -> Dict[str, Any]:
    """
    Sync Gmail emails for cron jobs.
    Uses service role Supabase client to bypass RLS.
    
    Args:
        gmail_service: Gmail API service
        connection_id: External connection ID
        user_id: User's ID
        service_supabase: Service role Supabase client (bypasses RLS)
        days_back: Number of days back to sync (default 7)
    
    Returns:
        Dict with sync results
    """
    from api.services.email.google_api_helpers import (
        parse_email_headers,
        decode_email_body,
        get_attachment_info
    )
    
    try:
        # Get last sync time from connection
        connection = service_supabase.table('ext_connections')\
            .select('last_synced')\
            .eq('id', connection_id)\
            .single()\
            .execute()
        
        last_synced = connection.data.get('last_synced') if connection.data else None
        
        # Determine sync date
        if last_synced:
            # Parse last sync date and subtract 1 hour buffer for safety
            last_sync_dt = datetime.fromisoformat(last_synced.replace('Z', '+00:00'))
            sync_since_dt = last_sync_dt - timedelta(hours=1)
            sync_since = sync_since_dt.strftime('%Y/%m/%d')
        else:
            # First sync - get last N days
            sync_since_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
            sync_since = sync_since_dt.strftime('%Y/%m/%d')
        
        query = f"after:{sync_since}"
        logger.info(f"📧 Gmail query: {query}")
        
        synced_count = 0
        updated_count = 0
        error_count = 0
        page_token = None
        total_processed = 0
        
        # Handle pagination
        while True:
            # Fetch message list
            messages_result = gmail_service.users().messages().list(
                userId='me',
                maxResults=100,
                q=query,
                pageToken=page_token
            ).execute()
            
            messages = messages_result.get('messages', [])
            
            if not messages:
                break
            
            total_processed += len(messages)
            logger.info(f"📦 Processing {len(messages)} messages (total: {total_processed})")
            
            for msg in messages:
                try:
                    # Get full message details
                    full_msg = gmail_service.users().messages().get(
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
                    labels = full_msg.get('labelIds', [])
                    internal_date = full_msg.get('internalDate')
                    
                    # Convert internal date to ISO format
                    if internal_date:
                        received_at = datetime.fromtimestamp(
                            int(internal_date) / 1000,
                            tz=timezone.utc
                        ).isoformat()
                    else:
                        received_at = datetime.now(timezone.utc).isoformat()
                    
                    # Get attachments info
                    attachments = get_attachment_info(full_msg.get('payload', {}))
                    
                    # Check if email already exists
                    existing = service_supabase.table('emails')\
                        .select('id')\
                        .eq('user_id', user_id)\
                        .eq('external_id', message_id)\
                        .execute()
                    
                    # Parse to/cc/bcc into arrays
                    to_addrs = [addr.strip() for addr in headers.get('to', '').split(',')] if headers.get('to') else []
                    cc_addrs = [addr.strip() for addr in headers.get('cc', '').split(',')] if headers.get('cc') else []
                    bcc_addrs = [addr.strip() for addr in headers.get('bcc', '').split(',')] if headers.get('bcc') else []
                    
                    # Use plain text body, or HTML if plain not available
                    body_content = body.get('plain') or body.get('html', '')
                    
                    # Check if draft
                    is_draft = 'DRAFT' in labels
                    
                    email_data = {
                        'user_id': user_id,
                        'ext_connection_id': connection_id,
                        'external_id': message_id,
                        'thread_id': thread_id,
                        'subject': headers.get('subject', '(No subject)'),
                        'from': headers.get('from', ''),
                        'to': to_addrs,
                        'cc': cc_addrs if cc_addrs else None,
                        'bcc': bcc_addrs if bcc_addrs else None,
                        'body': body_content,
                        'received_at': received_at,
                        'labels': labels,
                        'is_read': 'UNREAD' not in labels,
                        'is_starred': 'STARRED' in labels,
                        'is_draft': is_draft,
                        'has_attachments': len(attachments) > 0,
                        'attachments': attachments if attachments else None,
                        'synced_at': datetime.now(timezone.utc).isoformat(),
                        'raw_item': full_msg  # Store full Gmail message
                    }
                    
                    if existing.data:
                        # Update existing email
                        service_supabase.table('emails')\
                            .update(email_data)\
                            .eq('id', existing.data[0]['id'])\
                            .execute()
                        updated_count += 1
                    else:
                        # Insert new email
                        service_supabase.table('emails')\
                            .insert(email_data)\
                            .execute()
                        synced_count += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error processing message {msg.get('id')}: {str(e)}")
                    error_count += 1
                    continue
            
            # Check if there are more pages
            page_token = messages_result.get('nextPageToken')
            if not page_token:
                break
            
            # Safety limit: stop after processing 500 messages in one cron run
            if total_processed >= 500:
                logger.warning(f"⚠️ Reached 500 message limit, stopping pagination")
                break
        
        # Update last synced timestamp
        service_supabase.table('ext_connections')\
            .update({'last_synced': datetime.now(timezone.utc).isoformat()})\
            .eq('id', connection_id)\
            .execute()
        
        logger.info(f"✅ Gmail sync complete: {synced_count} new, {updated_count} updated, {error_count} errors")
        
        return {
            "status": "success",
            "new_emails": synced_count,
            "updated_emails": updated_count,
            "total_emails": synced_count + updated_count,
            "error_count": error_count,
            "total_processed": total_processed
        }
        
    except HttpError as e:
        logger.error(f"❌ Gmail API error: {str(e)}")
        return {
            "status": "error",
            "error": f"Gmail API error: {str(e)}",
            "new_emails": 0,
            "updated_emails": 0
        }
    except Exception as e:
        logger.error(f"❌ Error syncing Gmail: {str(e)}")
        logger.exception("Full traceback:")
        return {
            "status": "error",
            "error": str(e),
            "new_emails": 0,
            "updated_emails": 0
        }

