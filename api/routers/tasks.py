"""
Tasks router - HTTP endpoints for task management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from api.services.tasks import (
    create_task,
    get_tasks,
    get_task_tree,
    update_task,
    delete_task,
    toggle_task_completion,
)
from api.services.tasks.update_task import reorder_tasks
from api.dependencies import get_current_user_jwt, get_current_user_id
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# Pydantic models for request validation
class CreateTaskRequest(BaseModel):
    title: str
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    parent_id: Optional[str] = None
    position: int = 0


class UpdateTaskRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None
    parent_id: Optional[str] = None


class ToggleCompletionRequest(BaseModel):
    completed: bool


class ReorderTasksRequest(BaseModel):
    task_positions: List[dict]


# Get tasks endpoints
@router.get("/")
async def get_tasks_endpoint(
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt),
    parent_id: Optional[str] = None,
    include_completed: bool = True
):
    """
    Get tasks for a user, optionally filtered by parent.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"📋 Fetching tasks for user {user_id}")
        tasks = await get_tasks(user_id, user_jwt, parent_id, include_completed)
        logger.info(f"✅ Fetched {len(tasks)} tasks")
        return {"tasks": tasks}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching tasks: {error_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tasks: {error_str}"
        )


@router.get("/tree")
async def get_task_tree_endpoint(
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt),
    include_completed: bool = True
):
    """
    Get all tasks in a tree structure.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🌳 Fetching task tree for user {user_id}")
        task_tree = await get_task_tree(user_id, user_jwt, include_completed)
        logger.info(f"✅ Fetched task tree with {len(task_tree)} root tasks")
        return {"tasks": task_tree}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error fetching task tree: {error_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task tree: {error_str}"
        )


# Create task endpoint
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task_endpoint(
    request: CreateTaskRequest,
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Create a new task.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"➕ Creating task for user {user_id}: {request.title}")
        task = await create_task(
            user_id=user_id,
            user_jwt=user_jwt,
            title=request.title,
            notes=request.notes,
            due_date=request.due_date,
            parent_id=request.parent_id,
            position=request.position
        )
        logger.info(f"✅ Created task {task['id']}")
        return {"task": task}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error creating task: {error_str}")
        
        if "Maximum nesting level" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum nesting level (5) reached"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {error_str}"
        )


# Update task endpoint
@router.patch("/{task_id}")
async def update_task_endpoint(
    task_id: str,
    request: UpdateTaskRequest,
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Update a task.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"✏️ Updating task {task_id} for user {user_id}")
        task = await update_task(
            user_id=user_id,
            user_jwt=user_jwt,
            task_id=task_id,
            title=request.title,
            notes=request.notes,
            due_date=request.due_date,
            position=request.position,
            parent_id=request.parent_id
        )
        logger.info(f"✅ Updated task {task_id}")
        return {"task": task}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error updating task: {error_str}")
        
        if "No fields to update" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        if "Maximum nesting level" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum nesting level (5) reached"
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {error_str}"
        )


# Toggle completion endpoint
@router.patch("/{task_id}/completion")
async def toggle_completion_endpoint(
    task_id: str,
    request: ToggleCompletionRequest,
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Toggle task completion status.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"✅ Toggling completion for task {task_id}: {request.completed}")
        task = await toggle_task_completion(user_id, user_jwt, task_id, request.completed)
        logger.info(f"✅ Toggled completion for task {task_id}")
        return {"task": task}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error toggling task completion: {error_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle task completion: {error_str}"
        )


# Reorder tasks endpoint
@router.post("/reorder")
async def reorder_tasks_endpoint(
    request: ReorderTasksRequest,
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Reorder multiple tasks at once.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🔄 Reordering {len(request.task_positions)} tasks for user {user_id}")
        tasks = await reorder_tasks(user_id, user_jwt, request.task_positions)
        logger.info(f"✅ Reordered tasks")
        return {"tasks": tasks}
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error reordering tasks: {error_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reorder tasks: {error_str}"
        )


# Delete task endpoint
@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_endpoint(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    user_jwt: str = Depends(get_current_user_jwt)
):
    """
    Delete a task and all its subtasks.
    Requires: Authorization header with user's Supabase JWT
    """
    try:
        logger.info(f"🗑️ Deleting task {task_id} for user {user_id}")
        await delete_task(user_id, user_jwt, task_id)
        logger.info(f"✅ Deleted task {task_id}")
        return None
    except Exception as e:
        error_str = str(e)
        logger.error(f"❌ Error deleting task: {error_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {error_str}"
        )
