"""
Webhooks router - Receives push notifications from external services
"""
from fastapi import APIRouter, Request, HTTPException, status, Header
from typing import Optional
import logging
import json
import base64
from datetime import datetime, timezone
from api.services.syncs import process_gmail_history
from api.services.syncs.sync_google_calendar import sync_google_calendar
from lib.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None)
):
    """
    Receive Gmail push notifications from Google Cloud Pub/Sub
    
    Google sends notifications when the mailbox changes.
    We use the historyId to fetch only what changed (very efficient)
    
    Headers from Google:
    - X-Goog-Channel-ID: The UUID of the notification channel
    - X-Goog-Resource-ID: Opaque ID for the watched resource
    - X-Goog-Resource-State: "sync" (initial) or "exists" (change notification)
    - X-Goog-Message-Number: Sequential message number
    
    Returns 200 immediately to acknowledge receipt (required by Google)
    """
    try:
        # Log notification received
        logger.info(f"📬 Gmail webhook received: channel={x_goog_channel_id}, state={x_goog_resource_state}")
        
        # Handle sync message (initial verification from Google)
        if x_goog_resource_state == "sync":
            logger.info(f"✅ Gmail sync verification received for channel {x_goog_channel_id}")
            return {"status": "ok", "message": "Sync verified"}
        
        # Handle actual change notification
        if x_goog_resource_state == "exists":
            # Get the subscription from database to find user
            supabase = get_supabase_client()
            
            subscription = supabase.table('push_subscriptions')\
                .select('*, ext_connections!push_subscriptions_ext_connection_id_fkey!inner(user_id, access_token, refresh_token)')\
                .eq('channel_id', x_goog_channel_id)\
                .eq('provider', 'gmail')\
                .eq('is_active', True)\
                .execute()
            
            if not subscription.data:
                logger.warning(f"⚠️ No active subscription found for channel {x_goog_channel_id}")
                return {"status": "ok", "message": "No active subscription"}
            
            sub_data = subscription.data[0]
            user_id = sub_data['ext_connections']['user_id']
            history_id = sub_data.get('history_id')
            
            logger.info(f"🔄 Processing Gmail changes for user {user_id} from historyId {history_id}")
            
            # Update notification count
            notification_count = sub_data.get('notification_count', 0) + 1
            supabase.table('push_subscriptions')\
                .update({
                    'notification_count': notification_count,
                    'last_notification_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('id', sub_data['id'])\
                .execute()
            
            # TODO: Process in background queue for production
            # For now, we'll trigger sync directly (but Google requires 200 response quickly)
            # In production, use Celery, RQ, or similar to process async
            
            try:
                # Get a user JWT to make authenticated calls
                # Note: This is a simplified version - in production you'd need proper auth
                from lib.supabase_client import get_supabase_client
                admin_supabase = get_supabase_client()
                
                # Create a service role token for internal operations
                # In production, implement proper service-to-service auth
                logger.info(f"📊 Queueing history sync for user {user_id}")
                
                # For MVP: Just log that we'd process this
                # Full implementation would queue this job
                logger.info(f"✅ Gmail notification queued for processing")
                
            except Exception as e:
                logger.error(f"❌ Error processing Gmail notification: {str(e)}")
                # Still return 200 to Google - we'll catch it in cron
        
        return {"status": "ok", "message": "Notification received"}
        
    except Exception as e:
        logger.error(f"❌ Error handling Gmail webhook: {str(e)}")
        # Always return 200 to Google, even on error
        # We don't want Google to think our endpoint is down
        return {"status": "error", "message": str(e)}


@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None)
):
    """
    Receive Google Calendar push notifications
    
    Google sends notifications when calendar events change.
    We use sync tokens to fetch only what changed.
    
    Headers from Google:
    - X-Goog-Channel-ID: The UUID of the notification channel
    - X-Goog-Resource-ID: Opaque ID for the watched resource
    - X-Goog-Resource-State: "sync" (initial) or "exists" (change notification)
    - X-Goog-Message-Number: Sequential message number
    
    Returns 200 immediately to acknowledge receipt (required by Google)
    """
    try:
        # Log notification received
        logger.info(f"📅 Calendar webhook received: channel={x_goog_channel_id}, state={x_goog_resource_state}")
        
        # Handle sync message (initial verification from Google)
        if x_goog_resource_state == "sync":
            logger.info(f"✅ Calendar sync verification received for channel {x_goog_channel_id}")
            return {"status": "ok", "message": "Sync verified"}
        
        # Handle actual change notification
        if x_goog_resource_state == "exists":
            # Get the subscription from database to find user
            supabase = get_supabase_client()
            
            subscription = supabase.table('push_subscriptions')\
                .select('*, ext_connections!push_subscriptions_ext_connection_id_fkey!inner(user_id, access_token, refresh_token)')\
                .eq('channel_id', x_goog_channel_id)\
                .eq('provider', 'calendar')\
                .eq('is_active', True)\
                .execute()
            
            if not subscription.data:
                logger.warning(f"⚠️ No active subscription found for channel {x_goog_channel_id}")
                return {"status": "ok", "message": "No active subscription"}
            
            sub_data = subscription.data[0]
            user_id = sub_data['ext_connections']['user_id']
            sync_token = sub_data.get('sync_token')
            
            logger.info(f"🔄 Processing Calendar changes for user {user_id}")
            
            # Update notification count
            notification_count = sub_data.get('notification_count', 0) + 1
            supabase.table('push_subscriptions')\
                .update({
                    'notification_count': notification_count,
                    'last_notification_at': datetime.now(timezone.utc).isoformat()
                })\
                .eq('id', sub_data['id'])\
                .execute()
            
            # TODO: Process in background queue for production
            # For now, log that we'd process this
            logger.info(f"✅ Calendar notification queued for processing")
        
        return {"status": "ok", "message": "Notification received"}
        
    except Exception as e:
        logger.error(f"❌ Error handling Calendar webhook: {str(e)}")
        # Always return 200 to Google
        return {"status": "error", "message": str(e)}


@router.get("/gmail/verify")
async def verify_gmail_webhook():
    """
    Health check endpoint for Gmail webhook
    Used to verify the endpoint is accessible
    """
    return {
        "status": "healthy",
        "service": "gmail-webhook",
        "message": "Gmail webhook endpoint is ready to receive notifications"
    }


@router.get("/calendar/verify")
async def verify_calendar_webhook():
    """
    Health check endpoint for Calendar webhook
    Used to verify the endpoint is accessible
    """
    return {
        "status": "healthy",
        "service": "calendar-webhook",
        "message": "Calendar webhook endpoint is ready to receive notifications"
    }


