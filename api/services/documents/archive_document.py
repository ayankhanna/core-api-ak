"""Service for archiving/unarchiving documents."""
from lib.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)


async def archive_document(user_id: str, document_id: str) -> dict:
    """
    Archive a document (soft delete).
    
    Args:
        user_id: User ID who owns the document
        document_id: Document ID to archive
    
    Returns:
        The updated document record
    """
    try:
        result = (
            supabase.table("documents")
            .update({"is_archived": True})
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to archive document or document not found")
        
        logger.info(f"Archived document {document_id} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error archiving document {document_id}: {str(e)}")
        raise


async def unarchive_document(user_id: str, document_id: str) -> dict:
    """
    Unarchive a document.
    
    Args:
        user_id: User ID who owns the document
        document_id: Document ID to unarchive
    
    Returns:
        The updated document record
    """
    try:
        result = (
            supabase.table("documents")
            .update({"is_archived": False})
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to unarchive document or document not found")
        
        logger.info(f"Unarchived document {document_id} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error unarchiving document {document_id}: {str(e)}")
        raise

