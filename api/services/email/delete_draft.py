"""
Email service - Delete draft operations
"""
from typing import Dict, Any
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_gmail_service

logger = logging.getLogger(__name__)


def delete_draft(
    user_id: str,
    user_jwt: str,
    draft_id: str
) -> Dict[str, Any]:
    """
    Delete a draft email (two-way sync with database)
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        draft_id: Gmail draft ID to delete
        
    Returns:
        Dict with deletion confirmation
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Delete draft from Gmail
        service.users().drafts().delete(
            userId='me',
            id=draft_id
        ).execute()
        
        logger.info(f"✅ Deleted draft {draft_id} from Gmail for user {user_id}")
        
        # Delete from database
        auth_supabase.table('emails')\
            .delete()\
            .eq('user_id', user_id)\
            .eq('external_id', draft_id)\
            .execute()
        
        logger.info(f"✅ Deleted draft {draft_id} from database for user {user_id}")
        
        return {
            "message": "Draft deleted successfully",
            "draft_id": draft_id,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to delete draft: {str(e)}")
    except Exception as e:
        logger.error(f"Error deleting draft: {str(e)}")
        raise ValueError(f"Failed to delete draft: {str(e)}")

