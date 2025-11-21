"""Service for favoriting/unfavoriting documents."""
from lib.supabase_client import get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


async def favorite_document(user_id: str, user_jwt: str, document_id: str) -> dict:
    """
    Mark a document as favorite.
    
    Args:
        user_id: User ID who owns the document
        user_jwt: User's Supabase JWT for authenticated requests
        document_id: Document ID to favorite
    
    Returns:
        The updated document record
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        result = (
            auth_supabase.table("documents")
            .update({"is_favorite": True})
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to favorite document or document not found")
        
        logger.info(f"Favorited document {document_id} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error favoriting document {document_id}: {str(e)}")
        raise


async def unfavorite_document(user_id: str, user_jwt: str, document_id: str) -> dict:
    """
    Remove favorite mark from a document.
    
    Args:
        user_id: User ID who owns the document
        user_jwt: User's Supabase JWT for authenticated requests
        document_id: Document ID to unfavorite
    
    Returns:
        The updated document record
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        result = (
            auth_supabase.table("documents")
            .update({"is_favorite": False})
            .eq("user_id", user_id)
            .eq("id", document_id)
            .execute()
        )
        
        if not result.data:
            raise Exception("Failed to unfavorite document or document not found")
        
        logger.info(f"Unfavorited document {document_id} for user {user_id}")
        return result.data[0]
        
    except Exception as e:
        logger.error(f"Error unfavoriting document {document_id}: {str(e)}")
        raise

