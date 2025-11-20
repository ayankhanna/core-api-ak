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
    Fetch emails from database first (smart caching), then fallback to Gmail.
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        max_results: Maximum number of emails to fetch (default 50)
        query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
        label_ids: Filter by specific label IDs (e.g., ['INBOX', 'IMPORTANT'])
        include_spam_trash: Whether to include spam and trash (default False)
        
    Returns:
        Dict with emails list and metadata
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Smart Cache Strategy:
    # 1. If no complex query is present, try fetching from DB first (fastest)
    # 2. If DB returns results, return them immediately
    # 3. If DB empty or complex query, fall back to Gmail API
    
    if not query:
        try:
            logger.info(f"🔍 Checking email cache for user {user_id}")
            
            # Build DB query
            db_query = auth_supabase.table('emails')\
                .select('*')\
                .eq('user_id', user_id)
            
            # Apply label filtering if needed
            if label_ids:
                # Filter by labels (array containment)
                # Note: This requires the 'labels' column to be an array or JSONB
                for label in label_ids:
                    db_query = db_query.cs('labels', [label])
            elif not include_spam_trash:
                # Default filtering: Exclude trash and spam if not explicitly requested
                # Note: Negation might be tricky in all client versions, 
                # so we rely on the fact that sync usually handles what's in DB.
                # But ideally we would do: .not_.cs('labels', ['TRASH', 'SPAM'])
                pass
            
            # Order by received_at desc
            db_query = db_query.order('received_at', desc=True).limit(max_results)
            
            response = db_query.execute()
            cached_emails = response.data
            
            if cached_emails:
                logger.info(f"✅ Found {len(cached_emails)} cached emails")
                
                # Map DB format to API format
                mapped_emails = []
                for e in cached_emails:
                    # Handle array vs string fields safely
                    to_addr = e.get('to_addresses', [])
                    if isinstance(to_addr, list):
                        to_str = ', '.join(to_addr)
                    else:
                        to_str = str(to_addr or '')
                        
                    cc_addr = e.get('cc_addresses', [])
                    if isinstance(cc_addr, list):
                        cc_str = ', '.join(cc_addr)
                    else:
                        cc_str = str(cc_addr or '')
                        
                    mapped_emails.append({
                        'external_id': e['external_id'],
                        'thread_id': e.get('thread_id'),
                        'subject': e.get('subject', '(No Subject)'),
                        'from': e.get('from_address', ''),
                        'to': to_str,
                        'cc': cc_str,
                        'snippet': e.get('snippet', ''),
                        'labels': e.get('labels', []),
                        'is_unread': not e.get('is_read', True),
                        'received_at': e.get('received_at'),
                        'has_attachments': e.get('metadata', {}).get('has_attachments', False),
                        'attachment_count': len(e.get('metadata', {}).get('attachments', [])),
                        'source': 'cache' # Debug flag
                    })
                
                return {
                    "emails": mapped_emails,
                    "count": len(mapped_emails),
                    "message": "Fetched from cache"
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Cache lookup failed: {str(e)}. Falling back to Gmail API.")
            # Continue to Gmail API fallback
    
    # =========================================================================
    # Fallback: Fetch directly from Gmail API
    # =========================================================================
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        logger.info(f"🌍 Fetching fresh emails from Gmail API (Query: {query})")
        
        # Build list request
        list_params = {
            'userId': 'me',
            'maxResults': max_results,
            'includeSpamTrash': include_spam_trash
        }
        
        if query:
            list_params['q'] = query
        
        if label_ids:
            list_params['labelIds'] = label_ids
        
        # Fetch message list
        messages_result = service.users().messages().list(**list_params).execute()
        messages = messages_result.get('messages', [])
        
        if not messages:
            return {
                "emails": [],
                "count": 0,
                "message": "No emails found"
            }
        
        # Fetch metadata for each message
        emails = []
        for msg in messages:
            try:
                # Get message metadata only (efficient - no body content)
                full_msg = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date']
                ).execute()
                
                # Parse headers
                headers = parse_email_headers(full_msg.get('payload', {}).get('headers', []))
                
                # Get snippet and labels
                snippet = full_msg.get('snippet', '')
                labels = full_msg.get('labelIds', [])
                
                # Get thread ID and internal date
                thread_id = full_msg.get('threadId')
                internal_date = full_msg.get('internalDate')
                
                # Convert internal date to ISO format
                if internal_date:
                    received_at = datetime.fromtimestamp(
                        int(internal_date) / 1000,
                        tz=timezone.utc
                    ).isoformat()
                else:
                    # Fallback to current time if no internal date
                    received_at = datetime.now(timezone.utc).isoformat()
                
                # Check if read/unread
                is_unread = 'UNREAD' in labels
                
                # Get attachment info
                attachments = get_attachment_info(full_msg.get('payload', {}))
                has_attachments = len(attachments) > 0
                
                email_data = {
                    'external_id': msg['id'],
                    'thread_id': thread_id,
                    'subject': headers.get('subject', '(No Subject)'),
                    'from': headers.get('from', ''),
                    'to': headers.get('to', ''),
                    'cc': headers.get('cc'),
                    'snippet': snippet,
                    'labels': labels,
                    'is_unread': is_unread,
                    'received_at': received_at,
                    'has_attachments': has_attachments,
                    'attachment_count': len(attachments),
                    'source': 'gmail_api'
                }
                
                emails.append(email_data)
                
            except HttpError as e:
                logger.error(f"Error fetching message {msg['id']}: {str(e)}")
                continue
        
        logger.info(f"Fetched {len(emails)} emails from Gmail for user {user_id}")
        
        return {
            "emails": emails,
            "count": len(emails),
            "message": f"Successfully fetched {len(emails)} emails"
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to fetch emails: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching emails: {str(e)}")
        raise ValueError(f"Email fetch failed: {str(e)}")


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
