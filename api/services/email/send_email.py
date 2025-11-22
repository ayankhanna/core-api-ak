"""
Email service - Send email operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from lib.supabase_client import get_authenticated_supabase_client
import logging
from googleapiclient.errors import HttpError
from .google_api_helpers import (
    get_gmail_service,
    create_message
)

logger = logging.getLogger(__name__)


def send_email(
    user_id: str,
    user_jwt: str,
    to: str,
    subject: str,
    body: str,
    cc: Optional[List[str]] = None,
    bcc: Optional[List[str]] = None,
    html_body: Optional[str] = None,
    thread_id: Optional[str] = None,
    in_reply_to: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send an email via Gmail
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        to: Recipient email address
        subject: Email subject
        body: Plain text email body
        cc: Optional list of CC recipients
        bcc: Optional list of BCC recipients
        html_body: Optional HTML version of email body
        thread_id: Optional thread ID to send as reply
        in_reply_to: Optional message ID this is replying to
        
    Returns:
        Dict with sent email details
    """
    auth_supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service or not connection_id:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Create MIME message
        message = create_message(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            bcc=bcc,
            html_body=html_body
        )
        
        # Add thread ID if this is a reply
        send_params = {
            'userId': 'me',
            'body': message
        }
        
        if thread_id:
            send_params['body']['threadId'] = thread_id
        
        # Send the message
        sent_message = service.users().messages().send(**send_params).execute()
        
        sent_id = sent_message.get('id')
        sent_thread_id = sent_message.get('threadId')
        
        logger.info(f"✅ Sent email {sent_id} for user {user_id}")
        
        # Fetch the sent message to get the 'from' field
        try:
            detailed_message = service.users().messages().get(
                userId='me',
                id=sent_id,
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name'].lower(): h['value'] for h in detailed_message['payload']['headers']}
            from_address = headers.get('from', '')
        except Exception as e:
            logger.warning(f"Could not fetch 'from' field for sent message: {e}")
            from_address = ''
        
        # Store in database
        to_addresses = [to] if to else []
        cc_addresses = cc if cc else []
        bcc_addresses = bcc if bcc else []
        
        # Use plain text body, or HTML if plain not available
        body_content = body or html_body or ''
        
        db_data = {
            'user_id': user_id,
            'ext_connection_id': connection_id,
            'external_id': sent_id,
            'thread_id': sent_thread_id,
            'subject': subject,
            'from': from_address,
            'to': to_addresses,
            'cc': cc_addresses if cc_addresses else None,
            'bcc': bcc_addresses if bcc_addresses else None,
            'body': body_content,
            'snippet': body[:100] if body else '',
            'labels': ['SENT'],
            'is_read': True,
            'received_at': datetime.now(timezone.utc).isoformat(),
            'raw_item': sent_message
        }
        
        auth_supabase.table('emails')\
            .insert(db_data)\
            .execute()
        
        return {
            "message": "Email sent successfully",
            "email": {
                'id': sent_id,
                'thread_id': sent_thread_id,
                'to': to,
                'subject': subject,
                'labels': sent_message.get('labelIds', [])
            }
        }
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to send email: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to send email: {str(e)}")


def reply_to_email(
    user_id: str,
    user_jwt: str,
    original_email_id: str,
    body: str,
    html_body: Optional[str] = None,
    reply_all: bool = False
) -> Dict[str, Any]:
    """
    Reply to an existing email
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        original_email_id: ID of the email to reply to
        body: Reply body text
        html_body: Optional HTML version of reply body
        reply_all: Whether to reply to all recipients (default False)
        
    Returns:
        Dict with sent reply details
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Get original message to extract thread ID and recipients
        original = service.users().messages().get(
            userId='me',
            id=original_email_id,
            format='metadata',
            metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Message-ID']
        ).execute()
        
        thread_id = original.get('threadId')
        headers = {h['name'].lower(): h['value'] for h in original['payload']['headers']}
        
        # Determine recipients
        original_from = headers.get('from', '')
        original_subject = headers.get('subject', '')
        message_id = headers.get('message-id', '')
        
        # Parse "from" to get email address
        import re
        from_match = re.search(r'<(.+?)>', original_from)
        to_address = from_match.group(1) if from_match else original_from.strip()
        
        # Build reply subject
        if not original_subject.lower().startswith('re:'):
            reply_subject = f"Re: {original_subject}"
        else:
            reply_subject = original_subject
        
        # Get CC list if reply all
        cc_list = None
        if reply_all:
            original_to = headers.get('to', '')
            original_cc = headers.get('cc', '')
            # Parse and combine recipients (excluding self)
            # This is simplified - production would need better email parsing
            cc_addresses = []
            if original_to:
                cc_addresses.extend([a.strip() for a in original_to.split(',')])
            if original_cc:
                cc_addresses.extend([a.strip() for a in original_cc.split(',')])
            # TODO: Filter out user's own email address
            cc_list = cc_addresses if cc_addresses else None
        
        # Send the reply
        return send_email(
            user_id=user_id,
            user_jwt=user_jwt,
            to=to_address,
            subject=reply_subject,
            body=body,
            html_body=html_body,
            cc=cc_list,
            thread_id=thread_id,
            in_reply_to=message_id
        )
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to reply to email: {str(e)}")
    except Exception as e:
        logger.error(f"Error replying to email: {str(e)}")
        raise ValueError(f"Failed to reply: {str(e)}")


def forward_email(
    user_id: str,
    user_jwt: str,
    original_email_id: str,
    to: str,
    additional_message: Optional[str] = None,
    cc: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Forward an existing email to new recipients
    
    Args:
        user_id: User's ID
        user_jwt: User's Supabase JWT for authenticated requests
        original_email_id: ID of the email to forward
        to: Recipient email address
        additional_message: Optional message to prepend to forwarded content
        cc: Optional list of CC recipients
        
    Returns:
        Dict with forwarded email details
    """
    # Get Gmail service
    service, connection_id = get_gmail_service(user_id, user_jwt)
    
    if not service:
        raise ValueError("No active Google connection found for user. Please sign in with Google first.")
    
    try:
        # Get original message
        from .google_api_helpers import parse_email_headers, decode_email_body
        
        original = service.users().messages().get(
            userId='me',
            id=original_email_id,
            format='full'
        ).execute()
        
        headers = parse_email_headers(original['payload']['headers'])
        body = decode_email_body(original['payload'])
        
        # Build forwarded subject
        original_subject = headers.get('subject', '')
        if not original_subject.lower().startswith('fwd:'):
            forward_subject = f"Fwd: {original_subject}"
        else:
            forward_subject = original_subject
        
        # Build forwarded body
        forwarded_body = ""
        if additional_message:
            forwarded_body += f"{additional_message}\n\n"
        
        forwarded_body += "---------- Forwarded message ---------\n"
        forwarded_body += f"From: {headers.get('from', '')}\n"
        forwarded_body += f"Date: {headers.get('date', '')}\n"
        forwarded_body += f"Subject: {original_subject}\n"
        forwarded_body += f"To: {headers.get('to', '')}\n\n"
        forwarded_body += body.get('plain', '')
        
        # Send the forward
        return send_email(
            user_id=user_id,
            user_jwt=user_jwt,
            to=to,
            subject=forward_subject,
            body=forwarded_body,
            html_body=body.get('html') if not additional_message else None,
            cc=cc
        )
        
    except HttpError as e:
        logger.error(f"Gmail API error: {str(e)}")
        raise ValueError(f"Failed to forward email: {str(e)}")
    except Exception as e:
        logger.error(f"Error forwarding email: {str(e)}")
        raise ValueError(f"Failed to forward: {str(e)}")

