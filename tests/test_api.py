import pytest
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_root():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "core-api"

def test_get_tasks():
    """Test getting all tasks"""
    response = client.get("/api/tasks/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_create_task():
    """Test creating a new task"""
    task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "completed": False
    }
    response = client.post("/api/tasks/", json=task_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert "id" in data

def test_get_task_by_id():
    """Test getting a specific task"""
    # First create a task
    task_data = {"title": "Test Task", "completed": False}
    create_response = client.post("/api/tasks/", json=task_data)
    task_id = create_response.json()["id"]
    
    # Then retrieve it
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id

def test_update_task():
    """Test updating a task"""
    # Create a task
    task_data = {"title": "Original Title", "completed": False}
    create_response = client.post("/api/tasks/", json=task_data)
    task_id = create_response.json()["id"]
    
    # Update it
    updated_data = {"title": "Updated Title", "completed": True}
    response = client.put(f"/api/tasks/{task_id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["completed"] is True

def test_delete_task():
    """Test deleting a task"""
    # Create a task
    task_data = {"title": "Task to Delete", "completed": False}
    create_response = client.post("/api/tasks/", json=task_data)
    task_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/tasks/{task_id}")
    assert get_response.status_code == 404



