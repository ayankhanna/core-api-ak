"""
Webhooks router - Receives push notifications from Google
Handles Gmail and Google Calendar push notifications for real-time sync
"""
from fastapi import APIRouter, Request, HTTPException, Header, BackgroundTasks
from typing import Optional
import logging
import base64
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None)
):
    """
    Receive Gmail push notifications from Google Pub/Sub
    
    Google sends notifications when mailbox changes occur.
    We process these asynchronously in the background.
    
    Headers from Google:
    - x-goog-channel-id: The UUID of the watch channel
    - x-goog-resource-state: sync, exists, or not_exists
    - x-goog-resource-id: Opaque ID for the watched resource
    - x-goog-message-number: Message sequence number
    
    Returns 200 immediately to acknowledge receipt, processes in background
    """
    try:
        logger.info(f"📬 Gmail webhook received: channel={x_goog_channel_id}, state={x_goog_resource_state}")
        
        # Parse the notification body
        body = await request.body()
        
        # Pub/Sub messages are base64 encoded
        data = {}
        try:
            if body:
                notification = json.loads(body)
                if 'message' in notification and 'data' in notification['message']:
                    data = json.loads(base64.b64decode(notification['message']['data']))
        except Exception as e:
            logger.warning(f"⚠️ Could not parse notification body: {str(e)}")
        
        # Process in background to return quickly
        from api.services.syncs.notification_processor import process_gmail_notification
        
        background_tasks.add_task(
            process_gmail_notification,
            channel_id=x_goog_channel_id,
            resource_state=x_goog_resource_state,
            data=data
        )
        
        # Return 200 immediately (Google requires this within 10 seconds)
        return {
            'success': True,
            'message': 'Gmail notification received and queued for processing'
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling Gmail webhook: {str(e)}")
        # Still return 200 to avoid Google retrying
        return {
            'success': False,
            'error': 'Internal error',
            'message': 'Notification acknowledged but processing failed'
        }


@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None),
    x_goog_resource_id: Optional[str] = Header(None),
    x_goog_message_number: Optional[str] = Header(None)
):
    """
    Receive Google Calendar push notifications
    
    Google sends notifications when calendar events change.
    We process these asynchronously in the background.
    
    Returns 200 immediately to acknowledge receipt
    """
    try:
        logger.info(f"📅 Calendar webhook received: channel={x_goog_channel_id}, state={x_goog_resource_state}")
        
        # Parse notification body
        body = await request.body()
        data = {}
        try:
            if body:
                data = json.loads(body)
        except Exception as e:
            logger.warning(f"⚠️ Could not parse notification body: {str(e)}")
        
        # Process in background
        from api.services.syncs.notification_processor import process_calendar_notification
        
        background_tasks.add_task(
            process_calendar_notification,
            channel_id=x_goog_channel_id,
            resource_state=x_goog_resource_state,
            data=data
        )
        
        # Return 200 immediately
        return {
            'success': True,
            'message': 'Calendar notification received and queued for processing'
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling Calendar webhook: {str(e)}")
        # Still return 200 to avoid Google retrying
        return {
            'success': False,
            'error': 'Internal error',
            'message': 'Notification acknowledged but processing failed'
        }


@router.get("/test")
async def test_webhook():
    """
    Test endpoint to verify webhooks are accessible
    """
    return {
        'success': True,
        'message': 'Webhook endpoint is accessible',
        'endpoints': {
            'gmail': '/api/webhooks/gmail',
            'calendar': '/api/webhooks/calendar'
        }
    }

