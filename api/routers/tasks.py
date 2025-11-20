"""
Tasks router - HTTP endpoints for task management
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from api.services.tasks import TaskService

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"]
)


# Pydantic models for request/response validation
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[Task])
async def get_tasks():
    """Get all tasks"""
    return TaskService.get_all_tasks()


@router.post("/", response_model=Task, status_code=201)
async def create_task(task: TaskCreate):
    """Create a new task"""
    return TaskService.create_task(task.dict())


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: int):
    """Get a specific task by ID"""
    task = TaskService.get_task_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task


@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: int, task_update: TaskCreate):
    """Update a task"""
    updated_task = TaskService.update_task(task_id, task_update.dict())
    
    if not updated_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return updated_task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int):
    """Delete a task"""
    deleted = TaskService.delete_task(task_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
