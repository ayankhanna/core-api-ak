"""Create task service."""

from typing import Optional
from datetime import datetime
from lib.supabase_client import get_authenticated_supabase_client


async def create_task(
    user_id: str,
    user_jwt: str,
    title: str,
    notes: Optional[str] = None,
    due_date: Optional[datetime] = None,
    parent_id: Optional[str] = None,
    position: int = 0
) -> dict:
    """
    Create a new task.
    
    Args:
        user_id: The ID of the user creating the task
        user_jwt: The user's JWT token for authentication
        title: The title of the task
        notes: Optional notes for the task
        due_date: Optional due date for the task
        parent_id: Optional parent task ID for subtasks
        position: Position in the list (default: 0)
    
    Returns:
        The created task data
    
    Raises:
        Exception: If task creation fails
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    task_data = {
        "user_id": user_id,
        "title": title,
        "position": position,
    }
    
    if notes is not None:
        task_data["notes"] = notes
    
    if due_date is not None:
        task_data["due_date"] = due_date.isoformat()
    
    if parent_id is not None:
        task_data["parent_id"] = parent_id
    
    response = supabase.table("tasks").insert(task_data).execute()
    
    if not response.data:
        raise Exception("Failed to create task")
    
    return response.data[0]

