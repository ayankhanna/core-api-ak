"""
Email service - Create draft operations
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


def create_draft(
    user_id: str,
    user_jwt: str,
    to: str = None,
    subject: str = "",
    body: str = "",
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    html_body: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a draft email in Gmail (two-way sync with database)
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        to: Optional recipient email address
        subject: Email subject (default empty)
        body: Plain text email body (default empty)
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        html_body: Optional HTML version of email body
        
    Returns:
        Dict with draft details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Create MIME message
        # For drafts, 'to' can be empty
        message = create_message(
            to=to or "",
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            html_body=html_body
        )
        
        # Create draft in Gmail
        draft_body = {'message': message}
        draft = service.users().drafts().create(
            userId='me',
            body=draft_body
        ).execute()
        
        draft_id = draft.get('id')
        message_data = draft.get('message', {})
        message_id = message_data.get('id')
        thread_id = message_data.get('threadId')
        
        logger.info(f"✅ Created draft {draft_id} for user {user_id}")
        
        # Store in database
        to_addresses = [to] if to else []
        
        db_data = {
            'user_id': user_id,
            'ext_connection_id': connection_id,
            'external_id': message_id,
            'thread_id': thread_id,
            'subject': subject,
            'from_address': '',  # Drafts don't have from until sent
            'to_addresses': to_addresses,
            'cc_addresses': cc if cc else None,
            'body_text': body,
            'body_html': html_body,
            'snippet': body[:100] if body else '',
            'labels': ['DRAFT'],
            'is_read': True,
            'received_at': datetime.now(timezone.utc).isoformat(),
            'metadata': {
                'draft_id': draft_id,
                'raw_item': draft
            }
        }
        
        # Check if draft already exists in DB
        existing = auth_supabase.table('emails')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('external_id', message_id)\
            .execute()
        
        if existing.data:
            # Update existing
            result = auth_supabase.table('emails')\
                .update(db_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
        else:
            # Insert new
            result = auth_supabase.table('emails')\
                .insert(db_data)\
                .execute()
        
        return {
            "message": "Draft created successfully",
            "draft": {
                'id': draft_id,
                'message_id': message_id,
                'thread_id': thread_id,
                'to': to,
                'subject': subject,
                'body': body,
                'labels': message_data.get('labelIds', ['DRAFT'])
            },
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to create draft: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating draft: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to create draft: {str(e)}")


def get_draft(
    user_id: str,
    user_jwt: str,
    draft_id: str
) -> Dict[str, Any]:
    """
    Get a specific draft by ID
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        draft_id: Gmail draft ID
        
    Returns:
        Dict with draft details
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        draft = service.users().drafts().get(
            userId='me',
            id=draft_id,
            format='full'
        ).execute()
        
        from .google_api_helpers import parse_email_headers, decode_email_body
        
        message = draft.get('message', {})
        headers = parse_email_headers(message.get('payload', {}).get('headers', []))
        body = decode_email_body(message.get('payload', {}))
        
        return {
            "message": "Draft retrieved successfully",
            "draft": {
                'id': draft.get('id'),
                'message_id': message.get('id'),
                'thread_id': message.get('threadId'),
                'subject': headers.get('subject', ''),
                'to': headers.get('to', ''),
                'cc': headers.get('cc'),
                'bcc': headers.get('bcc'),
                'body_plain': body.get('plain', ''),
                'body_html': body.get('html', ''),
                'snippet': message.get('snippet', ''),
                'labels': message.get('labelIds', [])
            }
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to get draft: {str(e)}")


def list_drafts(
    user_id: str,
    user_jwt: str,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    List all draft emails
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of drafts to return (default 50)
        
    Returns:
        Dict with list of drafts
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        drafts_result = service.users().drafts().list(
            userId='me',
            maxResults=max_results
        ).execute()
        
        drafts = drafts_result.get('drafts', [])
        
        return {
            "message": f"Retrieved {len(drafts)} drafts",
            "drafts": [{'id': d['id'], 'message_id': d.get('message', {}).get('id')} for d in drafts],
            "count": len(drafts)
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to list drafts: {str(e)}")

