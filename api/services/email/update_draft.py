"""
Email service - Update draft operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import (
    get_gmail_service,
    create_message
)

logger = logging.getLogger(__name__)


def update_draft(
    user_id: str,
    user_jwt: str,
    draft_id: str,
    to: Optional[str] = None,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing draft email (two-way sync with database)
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        draft_id: Gmail draft ID to update
        to: Optional recipient email address (if changing)
        subject: Optional email subject (if changing)
        body: Optional plain text body (if changing)
        cc: Optional list of CC recipients (if changing)
        bcc: Optional list of BCC recipients (if changing)
        html_body: Optional HTML body (if changing)
        
    Returns:
        Dict with updated draft details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Get existing draft to merge with updates
        existing_draft = service.users().drafts().get(
            userId='me',
            id=draft_id,
            format='full'
        ).execute()
        
        from .google_api_helpers import parse_email_headers, decode_email_body
        
        existing_message = existing_draft.get('message', {})
        existing_headers = parse_email_headers(existing_message.get('payload', {}).get('headers', []))
        existing_body = decode_email_body(existing_message.get('payload', {}))
        
        # Merge updates with existing data
        final_to = to if to is not None else existing_headers.get('to', '')
        final_subject = subject if subject is not None else existing_headers.get('subject', '')
        final_body = body if body is not None else existing_body.get('plain', '')
        final_html = html_body if html_body is not None else existing_body.get('html')
        
        # CC and BCC handling
        if cc is not None:
            final_cc = cc
        else:
            existing_cc = existing_headers.get('cc', '')
            final_cc = existing_cc.split(', ') if existing_cc else None
        
        if bcc is not None:
            final_bcc = bcc
        else:
            existing_bcc = existing_headers.get('bcc', '')
            final_bcc = existing_bcc.split(', ') if existing_bcc else None
        
        # Create updated MIME message
        message = create_message(
            to=final_to,
            subject=final_subject,
            body=final_body,
            cc=final_cc,
            bcc=final_bcc,
            html_body=final_html
        )
        
        # Update draft in Gmail
        draft_body = {'message': message}
        updated_draft = service.users().drafts().update(
            userId='me',
            id=draft_id,
            body=draft_body
        ).execute()
        
        updated_message = updated_draft.get('message', {})
        message_id = updated_message.get('id')
        thread_id = updated_message.get('threadId')
        
        logger.info(f"✅ Updated draft {draft_id} for user {user_id}")
        
        # Update in database
        to_addresses = [final_to] if final_to else []
        
        db_data = {
            'subject': final_subject,
            'to_addresses': to_addresses,
            'cc_addresses': final_cc if final_cc else None,
            'body_text': final_body,
            'body_html': final_html,
            'snippet': final_body[:100] if final_body else '',
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {'raw_item': updated_draft}
        }
        
        # Update in database by external_id
        auth_supabase.table('emails')\
            .update(db_data)\
            .eq('user_id', user_id)\
            .eq('external_id', draft_id)\
            .execute()
        
        return {
            "message": "Draft updated successfully",
            "draft": {
                'id': draft_id,
                'message_id': message_id,
                'thread_id': thread_id,
                'to': final_to,
                'subject': final_subject,
                'body': final_body,
                'labels': updated_message.get('labelIds', ['DRAFT'])
            },
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to update draft: {str(e)}")
    except Exception as e:
        logger.error(f"Error updating draft: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to update draft: {str(e)}")


def send_draft(
    user_id: str,
    user_jwt: str,
    draft_id: str
) -> Dict[str, Any]:
    """
    Send an existing draft email
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        draft_id: Gmail draft ID to send
        
    Returns:
        Dict with sent email details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Send the draft
        sent_draft = service.users().drafts().send(
            userId='me',
            body={'id': draft_id}
        ).execute()
        
        message_id = sent_draft.get('id')
        thread_id = sent_draft.get('threadId')
        labels = sent_draft.get('labelIds', [])
        
        logger.info(f"✅ Sent draft {draft_id} as message {message_id} for user {user_id}")
        
        # Update in database - change from draft to sent
        auth_supabase.table('emails')\
            .update({
                'labels': labels,
                'received_at': datetime.now(timezone.utc).isoformat(),
                'metadata': {'raw_item': sent_draft}
            })\
            .eq('user_id', user_id)\
            .eq('external_id', draft_id)\
            .execute()
        
        return {
            "message": "Draft sent successfully",
            "email": {
                'id': message_id,
                'thread_id': thread_id,
                'labels': labels
            }
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to send draft: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending draft: {str(e)}")
        raise ValueError(f"Failed to send draft: {str(e)}")

