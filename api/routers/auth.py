"""
Authentication router - HTTP endpoints for auth operations
"""
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from api.services.auth import AuthService
from api.dependencies import get_current_user_jwt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


# Pydantic models for request/response validation
class UserCreate(BaseModel):
    id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class OAuthConnectionCreate(BaseModel):
    user_id: str
    provider: str
    provider_user_id: str
    provider_email: Optional[str] = None
    access_token: str
    refresh_token: Optional[str] = None
    scopes: List[str] = []
    metadata: Optional[dict] = None


class OAuthConnectionResponse(BaseModel):
    id: str
    user_id: str
    provider: str
    is_active: bool
    scopes: List[str]
    created_at: str


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate):
    """
    Create a new user in the database.
    If user already exists, returns existing user.
    """
    try:
        return AuthService.create_user(user.dict())
    except Exception as e:
        logger.error(f"Error in create_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/oauth-connections", status_code=status.HTTP_201_CREATED)
async def create_oauth_connection(connection: OAuthConnectionCreate):
    """
    Store OAuth connection tokens for a user.
    Creates or updates the connection if it already exists.
    """
    try:
        return AuthService.create_oauth_connection(connection.dict())
    except Exception as e:
        logger.error(f"Error in create_oauth_connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save OAuth connection: {str(e)}"
        )


@router.get("/oauth-connections/{user_id}")
async def get_user_connections(user_id: str):
    """
    Get all OAuth connections for a user.
    """
    try:
        return AuthService.get_user_connections(user_id)
    except Exception as e:
        logger.error(f"Error in get_user_connections: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch connections: {str(e)}"
        )


@router.delete("/oauth-connections/{connection_id}")
async def revoke_oauth_connection(connection_id: str):
    """
    Revoke/deactivate an OAuth connection.
    """
    try:
        revoked = AuthService.revoke_connection(connection_id)
        
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Connection not found"
            )
        
        return {
            "message": "Connection revoked successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in revoke_oauth_connection: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke connection: {str(e)}"
        )


class CompleteOAuthRequest(BaseModel):
    user_id: str
    email: EmailStr
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    provider: str = "google"
    provider_user_id: str
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[str] = None
    scopes: List[str] = []
    metadata: Optional[dict] = None


@router.post("/complete-oauth")
async def complete_oauth_flow(
    request: CompleteOAuthRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Complete OAuth flow - creates user and stores connection in one call.
    This is a convenience endpoint for the OAuth callback.
    
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🚀 === COMPLETE OAUTH FLOW START ===")
        logger.info(f"📧 User ID: {request.user_id}")
        logger.info(f"📧 Email: {request.email}")
        logger.info(f"👤 Name: {request.name}")
        logger.info(f"🔗 Provider: {request.provider}")
        logger.info(f"🔑 Has access token: {bool(request.access_token)}")
        logger.info(f"🔄 Has refresh token: {bool(request.refresh_token)}")
        logger.info(f"🎫 Has Supabase JWT: {bool(user_jwt)}")
        
        result = AuthService.complete_oauth_flow(request.dict(), user_jwt)
        
        logger.info(f"✅ OAuth flow completed successfully")
        logger.info(f"🏁 === COMPLETE OAUTH FLOW END ===")
        
        return result
    except Exception as e:
        logger.error(f"❌ Error in complete_oauth_flow: {str(e)}")
        logger.error(f"❌ Error type: {type(e).__name__}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete OAuth flow: {str(e)}"
        )
