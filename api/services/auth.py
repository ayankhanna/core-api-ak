"""
Authentication service - Business logic for user and OAuth operations
"""
from typing import Dict, Any, List, Optional
from lib.supabase_client import supabase, get_authenticated_supabase_client
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication operations"""

    @staticmethod
    def create_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new user in the database.
        Returns existing user if already exists.
        """
        user_id = user_data.get('id')
        
        # Check if user already exists
        existing = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if existing.data:
            logger.info(f"User {user_id} already exists")
            return {
                "message": "User already exists",
                "user": existing.data[0]
            }
        
        # Create new user
        result = supabase.table('users').insert({
            'id': user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'avatar_url': user_data.get('avatar_url'),
        }).execute()
        
        logger.info(f"Created new user: {user_id}")
        return {
            "message": "User created successfully",
            "user": result.data[0]
        }

    @staticmethod
    def create_oauth_connection(connection_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store OAuth connection tokens for a user.
        Creates or updates the connection if it already exists.
        """
        user_id = connection_data.get('user_id')
        provider = connection_data.get('provider')
        provider_user_id = connection_data.get('provider_user_id')
        
        # Check if connection already exists
        existing = supabase.table('ext_connections')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('provider', provider)\
            .eq('provider_user_id', provider_user_id)\
            .execute()
        
        data = {
            'user_id': user_id,
            'provider': provider,
            'provider_user_id': provider_user_id,
            'provider_email': connection_data.get('provider_email'),
            'access_token': connection_data.get('access_token'),
            'refresh_token': connection_data.get('refresh_token'),
            'token_expires_at': connection_data.get('token_expires_at'),
            'scopes': connection_data.get('scopes', []),
            'is_active': True,
            'metadata': connection_data.get('metadata', {})
        }
        
        if existing.data:
            # Update existing connection
            result = supabase.table('ext_connections')\
                .update(data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            logger.info(f"Updated OAuth connection for user {user_id}")
        else:
            # Create new connection
            result = supabase.table('ext_connections')\
                .insert(data)\
                .execute()
            logger.info(f"Created new OAuth connection for user {user_id}")
        
        return {
            "message": "OAuth connection saved successfully",
            "connection": result.data[0]
        }

    @staticmethod
    def get_user_connections(user_id: str) -> Dict[str, Any]:
        """
        Get all OAuth connections for a user.
        """
        result = supabase.table('ext_connections')\
            .select('id, user_id, provider, provider_email, scopes, is_active, created_at, updated_at')\
            .eq('user_id', user_id)\
            .execute()
        
        return {
            "connections": result.data
        }

    @staticmethod
    def revoke_connection(connection_id: str) -> bool:
        """
        Revoke/deactivate an OAuth connection.
        Returns True if revoked, False if not found.
        """
        result = supabase.table('ext_connections')\
            .update({'is_active': False})\
            .eq('id', connection_id)\
            .execute()
        
        if not result.data:
            return False
        
        logger.info(f"Revoked connection {connection_id}")
        return True

    @staticmethod
    def complete_oauth_flow(oauth_data: Dict[str, Any], user_jwt: str) -> Dict[str, Any]:
        """
        Complete OAuth flow - creates user and stores connection in one operation.
        
        Args:
            oauth_data: OAuth connection data
            user_jwt: User's Supabase JWT for authenticated requests
        """
        user_id = oauth_data.get('user_id')
        email = oauth_data.get('email')
        
        # Use authenticated Supabase client (respects RLS policies)
        auth_supabase = get_authenticated_supabase_client(user_jwt)
        
        # Create or update user
        user_result = auth_supabase.table('users').select('id').eq('id', user_id).execute()
        
        if not user_result.data:
            auth_supabase.table('users').insert({
                'id': user_id,
                'email': email,
                'name': oauth_data.get('name'),
                'avatar_url': oauth_data.get('avatar_url'),
            }).execute()
            logger.info(f"✅ Created new user: {user_id}")
        else:
            # Update user info in case it changed
            auth_supabase.table('users').update({
                'name': oauth_data.get('name'),
                'avatar_url': oauth_data.get('avatar_url'),
            }).eq('id', user_id).execute()
            logger.info(f"✅ Updated user: {user_id}")
        
        # Store OAuth connection
        from datetime import datetime, timedelta, timezone
        
        # Calculate token expiry if not provided (default to 1 hour from now)
        token_expires_at = oauth_data.get('token_expires_at')
        if not token_expires_at and oauth_data.get('access_token'):
            token_expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        
        connection_data = {
            'user_id': user_id,
            'provider': oauth_data.get('provider', 'google'),
            'provider_user_id': oauth_data.get('provider_user_id'),
            'provider_email': email,
            'access_token': oauth_data.get('access_token'),
            'refresh_token': oauth_data.get('refresh_token'),
            'token_expires_at': token_expires_at,
            'scopes': oauth_data.get('scopes', []),
            'is_active': True,
            'metadata': oauth_data.get('metadata', {})
        }
        
        # Check if connection exists
        existing = auth_supabase.table('ext_connections')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('provider', connection_data['provider'])\
            .eq('provider_user_id', connection_data['provider_user_id'])\
            .execute()
        
        if existing.data:
            # Update existing
            auth_supabase.table('ext_connections')\
                .update(connection_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            logger.info(f"✅ Updated OAuth connection for {user_id}")
        else:
            # Create new
            auth_supabase.table('ext_connections')\
                .insert(connection_data)\
                .execute()
            logger.info(f"✅ Created OAuth connection for {user_id}")
        
        return {
            "message": "OAuth flow completed successfully",
            "user_id": user_id
        }

