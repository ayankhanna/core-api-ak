"""
Documents router - HTTP endpoints for document operations
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from pydantic import BaseModel
from api.services.documents import (
    create_document,
    create_folder,
    get_documents,
    get_document_by_id,
    update_document,
    delete_document,
    archive_document,
    unarchive_document,
    favorite_document,
    unfavorite_document,
    reorder_documents,
)
from api.dependencies import get_current_user_jwt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])


# Pydantic models for request validation
class CreateDocumentRequest(BaseModel):
    title: str = "Untitled"
    content: str = ""
    icon: Optional[str] = None
    cover_image: Optional[str] = None
    parent_id: Optional[str] = None
    position: int = 0


class CreateFolderRequest(BaseModel):
    title: str = "New Folder"
    parent_id: Optional[str] = None
    position: int = 0


class UpdateDocumentRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    icon: Optional[str] = None
    cover_image: Optional[str] = None
    parent_id: Optional[str] = None
    position: Optional[int] = None


class ReorderDocumentsRequest(BaseModel):
    document_positions: List[dict]  # [{"id": "doc_id", "position": 0}, ...]


# Document CRUD endpoints
@router.get("/")
async def get_documents_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
    parent_id: Optional[str] = None,
    include_archived: bool = False,
    favorites_only: bool = False,
    folders_only: bool = False,
    documents_only: bool = False,
):
    """
    Get documents for a user with optional filtering.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Fetching documents for user {user_id}")
        documents = await get_documents(
            user_id=user_id,
            user_jwt=user_jwt,
            parent_id=parent_id,
            include_archived=include_archived,
            favorites_only=favorites_only,
            folders_only=folders_only,
            documents_only=documents_only,
        )
        logger.info(f"✅ Fetched {len(documents)} documents")
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching documents: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch documents: {error_str}"
        )


@router.get("/{document_id}")
async def get_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Get a specific document by ID.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Fetching document {document_id} for user {user_id}")
        document = await get_document_by_id(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        logger.info(f"✅ Fetched document {document_id}")
        return document
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch document: {error_str}"
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_document_endpoint(
    request: CreateDocumentRequest,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Create a new document.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Creating document for user {user_id}")
        document = await create_document(
            user_id=user_id,
            user_jwt=user_jwt,
            title=request.title,
            content=request.content,
            icon=request.icon,
            cover_image=request.cover_image,
            parent_id=request.parent_id,
            position=request.position,
        )
        logger.info(f"✅ Created document {document['id']}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error creating document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {error_str}"
        )


@router.post("/folders", status_code=status.HTTP_201_CREATED)
async def create_folder_endpoint(
    request: CreateFolderRequest,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Create a new folder.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📁 Creating folder for user {user_id}")
        folder = await create_folder(
            user_id=user_id,
            user_jwt=user_jwt,
            title=request.title,
            parent_id=request.parent_id,
            position=request.position,
        )
        logger.info(f"✅ Created folder {folder['id']}")
        return folder
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error creating folder: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create folder: {error_str}"
        )


@router.patch("/{document_id}")
async def update_document_endpoint(
    document_id: str,
    request: UpdateDocumentRequest,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Update an existing document.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Updating document {document_id} for user {user_id}")
        document = await update_document(
            user_id=user_id,
            user_jwt=user_jwt,
            document_id=document_id,
            title=request.title,
            content=request.content,
            icon=request.icon,
            cover_image=request.cover_image,
            parent_id=request.parent_id,
            position=request.position,
        )
        logger.info(f"✅ Updated document {document_id}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error updating document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {error_str}"
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Permanently delete a document.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Deleting document {document_id} for user {user_id}")
        await delete_document(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        logger.info(f"✅ Deleted document {document_id}")
        return None
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error deleting document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {error_str}"
        )


@router.post("/{document_id}/archive")
async def archive_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Archive a document (soft delete).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Archiving document {document_id} for user {user_id}")
        document = await archive_document(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        logger.info(f"✅ Archived document {document_id}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error archiving document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive document: {error_str}"
        )


@router.post("/{document_id}/unarchive")
async def unarchive_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Unarchive a document.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Unarchiving document {document_id} for user {user_id}")
        document = await unarchive_document(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        logger.info(f"✅ Unarchived document {document_id}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error unarchiving document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unarchive document: {error_str}"
        )


@router.post("/{document_id}/favorite")
async def favorite_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Mark a document as favorite.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Favoriting document {document_id} for user {user_id}")
        document = await favorite_document(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        logger.info(f"✅ Favorited document {document_id}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error favoriting document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to favorite document: {error_str}"
        )


@router.post("/{document_id}/unfavorite")
async def unfavorite_document_endpoint(
    document_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Remove favorite mark from a document.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Unfavoriting document {document_id} for user {user_id}")
        document = await unfavorite_document(user_id=user_id, user_jwt=user_jwt, document_id=document_id)
        logger.info(f"✅ Unfavorited document {document_id}")
        return document
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error unfavoriting document: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        if "not found" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unfavorite document: {error_str}"
        )


@router.post("/reorder")
async def reorder_documents_endpoint(
    request: ReorderDocumentsRequest,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
):
    """
    Reorder multiple documents at once.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📄 Reordering documents for user {user_id}")
        documents = await reorder_documents(
            user_id=user_id, user_jwt=user_jwt, document_positions=request.document_positions
        )
        logger.info(f"✅ Reordered {len(documents)} documents")
        return {"documents": documents, "count": len(documents)}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error reordering documents: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder documents: {error_str}"
        )

