"""
FastAPI dependencies for authentication and authorization
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import jwt


async def get_current_user_jwt(
    authorization: Optional[str] = Header(None)
) -> str:
    """
    Extract and validate the Supabase JWT from the Authorization header.
    
    Args:
        authorization: The Authorization header value (format: "Bearer <token>")
        
    Returns:
        str: The JWT token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>" format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    token = parts[1]
    
    # Basic validation - decode without verification for now
    # Supabase will validate it when we use it
    try:
        # Decode without verification to check it's a valid JWT structure
        jwt.decode(token, options={"verify_signature": False})
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT token"
        )
    
    return token


async def get_optional_user_jwt(
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Extract the Supabase JWT from the Authorization header.
    Returns None if not present (doesn't raise an error).
    
    Args:
        authorization: The Authorization header value (format: "Bearer <token>")
        
    Returns:
        Optional[str]: The JWT token or None
    """
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]



