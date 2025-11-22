"""Delete task service."""

from lib.supabase_client import get_authenticated_supabase_client


async def delete_task(user_id: str, user_jwt: str, task_id: str) -> bool:
    """
    Delete a task and all its subtasks (CASCADE).
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        task_id: The ID of the task to delete
    
    Returns:
        True if deletion was successful
    
    Raises:
        Exception: If task deletion fails
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    response = (
        supabase.table("tasks")
        .delete()
        .eq("user_id", user_id)
        .eq("id", task_id)
        .execute()
    )
    
    # Supabase returns data even on delete if successful
    return True

