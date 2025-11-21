"""Service for retrieving documents."""
from typing import Optional, List
from lib.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)


async def get_documents(
    user_id: str,
    parent_id: Optional[str] = None,
    include_archived: bool = False,
    favorites_only: bool = False,
) -> List[dict]:
    """
    Get documents for a user.
    
    Args:
        user_id: User ID
        parent_id: Filter by parent document ID (None for root documents)
        include_archived: Whether to include archived documents
        favorites_only: Only return favorite documents
    
    Returns:
        List of documents
    """
    try:
        query = supabase.table("documents").select("*").eq("user_id", user_id)
        
        # Filter by parent_id
        if parent_id is not None:
            query = query.eq("parent_id", parent_id)
        else:
            query = query.is_("parent_id", "null")
        
        # Filter archived
        if not include_archived:
            query = query.eq("is_archived", False)
        
        # Filter favorites
        if favorites_only:
            query = query.eq("is_favorite", True)
        
        # Order by position and created_at
        query = query.order("position", desc=False).order("created_at", desc=False)
        
        result = query.execute()
        
        logger.info(f"Retrieved {len(result.data)} documents for user {user_id}")
        return result.data
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        raise


async def get_document_by_id(user_id: str, document_id: str) -> Optional[dict]:
    """
    Get a specific document by ID.
    
    Args:
        user_id: User ID
        document_id: Document ID
    
    Returns:
        Document record or None if not found
    """
    try:
        result = (
            supabase.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            return None
        
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        raise

