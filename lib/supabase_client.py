"""
Supabase client for core-api
Provides Supabase client instances with proper authentication.
"""
import os
from typing import Optional
from supabase import create_client, Client

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create the Supabase client singleton with anon key.
    Use this for non-authenticated operations only.
    
    Returns:
        Client: The Supabase client instance with anon key
    """
    global _supabase_client
    
    if _supabase_client is None:
        # Import here to avoid circular dependency
        from api.config import settings
        
        supabase_url = settings.supabase_url or os.getenv('SUPABASE_URL')
        supabase_key = settings.supabase_anon_key or os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables or .env file"
            )
        
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client


def get_authenticated_supabase_client(user_jwt: str) -> Client:
    """
    Create a Supabase client authenticated as a specific user.
    This client will respect RLS policies for the authenticated user.
    
    Args:
        user_jwt: The user's Supabase JWT access token
        
    Returns:
        Client: Supabase client authenticated as the user
    """
    # Import here to avoid circular dependency
    from api.config import settings
    
    supabase_url = settings.supabase_url or os.getenv('SUPABASE_URL')
    supabase_key = settings.supabase_anon_key or os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables or .env file"
        )
    
    # Create client with user's JWT
    client = create_client(supabase_url, supabase_key)
    
    # Set the user's access token for authenticated requests (for database queries with RLS)
    # We only set the authorization header, not the full session
    client.postgrest.auth(user_jwt)
    
    return client


def get_service_role_client() -> Client:
    """
    Create a Supabase client with service role key.
    This client bypasses RLS policies and should ONLY be used for:
    - Cron jobs that need to access data across all users
    - Background tasks that run server-to-server
    - Administrative operations
    
    ⚠️ WARNING: Use with extreme caution! This client has full database access.
    
    Returns:
        Client: Supabase client with service role privileges
    """
    # Import here to avoid circular dependency
    from api.config import settings
    
    supabase_url = settings.supabase_url or os.getenv('SUPABASE_URL')
    supabase_service_key = settings.supabase_service_role_key or os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url:
        raise ValueError(
            "SUPABASE_URL must be set in environment variables or .env file"
        )
    
    if not supabase_service_key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY must be set in environment variables or .env file. "
            "This is required for server-to-server operations like cron jobs. "
            "Find your service role key in Supabase Dashboard → Settings → API"
        )
    
    # Create client with service role key (bypasses RLS)
    client = create_client(supabase_url, supabase_service_key)
    
    return client


# Convenience alias for anon client
supabase = get_supabase_client()


