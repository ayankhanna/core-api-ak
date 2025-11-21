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
        supabase_url = os.getenv(
            'SUPABASE_URL', 
            'https://rcwkcskfndgseuaonfsf.supabase.co'
        )
        supabase_key = os.getenv(
            'SUPABASE_ANON_KEY',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjd2tjc2tmbmRnc2V1YW9uZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM3NTAyMjcsImV4cCI6MjA3OTMyNjIyN30.t3tGXCwHMSyzDEoe0SQU_8iSRC8MnHODkC75XhXHLCQ'
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
    supabase_url = os.getenv(
        'SUPABASE_URL', 
        'https://rcwkcskfndgseuaonfsf.supabase.co'
    )
    supabase_key = os.getenv(
        'SUPABASE_ANON_KEY',
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJjd2tjc2tmbmRnc2V1YW9uZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM3NTAyMjcsImV4cCI6MjA3OTMyNjIyN30.t3tGXCwHMSyzDEoe0SQU_8iSRC8MnHODkC75XhXHLCQ'
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
    supabase_url = os.getenv(
        'SUPABASE_URL', 
        'https://rcwkcskfndgseuaonfsf.supabase.co'
    )
    supabase_service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_service_key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY environment variable is not set. "
            "This is required for server-to-server operations like cron jobs. "
            "Find your service role key in Supabase Dashboard → Settings → API"
        )
    
    # Create client with service role key (bypasses RLS)
    client = create_client(supabase_url, supabase_service_key)
    
    return client


# Convenience alias for anon client
supabase = get_supabase_client()


