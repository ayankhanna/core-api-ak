"""
Gmail API helper functions
Shared utilities for interacting with Gmail API
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from lib.supabase_client import get_authenticated_supabase_client
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


def get_gmail_service(user_id: str, user_jwt: str):
    """
    Get an authenticated Gmail API service instance
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Tuple of (service, connection_id) or (None, None) if no connection
    """
    try:
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        
        logger.info(f"🔍 Looking for Google connection for user {user_id}")
        
        # Get user's Google OAuth connection
        connection_result = auth_supabase.table('ext_connections')\
            .select('id, access_token, refresh_token, token_expires_at, metadata')\
            .eq('user_id', user_id)\
            .eq('provider', 'google')\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not connection_result.data:
            logger.warning(f"❌ No active Google connection found for user {user_id}")
            logger.info(f"💡 User needs to connect their Google account via OAuth")
            return None, None
        
        connection_data = connection_result.data
        connection_data['user_id'] = user_id
        connection_id = connection_data['id']
        
        logger.info(f"✅ Found Google connection (ID: {connection_id})")
        
        # Get valid access token (refresh if needed)
        access_token = _refresh_google_token_if_needed(connection_data)
        
        if not access_token:
            logger.error(f"❌ Unable to get valid access token for user {user_id}")
            logger.error(f"💡 Token may be expired or invalid. User should re-authenticate.")
            return None, None
        
        logger.info(f"✅ Got valid access token")
        
        # Build Gmail API client
        credentials = Credentials(token=access_token)
        service = build('gmail', 'v1', credentials=credentials)
        
        logger.info(f"✅ Built Gmail API service")
        
        return service, connection_id
        
    except Exception as e:
        logger.error(f"❌ Error getting Gmail service: {str(e)}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return None, None


def _refresh_google_token_if_needed(connection_data: Dict[str, Any]) -> Optional[str]:
    """
    Check if access token is expired and refresh if needed
    Returns the valid access token
    """
    token_expires_at = connection_data.get('token_expires_at')
    
    # If no expiry time, assume token is still valid
    if not token_expires_at:
        return connection_data.get('access_token')
    
    # Check if token is expired (with 5 minute buffer)
    expires_at = datetime.fromisoformat(token_expires_at.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    if expires_at > now + timedelta(minutes=5):
        # Token is still valid
        return connection_data.get('access_token')
    
    # Token expired, need to refresh
    refresh_token = connection_data.get('refresh_token')
    if not refresh_token:
        logger.error("No refresh token available")
        return None
    
    try:
        # Use Google's refresh flow
        from google.auth.transport.requests import Request
        from lib.supabase_client import supabase
        from api.config import settings
        
        # Get client credentials from metadata or fall back to settings
        metadata = connection_data.get('metadata', {})
        client_id = metadata.get('client_id') or settings.google_client_id
        client_secret = metadata.get('client_secret') or settings.google_client_secret
        
        if not client_id or not client_secret:
            logger.error("Missing Google OAuth client credentials (client_id or client_secret)")
            logger.error("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables")
            return None
        
        credentials = Credentials(
            token=connection_data.get('access_token'),
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_id,
            client_secret=client_secret
        )
        
        credentials.refresh(Request())
        
        # Update tokens in database
        new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
        supabase.table('ext_connections')\
            .update({
                'access_token': credentials.token,
                'token_expires_at': new_expires_at.isoformat()
            })\
            .eq('user_id', connection_data.get('user_id'))\
            .eq('provider', 'google')\
            .execute()
        
        logger.info("Successfully refreshed Google access token")
        return credentials.token
        
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        return None


def create_message(to: str, subject: str, body: str, from_email: str = None, 
                  cc: List[str] = None, bcc: List[str] = None, 
                  html_body: str = None) -> Dict[str, Any]:
    """
    Create a MIME message for sending via Gmail API
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text email body
        from_email: Optional sender email (defaults to authenticated user)
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        html_body: Optional HTML version of email body
        
    Returns:
        Dict with 'raw' key containing base64url-encoded message
    """
    # Create message container
    if html_body:
        message = MIMEMultipart('alternative')
    else:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        if from_email:
            message['from'] = from_email
        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}
    
    # For HTML emails
    message['to'] = to
    message['subject'] = subject
    if from_email:
        message['from'] = from_email
    if cc:
        message['cc'] = ', '.join(cc)
    if bcc:
        message['bcc'] = ', '.join(bcc)
    
    # Attach plain text and HTML parts
    part1 = MIMEText(body, 'plain')
    part2 = MIMEText(html_body, 'html')
    message.attach(part1)
    message.attach(part2)
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}


def parse_email_headers(headers: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Parse email headers into a more accessible dictionary
    
    Args:
        headers: List of header dicts from Gmail API
        
    Returns:
        Dict with common headers (From, To, Subject, Date, etc.)
    """
    parsed = {}
    for header in headers:
        name = header.get('name', '').lower()
        value = header.get('value', '')
        
        if name in ['from', 'to', 'subject', 'date', 'cc', 'bcc', 'message-id', 'in-reply-to', 'references']:
            parsed[name] = value
    
    return parsed


def decode_email_body(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Decode email body from Gmail API payload
    
    Args:
        payload: Email payload from Gmail API
        
    Returns:
        Dict with 'plain' and 'html' keys containing decoded body content
    """
    result = {'plain': '', 'html': ''}
    
    def get_body_from_part(part: Dict[str, Any]) -> None:
        """Recursively extract body from message parts"""
        mime_type = part.get('mimeType', '')
        
        if mime_type == 'text/plain':
            body_data = part.get('body', {}).get('data')
            if body_data:
                result['plain'] = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        elif mime_type == 'text/html':
            body_data = part.get('body', {}).get('data')
            if body_data:
                result['html'] = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        elif mime_type.startswith('multipart/'):
            # Recursively process multipart messages
            for subpart in part.get('parts', []):
                get_body_from_part(subpart)
    
    # Start processing from top-level payload
    if 'parts' in payload:
        for part in payload['parts']:
            get_body_from_part(part)
    else:
        # Single-part message
        get_body_from_part(payload)
    
    return result


def get_attachment_info(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract attachment information from email payload
    
    Args:
        payload: Email payload from Gmail API
        
    Returns:
        List of attachment info dicts with filename, mimeType, size, attachmentId
    """
    attachments = []
    
    def extract_attachments(part: Dict[str, Any]) -> None:
        """Recursively extract attachment info"""
        filename = part.get('filename')
        body = part.get('body', {})
        
        if filename and body.get('attachmentId'):
            attachments.append({
                'filename': filename,
                'mimeType': part.get('mimeType'),
                'size': body.get('size', 0),
                'attachmentId': body.get('attachmentId')
            })
        
        # Process nested parts
        for subpart in part.get('parts', []):
            extract_attachments(subpart)
    
    extract_attachments(payload)
    return attachments


def convert_to_gmail_label_ids(label_names: List[str], service) -> List[str]:
    """
    Convert label names to Gmail label IDs
    
    Args:
        label_names: List of label names (e.g., ['INBOX', 'IMPORTANT'])
        service: Gmail API service instance
        
    Returns:
        List of label IDs
    """
    # System labels are uppercase and can be used directly
    system_labels = ['INBOX', 'SPAM', 'TRASH', 'UNREAD', 'STARRED', 'IMPORTANT', 
                     'SENT', 'DRAFT', 'CATEGORY_PERSONAL', 'CATEGORY_SOCIAL', 
                     'CATEGORY_PROMOTIONS', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS']
    
    label_ids = []
    
    # Get all labels to find custom label IDs
    labels_result = service.users().labels().list(userId='me').execute()
    all_labels = labels_result.get('labels', [])
    
    # Create mapping of name to ID
    label_map = {label['name']: label['id'] for label in all_labels}
    
    for name in label_names:
        if name.upper() in system_labels:
            label_ids.append(name.upper())
        elif name in label_map:
            label_ids.append(label_map[name])
        else:
            logger.warning(f"Label '{name}' not found")
    
    return label_ids



