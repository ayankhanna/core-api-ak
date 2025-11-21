"""Service for retrieving documents."""
from typing import Optional, List
from lib.supabase_client import get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


async def get_documents(
    user_id: str,
    user_jwt: str,
    parent_id: Optional[str] = None,
    include_archived: bool = False,
    favorites_only: bool = False,
    folders_only: bool = False,
    documents_only: bool = False,
) -> List[dict]:
    """
    Get documents for a user.
    
    Args:
        user_id: User ID
        user_jwt: User's Supabase JWT for authenticated requests
        parent_id: Filter by parent document ID (None for root documents)
        include_archived: Whether to include archived documents
        favorites_only: Only return favorite documents
        folders_only: Only return folders
        documents_only: Only return documents (not folders)
    
    Returns:
        List of documents
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        query = auth_supabase.table("documents").select("*").eq("user_id", user_id)
        
        # Filter by parent_id - if explicitly looking for root, don't filter
        if parent_id is not None:
            query = query.eq("parent_id", parent_id)
        
        # Filter archived
        if not include_archived:
            query = query.eq("is_archived", False)
        
        # Filter favorites
        if favorites_only:
            query = query.eq("is_favorite", True)
        
        # Filter by type
        if folders_only:
            query = query.eq("is_folder", True)
        elif documents_only:
            query = query.eq("is_folder", False)
        
        # Order by folder first, then position, then created_at
        query = query.order("is_folder", desc=True).order("position", desc=False).order("created_at", desc=False)
        
        result = query.execute()
        
        logger.info(f"Retrieved {len(result.data)} documents for user {user_id}")
        return result.data
        
    except Exception as e:
        logger.error(f"Error retrieving documents: {str(e)}")
        raise


async def get_document_by_id(user_id: str, user_jwt: str, document_id: str) -> Optional[dict]:
    """
    Get a specific document by ID and update last_opened_at.
    
    Args:
        user_id: User ID
        user_jwt: User's Supabase JWT for authenticated requests
        document_id: Document ID
    
    Returns:
        Document record or None if not found
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        # Get the document
        result = (
            auth_supabase.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            return None
        
        # Update last_opened_at
        from datetime import datetime, timezone
        auth_supabase.table("documents").update({
            "last_opened_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", document_id).eq("user_id", user_id).execute()
        
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {str(e)}")
        raise

