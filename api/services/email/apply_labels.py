"""
Email service - Label operations
"""
from typing import Dict, Any, List
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import get_gmail_service, convert_to_gmail_label_ids

logger = logging.getLogger(__name__)


def get_labels(
    user_id: str,
    user_jwt: str
) -> Dict[str, Any]:
    """
    Get all available labels for the user
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        
    Returns:
        Dict with list of labels
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        labels_result = service.users().labels().list(userId='me').execute()
        labels = labels_result.get('labels', [])
        
        # Format labels for easy consumption
        formatted_labels = [
            {
                'id': label['id'],
                'name': label['name'],
                'type': label.get('type', 'user'),
                'message_list_visibility': label.get('messageListVisibility'),
                'label_list_visibility': label.get('labelListVisibility')
            }
            for label in labels
        ]
        
        return {
            "message": f"Retrieved {len(formatted_labels)} labels",
            "labels": formatted_labels,
            "count": len(formatted_labels)
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to get labels: {str(e)}")


def apply_labels(
    user_id: str,
    user_jwt: str,
    email_id: str,
    label_names: List[str]
) -> Dict[str, Any]:
    """
    Apply labels to an email
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID
        label_names: List of label names to apply (e.g., ['IMPORTANT', 'Work'])
        
    Returns:
        Dict with updated labels
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Convert label names to IDs
        label_ids = convert_to_gmail_label_ids(label_names, service)
        
        if not label_ids:
            return {
                "message": "No valid labels to apply",
                "email_id": email_id,
                "labels": []
            }
        
        # Apply labels
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'addLabelIds': label_ids}
        ).execute()
        
        all_labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Applied labels {label_names} to email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({'labels': all_labels})\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Labels applied successfully",
            "email_id": email_id,
            "added_labels": label_names,
            "all_labels": all_labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to apply labels: {str(e)}")
    except Exception as e:
        logger.error(f"Error applying labels: {str(e)}")
        raise ValueError(f"Failed to apply labels: {str(e)}")


def remove_labels(
    user_id: str,
    user_jwt: str,
    email_id: str,
    label_names: List[str]
) -> Dict[str, Any]:
    """
    Remove labels from an email
    Two-way sync with database
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        email_id: Gmail message ID
        label_names: List of label names to remove (e.g., ['IMPORTANT', 'Work'])
        
    Returns:
        Dict with updated labels
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Convert label names to IDs
        label_ids = convert_to_gmail_label_ids(label_names, service)
        
        if not label_ids:
            return {
                "message": "No valid labels to remove",
                "email_id": email_id,
                "labels": []
            }
        
        # Remove labels
        updated = service.users().messages().modify(
            userId='me',
            id=email_id,
            body={'removeLabelIds': label_ids}
        ).execute()
        
        all_labels = updated.get('labelIds', [])
        
        logger.info(f"✅ Removed labels {label_names} from email {email_id} for user {user_id}")
        
        # Update in database
        auth_supabase.table('emails')\
            .update({'labels': all_labels})\
            .eq('user_id', user_id)\
            .eq('external_id', email_id)\
            .execute()
        
        return {
            "message": "Labels removed successfully",
            "email_id": email_id,
            "removed_labels": label_names,
            "all_labels": all_labels,
            "synced_to_google": True
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to remove labels: {str(e)}")
    except Exception as e:
        logger.error(f"Error removing labels: {str(e)}")
        raise ValueError(f"Failed to remove labels: {str(e)}")


def create_label(
    user_id: str,
    user_jwt: str,
    label_name: str,
    label_list_visibility: str = 'labelShow',
    message_list_visibility: str = 'show'
) -> Dict[str, Any]:
    """
    Create a new custom label
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        label_name: Name for the new label
        label_list_visibility: Visibility in label list ('labelShow', 'labelHide', 'labelShowIfUnread')
        message_list_visibility: Visibility in message list ('show', 'hide')
        
    Returns:
        Dict with created label details
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        label_body = {
            'name': label_name,
            'labelListVisibility': label_list_visibility,
            'messageListVisibility': message_list_visibility
        }
        
        created_label = service.users().labels().create(
            userId='me',
            body=label_body
        ).execute()
        
        logger.info(f"✅ Created label '{label_name}' for user {user_id}")
        
        return {
            "message": "Label created successfully",
            "label": {
                'id': created_label['id'],
                'name': created_label['name'],
                'type': created_label.get('type', 'user')
            }
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to create label: {str(e)}")


def delete_label(
    user_id: str,
    user_jwt: str,
    label_id: str
) -> Dict[str, Any]:
    """
    Delete a custom label
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        label_id: Gmail label ID to delete
        
    Returns:
        Dict with deletion confirmation
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        service.users().labels().delete(
            userId='me',
            id=label_id
        ).execute()
        
        logger.info(f"✅ Deleted label {label_id} for user {user_id}")
        
        return {
            "message": "Label deleted successfully",
            "label_id": label_id
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to delete label: {str(e)}")


