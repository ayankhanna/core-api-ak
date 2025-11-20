"""
Email service - Archive email operations
"""
from typing import Dict, Any
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_gmail_service

logger = logging.getLogger(__name__)


def archive_email(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Archive an email (remove from inbox but keep accessible)
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to archive
        
    Returns:
        Dict with archive confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Archive = remove INBOX label
        archived = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': ['INBOX']}
        ).execute()
        
        labels = archived.get('labelIds', [])
        
        logger.info(f"✅ Archived email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email archived successfully",
            "email_id": email_id,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to archive email: {str(e)}")
    except Exception as e:
        logger.error(f"Error archiving email: {str(e)}")
        raise ValueError(f"Failed to archive email: {str(e)}")


def unarchive_email(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Unarchive an email (move back to inbox)
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to unarchive
        
    Returns:
        Dict with unarchive confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Unarchive = add INBOX label
        unarchived = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': ['INBOX']}
        ).execute()
        
        labels = unarchived.get('labelIds', [])
        
        logger.info(f"✅ Unarchived email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email moved back to inbox successfully",
            "email_id": email_id,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to unarchive email: {str(e)}")
    except Exception as e:
        logger.error(f"Error unarchiving email: {str(e)}")
        raise ValueError(f"Failed to unarchive email: {str(e)}")

