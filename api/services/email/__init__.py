"""
Email services for Gmail operations
"""
from .fetch_emails import fetch_emails, get_email_by_id
from .get_email_details import get_email_details
from .send_email import send_email
from .create_draft import create_draft
from .update_draft import update_draft
from .delete_draft import delete_draft
from .delete_email import delete_email
from .archive_email import archive_email
from .apply_labels import apply_labels, remove_labels, get_labels
from .mark_read_unread import mark_as_read, mark_as_unread

__all__ = [
    'fetch_emails',
    'get_email_by_id',
    'get_email_details',
    'send_email',
    'create_draft',
    'update_draft',
    'delete_draft',
    'delete_email',
    'archive_email',
    'apply_labels',
    'remove_labels',
    'get_labels',
    'mark_as_read',
    'mark_as_unread'
]


