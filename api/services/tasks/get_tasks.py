"""Get tasks service."""

from typing import Optional, List, Dict, Any
from lib.supabase_client import get_authenticated_supabase_client


async def get_tasks(
    user_id: str,
    user_jwt: str,
    parent_id: Optional[str] = None,
    include_completed: bool = True
) -> List[Dict[str, Any]]:
    """
    Get tasks for a user, optionally filtered by parent.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        parent_id: Optional parent task ID to filter by
        include_completed: Whether to include completed tasks
    
    Returns:
        List of tasks
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    query = supabase.table("tasks").select("*").eq("user_id", user_id)
    
    if parent_id is None:
        query = query.is_("parent_id", "null")
    else:
        query = query.eq("parent_id", parent_id)
    
    if not include_completed:
        query = query.eq("completed", False)
    
    query = query.order("position", desc=False).order("created_at", desc=False)
    
    response = query.execute()
    
    return response.data if response.data else []


async def get_task_tree(user_id: str, user_jwt: str, include_completed: bool = True) -> List[Dict[str, Any]]:
    """
    Get all tasks in a tree structure.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        include_completed: Whether to include completed tasks
    
    Returns:
        List of tasks with nested children
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    # Get all tasks for the user
    query = supabase.table("tasks").select("*").eq("user_id", user_id)
    
    if not include_completed:
        query = query.eq("completed", False)
    
    query = query.order("position", desc=False).order("created_at", desc=False)
    
    response = query.execute()
    
    if not response.data:
        return []
    
    # Build a map of tasks by ID
    task_map = {task["id"]: {**task, "children": []} for task in response.data}
    
    # Build the tree
    root_tasks = []
    
    for task in response.data:
        if task["parent_id"] is None:
            root_tasks.append(task_map[task["id"]])
        else:
            parent = task_map.get(task["parent_id"])
            if parent:
                parent["children"].append(task_map[task["id"]])
    
    return root_tasks


async def get_task_by_id(user_id: str, user_jwt: str, task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific task by ID.
    
    Args:
        user_id: The ID of the user
        user_jwt: The user's JWT token for authentication
        task_id: The ID of the task
    
    Returns:
        The task data or None if not found
    """
    supabase = get_authenticated_supabase_client(user_jwt)
    
    response = (
        supabase.table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .eq("id", task_id)
        .execute()
    )
    
    if response.data and len(response.data) > 0:
        return response.data[0]
    
    return None

