"""
Email service - Mark as read/unread operations
"""
from typing import Dict, Any
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_gmail_service

logger = logging.getLogger(__name__)


def mark_as_read(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Mark an email as read
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to mark as read
        
    Returns:
        Dict with confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Mark as read = remove UNREAD label
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Marked email {email_id} as read for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'is_read': True,
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email marked as read successfully",
            "email_id": email_id,
            "is_read": True,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to mark email as read: {str(e)}")
    except Exception as e:
        logger.error(f"Error marking email as read: {str(e)}")
        raise ValueError(f"Failed to mark as read: {str(e)}")


def mark_as_unread(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Mark an email as unread
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to mark as unread
        
    Returns:
        Dict with confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Mark as unread = add UNREAD label
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        
        labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Marked email {email_id} as unread for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'is_read': False,
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email marked as unread successfully",
            "email_id": email_id,
            "is_read": False,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to mark email as unread: {str(e)}")
    except Exception as e:
        logger.error(f"Error marking email as unread: {str(e)}")
        raise ValueError(f"Failed to mark as unread: {str(e)}")


def mark_as_starred(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Star an email
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to star
        
    Returns:
        Dict with confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Star = add STARRED label
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['STARRED']}
        ).execute()
        
        labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Starred email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'is_starred': True,
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email starred successfully",
            "email_id": email_id,
            "is_starred": True,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to star email: {str(e)}")


def unstar_email(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Unstar an email
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to unstar
        
    Returns:
        Dict with confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Unstar = remove STARRED label
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['STARRED']}
        ).execute()
        
        labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Unstarred email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'is_starred': False,
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email unstarred successfully",
            "email_id": email_id,
            "is_starred": False,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to unstar email: {str(e)}")

