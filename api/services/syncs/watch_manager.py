"""
Watch Manager Service - Manages Google push notification subscriptions
Handles Gmail and Google Calendar watch subscriptions for real-time updates
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from lib.supabase_client import get_authenticated_supabase_client
import logging
import uuid
import os
from googleapiclient.errors import HttpError
from api.services.email.google_api_helpers import get_gmail_service
from api.services.calendar.google_api_helpers import get_google_calendar_service

logger = logging.getLogger(__name__)

# Configuration
WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL', 'https://your-domain.vercel.app')
GMAIL_WEBHOOK_PATH = '/api/webhooks/gmail'
CALENDAR_WEBHOOK_PATH = '/api/webhooks/calendar'


def start_gmail_watch(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Start watching a user's Gmail for push notifications
    
    Gmail watch expires after 7 days and must be renewed.
    When changes occur, Google sends a notification with historyId.
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Dict with watch subscription details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        # Get Gmail service
        service, connection_id = get_gmail_service(user_id, user_jwt)
        
        if not service or not connection_id:
            raise ValueError("No active Google connection found for user")
        
        # Generate unique channel ID
        channel_id = str(uuid.uuid4())
        
        # Set up watch request
        request_body = {
            'labelIds': ['INBOX', 'UNREAD', 'IMPORTANT'],
            'labelFilterAction': 'include',
            'topicName': f'projects/{os.getenv("GOOGLE_CLOUD_PROJECT_ID")}/topics/gmail-notifications'
        }
        
        logger.info(f"🔔 Starting Gmail watch for user {user_id}, channel: {channel_id}")
        
        # Start the watch
        watch_response = service.users().watch(
            userId='me',
            body=request_body
        ).execute()
        
        history_id = watch_response.get('historyId')
        expiration = watch_response.get('expiration')
        
        # Convert expiration (milliseconds since epoch) to datetime
        if expiration:
            expiration_dt = datetime.fromtimestamp(int(expiration) / 1000, tz=timezone.utc)
        else:
            # Default to 7 days from now (Gmail's max)
            expiration_dt = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Check if subscription already exists
        existing = auth_supabase.table('push_subscriptions')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('provider', 'gmail')\
            .execute()
        
        subscription_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'provider': 'gmail',
            'channel_id': channel_id,
            'resource_id': watch_response.get('resourceId'),
            'history_id': history_id,
            'expiration': expiration_dt.isoformat(),
            'is_active': True,
            'metadata': {
                'watch_response': watch_response,
                'started_at': datetime.now(timezone.utc).isoformat()
            },
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing.data:
            # Update existing subscription
            result = auth_supabase.table('push_subscriptions')\
                .update(subscription_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            logger.info(f"✅ Updated Gmail watch for user {user_id}")
        else:
            # Insert new subscription
            result = auth_supabase.table('push_subscriptions')\
                .insert(subscription_data)\
                .execute()
            logger.info(f"✅ Created Gmail watch for user {user_id}")
        
        return {
            'success': True,
            'provider': 'gmail',
            'channel_id': channel_id,
            'history_id': history_id,
            'expiration': expiration_dt.isoformat(),
            'message': 'Gmail watch started successfully'
        }
        
    except HttpError as e:
        logger.error(f"❌ Gmail API error starting watch: {str(e)}")
        raise ValueError(f"Failed to start Gmail watch: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error starting Gmail watch: {str(e)}")
        raise ValueError(f"Failed to start Gmail watch: {str(e)}")


def start_calendar_watch(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Start watching a user's Google Calendar for push notifications
    
    Calendar watch expires based on configured time (we'll use 7 days for consistency).
    When changes occur, Google sends a notification with sync token.
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Dict with watch subscription details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        # Get Calendar service
        service, connection_id = get_google_calendar_service(user_id, user_jwt)
        
        if not service or not connection_id:
            raise ValueError("No active Google connection found for user")
        
        # Generate unique channel ID
        channel_id = str(uuid.uuid4())
        
        # Calculate expiration (7 days from now, in milliseconds)
        expiration_dt = datetime.now(timezone.utc) + timedelta(days=7)
        expiration_ms = int(expiration_dt.timestamp() * 1000)
        
        # Set up watch request
        webhook_url = f"{WEBHOOK_BASE_URL}{CALENDAR_WEBHOOK_PATH}"
        request_body = {
            'id': channel_id,
            'type': 'web_hook',
            'address': webhook_url,
            'expiration': expiration_ms
        }
        
        logger.info(f"🔔 Starting Calendar watch for user {user_id}, channel: {channel_id}")
        
        # Start the watch
        watch_response = service.events().watch(
            calendarId='primary',
            body=request_body
        ).execute()
        
        resource_id = watch_response.get('resourceId')
        
        # Get sync token for incremental updates
        events_result = service.events().list(
            calendarId='primary',
            maxResults=1
        ).execute()
        sync_token = events_result.get('nextSyncToken')
        
        # Check if subscription already exists
        existing = auth_supabase.table('push_subscriptions')\
            .select('id')\
            .eq('user_id', user_id)\
            .eq('provider', 'calendar')\
            .execute()
        
        subscription_data = {
            'user_id': user_id,
            'connection_id': connection_id,
            'provider': 'calendar',
            'channel_id': channel_id,
            'resource_id': resource_id,
            'sync_token': sync_token,
            'expiration': expiration_dt.isoformat(),
            'is_active': True,
            'metadata': {
                'watch_response': watch_response,
                'webhook_url': webhook_url,
                'started_at': datetime.now(timezone.utc).isoformat()
            },
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        
        if existing.data:
            # Update existing subscription
            result = auth_supabase.table('push_subscriptions')\
                .update(subscription_data)\
                .eq('id', existing.data[0]['id'])\
                .execute()
            logger.info(f"✅ Updated Calendar watch for user {user_id}")
        else:
            # Insert new subscription
            result = auth_supabase.table('push_subscriptions')\
                .insert(subscription_data)\
                .execute()
            logger.info(f"✅ Created Calendar watch for user {user_id}")
        
        return {
            'success': True,
            'provider': 'calendar',
            'channel_id': channel_id,
            'resource_id': resource_id,
            'sync_token': sync_token,
            'expiration': expiration_dt.isoformat(),
            'message': 'Calendar watch started successfully'
        }
        
    except HttpError as e:
        logger.error(f"❌ Calendar API error starting watch: {str(e)}")
        raise ValueError(f"Failed to start Calendar watch: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error starting Calendar watch: {str(e)}")
        raise ValueError(f"Failed to start Calendar watch: {str(e)}")


def stop_watch(user_id: str, user_jwt: str, provider: str) -> Dict[str, Any]:
    """
    Stop a watch subscription for a user
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT
        provider: 'gmail' or 'calendar'
        
    Returns:
        Dict with result
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    try:
        # Get subscription
        subscription = auth_supabase.table('push_subscriptions')\
            .select('*')\
            .eq('user_id', user_id)\
            .eq('provider', provider)\
            .eq('is_active', True)\
            .single()\
            .execute()
        
        if not subscription.data:
            return {
                'success': True,
                'message': f'No active {provider} watch found'
            }
        
        channel_id = subscription.data['channel_id']
        resource_id = subscription.data['resource_id']
        
        logger.info(f"🛑 Stopping {provider} watch for user {user_id}, channel: {channel_id}")
        
        if provider == 'gmail':
            service, _ = get_gmail_service(user_id, user_jwt)
            if service:
                try:
                    service.users().stop(userId='me').execute()
                except HttpError as e:
                    logger.warning(f"⚠️ Could not stop Gmail watch (may already be expired): {str(e)}")
        
        elif provider == 'calendar':
            service, _ = get_google_calendar_service(user_id, user_jwt)
            if service:
                try:
                    service.channels().stop(
                        body={
                            'id': channel_id,
                            'resourceId': resource_id
                        }
                    ).execute()
                except HttpError as e:
                    logger.warning(f"⚠️ Could not stop Calendar watch (may already be expired): {str(e)}")
        
        # Mark as inactive in database
        auth_supabase.table('push_subscriptions')\
            .update({'is_active': False, 'updated_at': datetime.now(timezone.utc).isoformat()})\
            .eq('id', subscription.data['id'])\
            .execute()
        
        logger.info(f"✅ Stopped {provider} watch for user {user_id}")
        
        return {
            'success': True,
            'provider': provider,
            'message': f'{provider.title()} watch stopped successfully'
        }
        
    except Exception as e:
        logger.error(f"❌ Error stopping {provider} watch: {str(e)}")
        raise ValueError(f"Failed to stop {provider} watch: {str(e)}")


def renew_watch(user_id: str, user_jwt: str, provider: str) -> Dict[str, Any]:
    """
    Renew a watch subscription before it expires
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT
        provider: 'gmail' or 'calendar'
        
    Returns:
        Dict with result
    """
    logger.info(f"🔄 Renewing {provider} watch for user {user_id}")
    
    try:
        # Stop old watch (if still active)
        try:
            stop_watch(user_id, user_jwt, provider)
        except Exception as e:
            logger.warning(f"⚠️ Could not stop old watch (may already be expired): {str(e)}")
        
        # Start new watch
        if provider == 'gmail':
            result = start_gmail_watch(user_id, user_jwt)
        elif provider == 'calendar':
            result = start_calendar_watch(user_id, user_jwt)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        logger.info(f"✅ Renewed {provider} watch for user {user_id}")
        
        return {
            'success': True,
            'provider': provider,
            'message': f'{provider.title()} watch renewed successfully',
            'details': result
        }
        
    except Exception as e:
        logger.error(f"❌ Error renewing {provider} watch: {str(e)}")
        raise ValueError(f"Failed to renew {provider} watch: {str(e)}")


def get_expiring_subscriptions(hours: int = 24) -> list:
    """
    Get all subscriptions expiring within the specified hours
    This is used by cron jobs to renew watches before they expire
    
    Args:
        hours: Number of hours to look ahead (default 24)
        
    Returns:
        List of subscriptions that need renewal
    """
    from lib.supabase_client import get_supabase_client
    supabase = get_supabase_client()
    
    try:
        expiration_threshold = datetime.now(timezone.utc) + timedelta(hours=hours)
        
        result = supabase.table('push_subscriptions')\
            .select('*')\
            .eq('is_active', True)\
            .lt('expiration', expiration_threshold.isoformat())\
            .execute()
        
        subscriptions = result.data or []
        
        logger.info(f"📊 Found {len(subscriptions)} subscriptions expiring within {hours} hours")
        
        return subscriptions
        
    except Exception as e:
        logger.error(f"❌ Error fetching expiring subscriptions: {str(e)}")
        return []


def setup_watches_for_user(user_id: str, user_jwt: str) -> Dict[str, Any]:
    """
    Set up both Gmail and Calendar watches for a user
    Used during onboarding or when watches are missing
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT
        
    Returns:
        Dict with results for both providers
    """
    results = {
        'gmail': {'success': False, 'error': None},
        'calendar': {'success': False, 'error': None}
    }
    
    # Try Gmail watch
    try:
        gmail_result = start_gmail_watch(user_id, user_jwt)
        results['gmail'] = {'success': True, 'data': gmail_result}
    except Exception as e:
        logger.error(f"❌ Failed to set up Gmail watch: {str(e)}")
        results['gmail'] = {'success': False, 'error': str(e)}
    
    # Try Calendar watch
    try:
        calendar_result = start_calendar_watch(user_id, user_jwt)
        results['calendar'] = {'success': True, 'data': calendar_result}
    except Exception as e:
        logger.error(f"❌ Failed to set up Calendar watch: {str(e)}")
        results['calendar'] = {'success': False, 'error': str(e)}
    
    return results

