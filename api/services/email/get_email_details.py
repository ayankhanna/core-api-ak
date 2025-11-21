"""
Email service - Get full email details
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import (
    get_gmail_service,
    parse_email_headers,
    decode_email_body,
    get_attachment_info
)

logger = logging.getLogger(__name__)


def get_email_details(
    user_id: str,
    user_jwt: str,
    email_id: str,
    format: str = 'full'
) -> Dict[str, Any]:
    """
    Get full details of a specific email including body content
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID
        format: Message format ('full', 'metadata', 'minimal', 'raw')
                - full: Complete message with body
                - metadata: Headers only, no body
                - minimal: Subject, from, to only
                - raw: Raw MIME message
        
    Returns:
        Dict with complete email details including body content
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Fetch full message details
        full_msg = service.users().messages().get(
            userId='me',
            id=email_id,
            format=format
        ).execute()
        
        # Parse headers
        headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
        
        # Get basic info
        snippet = full_msg.get('snippet', '')
        labels = full_msg.get('labelIds', [])
        thread_id = full_msg.get('threadId')
        internal_date = full_msg.get('internalDate')
        size_estimate = full_msg.get('sizeEstimate', 0)
        
        # Decode body content
        body = decode_email_body(full_msg.get('payload', {}))
        
        # Get attachments info
        attachments = get_attachment_info(full_msg.get('payload', {}))
        
        # Check various flags
        is_unread = 'UNREAD' in labels
        is_starred = 'STARRED' in labels
        is_important = 'IMPORTANT' in labels
        is_draft = 'DRAFT' in labels
        
        email_details = {
            'id': email_id,
            'thread_id': thread_id,
            'subject': headers.get('subject', '(No Subject)'),
            'from': headers.get('from', ''),
            'to': headers.get('to', ''),
            'cc': headers.get('cc'),
            'bcc': headers.get('bcc'),
            'date': headers.get('date'),
            'message_id': headers.get('message-id'),
            'in_reply_to': headers.get('in-reply-to'),
            'references': headers.get('references'),
            'snippet': snippet,
            'body_plain': body.get('plain', ''),
            'body_html': body.get('html', ''),
            'labels': labels,
            'is_unread': is_unread,
            'is_starred': is_starred,
            'is_important': is_important,
            'is_draft': is_draft,
            'internal_date': internal_date,
            'size_estimate': size_estimate,
            'attachments': attachments,
            'has_attachments': len(attachments) > 0,
            'raw_item': full_msg  # Store complete raw data
        }
        
        # Store/update in database for caching
        existing = auth_supabase.table('emails')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        # Parse addresses into arrays
        to_addresses = [addr.strip() for addr in email_details['to'].split(',')] if email_details['to'] else []
        cc_addresses = [addr.strip() for addr in email_details.get('cc', '').split(',')] if email_details.get('cc') else []
        bcc_addresses = [addr.strip() for addr in email_details.get('bcc', '').split(',')] if email_details.get('bcc') else []
        
        # Convert internal date to received_at
        if internal_date:
            received_at = datetime.fromtimestamp(
                int(internal_date) / 1000,
                tz=timezone.utc
            ).isoformat()
        else:
            # Fallback to current time if no internal date
            received_at = datetime.now(timezone.utc).isoformat()
        
        # Use plain text body, or HTML if plain not available
        body_content = body.get('plain') or body.get('html', '')
        
        db_data = {
            'user_id': user_id,
            'ext_connection_id': connection_id,
            'external_id': email_id,
            'thread_id': thread_id,
            'subject': email_details['subject'],
            'from': email_details['from'],
            'to': to_addresses,
            'cc': cc_addresses if cc_addresses else None,
            'bcc': bcc_addresses if bcc_addresses else None,
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
            # Update existing
            auth_supabase.table('emails')\
                .update(db_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Insert new
            auth_supabase.table('emails')\
                .insert(db_data)\
                .execute()
        
        logger.info(f"Retrieved email details for message {email_id}")
        
        return {
            "message": "Email details retrieved successfully",
            "email": email_details
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to get email details: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting email details: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to retrieve email: {str(e)}")


def get_email_attachment(
    user_id: str,
    user_jwt: str,
    email_id: str,
    attachment_id: str
) -> Dict[str, Any]:
    """
    Get a specific email attachment
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID
        attachment_id: Attachment ID from Gmail
        
    Returns:
        Dict with attachment data (base64 encoded)
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        attachment = service.users().messages().attachments().get(
            userId='me',
            messageId=email_id,
            id=attachment_id
        ).execute()
        
        return {
            "message": "Attachment retrieved successfully",
            "attachment": {
                'attachmentId': attachment_id,
                'data': attachment.get('data'),  # Base64url encoded
                'size': attachment.get('size', 0)
            }
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to get attachment: {str(e)}")

