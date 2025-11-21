"""Service for updating documents."""
from typing import Optional
from lib.supabase_client import get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


async def update_document(
    user_id: str,
    user_jwt: str,
    document_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    icon: Optional[str] = None,
    cover_image: Optional[str] = None,
    parent_id: Optional[str] = None,
    position: Optional[int] = None,
) -> dict:
    """
    Update an existing document.
    
    Args:
        user_id: User ID who owns the document
        user_jwt: User's Supabase JWT for authenticated requests
        document_id: Document ID to update
        title: New title (optional)
        content: New content (optional)
        icon: New icon (optional)
        cover_image: New cover image (optional)
        parent_id: New parent ID (optional)
        position: New position (optional)
    
    Returns:
        The updated document record
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        update_data = {}
        
        if title is not None:
            update_data["title"] = title
        if content is not None:
            update_data["content"] = content
        if icon is not None:
            update_data["icon"] = icon
        if cover_image is not None:
            update_data["cover_image"] = cover_image
        if parent_id is not None:
            update_data["parent_id"] = parent_id
        if position is not None:
            update_data["position"] = position
        
        if not update_data:
            raise ValueError("No fields to update")
        
        result = (
            auth_supabase.table("documents")
            .update(update_data)
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to update document or document not found")
        
        logger.info(f"Updated document {document_id} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error updating document {document_id}: {str(e)}")
        raise

