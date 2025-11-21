"""
Email service - Fetch operations for emails
"""
from typing import Optional, Dict, Any, List
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


def fetch_emails(
    user_id: str,
    user_jwt: str,
    max_results: int = 50,
    query: Optional[str] = None,
    label_ids: Optional[List[str]] = None,
    include_spam_trash: bool = False
) -> Dict[str, Any]:
    """
    Fetch emails from database ONLY - no Gmail API fallback.
    
    This ensures fast performance by only reading from our synced database.
    If no emails are found, user should trigger a manual sync.
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of emails to fetch (default 50)
        query: Search query (currently only DB search, not Gmail query)
        label_ids: Filter by specific label IDs (e.g., ['INBOX', 'IMPORTANT'])
        include_spam_trash: Whether to include spam and trash (default False)
        
    Returns:
        Dict with emails list and metadata
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        logger.info(f"📧 Fetching emails from database for user {user_id[:8]}...")
        
        # Build DB query
        db_query = auth_supabase.table('emails')\
            .select('*')\
            .eq('user_id', user_id)
        
        # Apply label filtering if needed
        if label_ids:
            # Filter by labels (array containment)
            for label in label_ids:
                db_query = db_query.cs('labels', [label])
        elif not include_spam_trash:
            # Default: show inbox emails (filter out TRASH and SPAM)
            # This is a simple approach - we could enhance this later
            pass
        
        # Text search in subject/from if query is provided
        if query:
            # Simple text search in subject and from
            # For production, consider using PostgreSQL full-text search
            db_query = db_query.or_(f'subject.ilike.%{query}%,from.ilike.%{query}%')
        
        # Order by received_at desc
        db_query = db_query.order('received_at', desc=True).limit(max_results)
        
        response = db_query.execute()
        cached_emails = response.data or []
        
        logger.info(f"✅ Found {len(cached_emails)} emails in database")
        
        # Map DB format to API format
        mapped_emails = []
        for e in cached_emails:
            # Handle array fields
            to_field = e.get('to', [])
            if isinstance(to_field, list):
                to_str = ', '.join(to_field)
            else:
                to_str = str(to_field or '')
                
            cc_field = e.get('cc', [])
            if isinstance(cc_field, list):
                cc_str = ', '.join(cc_field)
            else:
                cc_str = str(cc_field or '')
                
                mapped_emails.append({
                    'external_id': e['external_id'],
                    'thread_id': e.get('thread_id'),
                    'subject': e.get('subject', '(No Subject)'),
                    'from': e.get('from', ''),
                    'to': to_str,
                    'cc': cc_str,
                    'snippet': e.get('snippet', ''),
                    'labels': e.get('labels', []),
                    'is_unread': not e.get('is_read', True),
                    'received_at': e.get('received_at'),
                    'has_attachments': e.get('has_attachments', False),
                    'attachment_count': len(e.get('attachments', [])),
                    'source': 'database'
                })
        
        return {
            "emails": mapped_emails,
            "count": len(mapped_emails),
            "message": "Fetched from database"
        }
            
    except Exception as e:
        logger.error(f"❌ Error fetching emails from database: {str(e)}")
        # Return empty list rather than failing
        return {
            "emails": [],
            "count": 0,
            "message": f"Error fetching emails: {str(e)}"
        }


def get_email_by_id(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get a specific email by ID from database or Gmail
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID
        
    Returns:
        Email data dict or None if not found
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # First try to get from database
    result = auth_supabase.table('emails')\
        .select('*')\
        .eq('user_id', user_id)\
        .eq('external_id', email_id)\
        .single()\
        .execute()
    
    if result.data:
        return result.data
    
    # If not in database, fetch from Gmail
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        return None
    
    try:
        # Get metadata only (efficient - no body content)
        full_msg = service.users().messages().get(
            userId='me',
            id=email_id,
            format='metadata',
            metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date']
        ).execute()
        
        # Parse and return email data
        headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
        labels = full_msg.get('labelIds', [])
        
        return {
            'external_id': email_id,
            'thread_id': full_msg.get('threadId'),
            'subject': headers.get('subject', '(No Subject)'),
            'from': headers.get('from', ''),
            'to': headers.get('to', ''),
            'cc': headers.get('cc'),
            'snippet': full_msg.get('snippet', ''),
            'labels': labels,
            'is_unread': 'UNREAD' in labels,
            'raw_item': full_msg
        }
        
    except HttpError as e:
        logger.error(f"Error fetching email {email_id}: {str(e)}")
        return None


def search_emails(
    user_id: str,
    user_jwt: str,
    search_query: str,
    max_results: int = 25
) -> Dict[str, Any]:
    """
    Search emails using Gmail search syntax
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        search_query: Gmail search query (e.g., 'subject:invoice', 'from:boss@company.com')
        max_results: Maximum number of results (default 25)
        
    Returns:
        Dict with matching emails
    """
    return fetch_emails(
        user_id=user_id,
        user_jwt=user_jwt,
        max_results=max_results,
        query=search_query
    )


def get_unread_emails(
    user_id: str,
    user_jwt: str,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Get unread emails for a user
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of emails (default 50)
        
    Returns:
        Dict with unread emails
    """
    return fetch_emails(
        user_id=user_id,
        user_jwt=user_jwt,
        max_results=max_results,
        label_ids=['UNREAD']
    )


def get_inbox_emails(
    user_id: str,
    user_jwt: str,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Get inbox emails for a user
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of emails (default 50)
        
    Returns:
        Dict with inbox emails
    """
    return fetch_emails(
        user_id=user_id,
        user_jwt=user_jwt,
        max_results=max_results,
        label_ids=['INBOX']
    )
