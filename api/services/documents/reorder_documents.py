"""Service for reordering documents."""
from typing import List, Dict
from lib.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)


async def reorder_documents(
    user_id: str, document_positions: List[Dict[str, int]]
) -> List[dict]:
    """
    Reorder multiple documents at once.
    
    Args:
        user_id: User ID who owns the documents
        document_positions: List of {"id": document_id, "position": new_position}
    
    Returns:
        List of updated document records
    """
    try:
        updated_documents = []
        
        for item in document_positions:
            document_id = item.get("id")
            position = item.get("position")
            
            if document_id is None or position is None:
                continue
            
            result = (
                supabase.table("documents")
                .update({"position": position})
                .eq("user_id", user_id)
                .eq("id", document_id)
                .execute()
            )
            
            if result.data:
                updated_documents.extend(result.data)
        
        logger.info(f"Reordered {len(updated_documents)} documents for user {user_id}")
        return updated_documents
        
    except Exception as e:
        logger.error(f"Error reordering documents: {str(e)}")
        raise

