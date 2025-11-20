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
        try:
            supabase_url = os.getenv(
                'SUPABASE_URL', 
                'https://ztnfztpquyvoipttozgz.supabase.co'
            )
            supabase_key = os.getenv(
                'SUPABASE_ANON_KEY',
                'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp0bmZ6dHBxdXl2b2lwdHRvemd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1MjY3NzYsImV4cCI6MjA3OTEwMjc3Nn0.NT8D4xPzEPQFKa3UOJyoXJ060Kx1OTQYfn1I4exCGyM'
            )
            
            _supabase_client = create_client(supabase_url, supabase_key)
        except Exception as e:
            print(f"Error creating Supabase client: {e}")
            # Return a minimal client that will fail gracefully on use
            raise RuntimeError(f"Failed to initialize Supabase client: {e}")
    
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
    try:
        supabase_url = os.getenv(
            'SUPABASE_URL', 
            'https://ztnfztpquyvoipttozgz.supabase.co'
        )
        supabase_key = os.getenv(
            'SUPABASE_ANON_KEY',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp0bmZ6dHBxdXl2b2lwdHRvemd6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjM1MjY3NzYsImV4cCI6MjA3OTEwMjc3Nn0.NT8D4xPzEPQFKa3UOJyoXJ060Kx1OTQYfn1I4exCGyM'
        )
        
        # Create client with user's JWT
        client = create_client(supabase_url, supabase_key)
        
        # Set the user's access token for authenticated requests (for database queries with RLS)
        # We only set the authorization header, not the full session
        client.postgrest.auth(user_jwt)
        
        return client
    except Exception as e:
        print(f"Error creating authenticated Supabase client: {e}")
        raise RuntimeError(f"Failed to initialize authenticated Supabase client: {e}")


# Lazy-loaded module-level client for backward compatibility
# This will only initialize when actually accessed, not at import time
class _LazySupabaseClient:
    """Lazy-loaded Supabase client that initializes on first access"""
    _instance: Optional[Client] = None
    
    def __getattr__(self, name):
        if self._instance is None:
            self._instance = get_supabase_client()
        return getattr(self._instance, name)
    
    def __call__(self, *args, **kwargs):
        if self._instance is None:
            self._instance = get_supabase_client()
        return self._instance(*args, **kwargs)


# Create lazy client instance - safe to import, won't crash at import time
supabase = _LazySupabaseClient()
