"""Service for deleting documents."""
from lib.supabase_client import get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


async def delete_document(user_id: str, user_jwt: str, document_id: str) -> bool:
    """
    Permanently delete a document.
    
    Note: This will cascade delete all child documents.
    
    Args:
        user_id: User ID who owns the document
        user_jwt: User's Supabase JWT for authenticated requests
        document_id: Document ID to delete
    
    Returns:
        True if successful
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        result = (
            auth_supabase.table("documents")
            .delete()
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to delete document or document not found")
        
        logger.info(f"Deleted document {document_id} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise

