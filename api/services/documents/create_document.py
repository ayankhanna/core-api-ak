"""Service for creating new documents."""
from typing import Optional
from lib.supabase_client import get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


async def create_document(
    user_id: str,
    user_jwt: str,
    title: str = "Untitled",
    content: str = "",
    icon: Optional[str] = None,
    cover_image: Optional[str] = None,
    parent_id: Optional[str] = None,
    position: int = 0,
) -> dict:
    """
    Create a new document.
    
    Args:
        user_id: User ID who owns the document
        user_jwt: User's Supabase JWT for authenticated requests
        title: Document title
        content: Document content (markdown)
        icon: Optional emoji or icon identifier
        cover_image: Optional cover image URL
        parent_id: Optional parent document ID for nesting
        position: Position for ordering (default 0)
    
    Returns:
        The created document record
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        document_data = {
            "user_id": user_id,
            "title": title,
            "content": content,
            "position": position,
        }
        
        if icon is not None:
            document_data["icon"] = icon
        if cover_image is not None:
            document_data["cover_image"] = cover_image
        if parent_id is not None:
            document_data["parent_id"] = parent_id
        
        result = auth_supabase.table("documents").insert(document_data).execute()
        
        if not result.data:
            raise Exception("Failed to create document")
        
        logger.info(f"Created document {result.data[0]['id']} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        raise

