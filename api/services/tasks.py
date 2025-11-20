"""
Tasks service - Business logic for task management operations
"""
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class TaskService:
    """Service class for task operations"""
    
    # Temporary in-memory storage
    # TODO: Replace with database integration when ready
    _tasks_db: List[Dict[str, Any]] = []
    _task_id_counter: int = 1

    @classmethod
    def get_all_tasks(cls) -> List[Dict[str, Any]]:
        """Get all tasks"""
        return cls._tasks_db

    @classmethod
    def create_task(cls, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new task"""
        new_task = {
            'id': cls._task_id_counter,
            'title': task_data.get('title'),
            'description': task_data.get('description'),
            'completed': task_data.get('completed', False)
        }
        
        cls._tasks_db.append(new_task)
        cls._task_id_counter += 1
        
        logger.info(f"Created task with ID {new_task['id']}")
        return new_task

    @classmethod
    def get_task_by_id(cls, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        for task in cls._tasks_db:
            if task['id'] == task_id:
                return task
        return None

    @classmethod
    def update_task(cls, task_id: int, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a task"""
        for idx, task in enumerate(cls._tasks_db):
            if task['id'] == task_id:
                updated_task = {
                    'id': task_id,
                    'title': task_data.get('title'),
                    'description': task_data.get('description'),
                    'completed': task_data.get('completed', False)
                }
                cls._tasks_db[idx] = updated_task
                logger.info(f"Updated task {task_id}")
                return updated_task
        return None

    @classmethod
    def delete_task(cls, task_id: int) -> bool:
        """
        Delete a task
        Returns True if deleted, False if not found
        """
        for idx, task in enumerate(cls._tasks_db):
            if task['id'] == task_id:
                cls._tasks_db.pop(idx)
                logger.info(f"Deleted task {task_id}")
                return True
        return False



