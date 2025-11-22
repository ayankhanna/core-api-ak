"""Complete task service."""

from lib.supabase_client import get_authenticated_supabase_client


async def toggle_task_completion(
    user_id: str,
    user_jwt: str,
    task_id: str,
    completed: bool
) -> dict:
    """
    Toggle task completion status.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        task_id: The ID of the task
        completed: New completion status
    
    Returns:
        The updated task data
    
    Raises:
        Exception: If update fails
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    response = (
        supabase.table("tasks")
        .update({"completed": completed})
        .eq("user_id", user_id)
        .eq("id", task_id)
        .execute()
    )
    
    if not response.data:
        raise Exception("Failed to update task completion status")
    
    return response.data[0]

