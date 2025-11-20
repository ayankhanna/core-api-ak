"""
Email service - Delete email operations
"""
from typing import Dict, Any
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_gmail_service

logger = logging.getLogger(__name__)


def delete_email(
    user_id: str,
    user_jwt: str,
    email_id: str,
    permanently: bool = False
) -> Dict[str, Any]:
    """
    Delete an email (move to trash or permanently delete)
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to delete
        permanently: If True, permanently delete; if False, move to trash (default False)
        
    Returns:
        Dict with deletion confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        if permanently:
            # Permanently delete the message
            service.users().messages().delete(
                userId='me',
                id=email_id
            ).execute()
            
            logger.info(f"✅ Permanently deleted email {email_id} for user {user_id}")
            
            # Delete from database
            auth_supabase.table('emails')\
                .delete()\
                .eq('user_id', user_id)\
                .eq('external_id', email_id)\
                .execute()
            
            return {
                "message": "Email permanently deleted successfully",
                "email_id": email_id,
                "permanently_deleted": True,
                "synced_to_google": True
            }
        else:
            # Move to trash (add TRASH label, remove INBOX)
            service.users().messages().trash(
                userId='me',
                id=email_id
            ).execute()
            
            logger.info(f"✅ Moved email {email_id} to trash for user {user_id}")
            
            # Update in database
            auth_supabase.table('emails')\
                .update({
                    'labels': ['TRASH']
                })\
                .eq('user_id', user_id)\
                .eq('external_id', email_id)\
                .execute()
            
            return {
                "message": "Email moved to trash successfully",
                "email_id": email_id,
                "permanently_deleted": False,
                "synced_to_google": True
            }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to delete email: {str(e)}")
    except Exception as e:
        logger.error(f"Error deleting email: {str(e)}")
        raise ValueError(f"Failed to delete email: {str(e)}")


def restore_email(
    user_id: str,
    user_jwt: str,
    email_id: str
) -> Dict[str, Any]:
    """
    Restore an email from trash
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID to restore
        
    Returns:
        Dict with restoration confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Restore from trash (remove TRASH label)
        restored = service.users().messages().untrash(
            userId='me',
            id=email_id
        ).execute()
        
        labels = restored.get('labelIds', [])
        
        logger.info(f"✅ Restored email {email_id} from trash for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({
                'labels': labels
            })\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Email restored from trash successfully",
            "email_id": email_id,
            "labels": labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to restore email: {str(e)}")
    except Exception as e:
        logger.error(f"Error restoring email: {str(e)}")
        raise ValueError(f"Failed to restore email: {str(e)}")

