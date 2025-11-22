"""Update task service."""

from typing import Optional
from datetime import datetime
from lib.supabase_client import get_authenticated_supabase_client


async def update_task(
    user_id: str,
    user_jwt: str,
    task_id: str,
    title: Optional[str] = None,
    notes: Optional[str] = None,
    due_date: Optional[datetime] = None,
    position: Optional[int] = None,
    parent_id: Optional[str] = None
) -> dict:
    """
    Update a task.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        task_id: The ID of the task to update
        title: Optional new title
        notes: Optional new notes
        due_date: Optional new due date
        position: Optional new position
        parent_id: Optional new parent task ID
    
    Returns:
        The updated task data
    
    Raises:
        Exception: If task update fails
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    update_data = {}
    
    if title is not None:
        update_data["title"] = title
    
    if notes is not None:
        update_data["notes"] = notes
    
    if due_date is not None:
        update_data["due_date"] = due_date.isoformat()
    
    if position is not None:
        update_data["position"] = position
    
    if parent_id is not None:
        update_data["parent_id"] = parent_id
    
    if not update_data:
        raise Exception("No fields to update")
    
    response = (
        supabase.table("tasks")
        .update(update_data)
        .eq("user_id", user_id)
        .eq("id", task_id)
        .execute()
    )
    
    if not response.data:
        raise Exception("Failed to update task")
    
    return response.data[0]


async def reorder_tasks(
    user_id: str,
    user_jwt: str,
    task_positions: list[dict[str, any]]
) -> list[dict]:
    """
    Reorder multiple tasks at once.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        task_positions: List of dicts with 'id' and 'position' keys
    
    Returns:
        List of updated tasks
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    updated_tasks = []
    
    for task_pos in task_positions:
        task_id = task_pos.get("id")
        position = task_pos.get("position")
        
        if task_id and position is not None:
            response = (
                supabase.table("tasks")
                .update({"position": position})
                .eq("user_id", user_id)
                .eq("id", task_id)
                .execute()
            )
            
            if response.data:
                updated_tasks.extend(response.data)
    
    return updated_tasks

