"""
Email router - HTTP endpoints for email operations
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from pydantic import BaseModel
from api.services.email import (
    fetch_emails,
    get_email_details,
    send_email,
    create_draft,
    update_draft,
    delete_draft,
    delete_email,
    archive_email,
    apply_labels,
    remove_labels,
    get_labels,
    mark_as_read,
    mark_as_unread
)
from api.services.syncs import sync_gmail
from api.dependencies import get_current_user_jwt
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])


# Pydantic models for request validation
class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    html_body: Optional[str] = None
    thread_id: Optional[str] = None


class CreateDraftRequest(BaseModel):
    to: Optional[str] = None
    subject: str = ""
    body: str = ""
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    html_body: Optional[str] = None


class UpdateDraftRequest(BaseModel):
    to: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    html_body: Optional[str] = None


class ApplyLabelsRequest(BaseModel):
    label_names: List[str]


# Email fetch endpoints
@router.get("/messages")
async def fetch_emails_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
    max_results: int = 50,
    query: Optional[str] = None
):
    """
    Fetch emails from Gmail with optional filtering.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Fetching emails for user {user_id}")
        result = fetch_emails(user_id, user_jwt, max_results, query)
        logger.info(f"✅ Fetched {result.get('count', 0)} emails")
        return result
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching emails: {error_str}")
        
        if 'JWT expired' in error_str or 'PGRST303' in error_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your session has expired. Please sign in again."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch emails: {error_str}"
        )


@router.get("/messages/{email_id}")
async def get_email_details_endpoint(
    email_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Get full details of a specific email including body content.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Fetching email details for {email_id}")
        result = get_email_details(user_id, user_jwt, email_id)
        logger.info(f"✅ Email details retrieved")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching email details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch email details: {str(e)}"
        )


# Send email endpoints
@router.post("/send")
async def send_email_endpoint(
    user_id: str,
    email_data: SendEmailRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Send an email via Gmail.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Sending email for user {user_id}")
        result = send_email(
            user_id=user_id,
            user_jwt=user_jwt,
            to=email_data.to,
            subject=email_data.subject,
            body=email_data.body,
            cc=email_data.cc,
            bcc=email_data.bcc,
            html_body=email_data.html_body,
            thread_id=email_data.thread_id
        )
        logger.info(f"✅ Email sent successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error sending email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


# Draft endpoints
@router.post("/drafts")
async def create_draft_endpoint(
    user_id: str,
    draft_data: CreateDraftRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Create a draft email.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Creating draft for user {user_id}")
        result = create_draft(
            user_id=user_id,
            user_jwt=user_jwt,
            to=draft_data.to,
            subject=draft_data.subject,
            body=draft_data.body,
            cc=draft_data.cc,
            bcc=draft_data.bcc,
            html_body=draft_data.html_body
        )
        logger.info(f"✅ Draft created successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error creating draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create draft: {str(e)}"
        )


@router.put("/drafts/{draft_id}")
async def update_draft_endpoint(
    draft_id: str,
    user_id: str,
    draft_data: UpdateDraftRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Update an existing draft email.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Updating draft {draft_id} for user {user_id}")
        result = update_draft(
            user_id=user_id,
            user_jwt=user_jwt,
            draft_id=draft_id,
            to=draft_data.to,
            subject=draft_data.subject,
            body=draft_data.body,
            cc=draft_data.cc,
            bcc=draft_data.bcc,
            html_body=draft_data.html_body
        )
        logger.info(f"✅ Draft updated successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error updating draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update draft: {str(e)}"
        )


@router.delete("/drafts/{draft_id}")
async def delete_draft_endpoint(
    draft_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Delete a draft email.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Deleting draft {draft_id} for user {user_id}")
        result = delete_draft(user_id, user_jwt, draft_id)
        logger.info(f"✅ Draft deleted successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error deleting draft: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete draft: {str(e)}"
        )


# Email action endpoints
@router.delete("/messages/{email_id}")
async def delete_email_endpoint(
    email_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt),
    permanently: bool = False
):
    """
    Delete an email (move to trash or permanently delete).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Deleting email {email_id} for user {user_id} (permanent: {permanently})")
        result = delete_email(user_id, user_jwt, email_id, permanently)
        logger.info(f"✅ Email deleted successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error deleting email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete email: {str(e)}"
        )


@router.post("/messages/{email_id}/archive")
async def archive_email_endpoint(
    email_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Archive an email (remove from inbox).
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Archiving email {email_id} for user {user_id}")
        result = archive_email(user_id, user_jwt, email_id)
        logger.info(f"✅ Email archived successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error archiving email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive email: {str(e)}"
        )


@router.post("/messages/{email_id}/mark-read")
async def mark_read_endpoint(
    email_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Mark an email as read.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Marking email {email_id} as read for user {user_id}")
        result = mark_as_read(user_id, user_jwt, email_id)
        logger.info(f"✅ Email marked as read")
        return result
    except Exception as e:
        logger.error(f"❌ Error marking email as read: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark email as read: {str(e)}"
        )


@router.post("/messages/{email_id}/mark-unread")
async def mark_unread_endpoint(
    email_id: str,
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Mark an email as unread.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Marking email {email_id} as unread for user {user_id}")
        result = mark_as_unread(user_id, user_jwt, email_id)
        logger.info(f"✅ Email marked as unread")
        return result
    except Exception as e:
        logger.error(f"❌ Error marking email as unread: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark email as unread: {str(e)}"
        )


# Label endpoints
@router.get("/labels")
async def get_labels_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Get all available Gmail labels for the user.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Fetching labels for user {user_id}")
        result = get_labels(user_id, user_jwt)
        logger.info(f"✅ Fetched {result.get('count', 0)} labels")
        return result
    except Exception as e:
        logger.error(f"❌ Error fetching labels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch labels: {str(e)}"
        )


@router.post("/messages/{email_id}/labels")
async def apply_labels_endpoint(
    email_id: str,
    user_id: str,
    labels_data: ApplyLabelsRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Apply labels to an email.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Applying labels to email {email_id} for user {user_id}")
        result = apply_labels(user_id, user_jwt, email_id, labels_data.label_names)
        logger.info(f"✅ Labels applied successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error applying labels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply labels: {str(e)}"
        )


@router.delete("/messages/{email_id}/labels")
async def remove_labels_endpoint(
    email_id: str,
    user_id: str,
    labels_data: ApplyLabelsRequest,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Remove labels from an email.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📧 Removing labels from email {email_id} for user {user_id}")
        result = remove_labels(user_id, user_jwt, email_id, labels_data.label_names)
        logger.info(f"✅ Labels removed successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Error removing labels: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove labels: {str(e)}"
        )


# Sync endpoint
@router.post("/sync")
async def sync_gmail_endpoint(
    user_id: str,
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Sync emails from Gmail to database.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🔄 Syncing Gmail for user {user_id}")
        result = sync_gmail(user_id, user_jwt)
        logger.info(f"✅ Sync completed for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error syncing Gmail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync Gmail: {str(e)}"
        )



