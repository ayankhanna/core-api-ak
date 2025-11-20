"""
Services package - Business logic layer for the API
All functional logic should be implemented here, separate from HTTP routing
"""

# Lazy imports to avoid import-time crashes
def __getattr__(name):
    """Lazy load services only when accessed"""
    if name == "AuthService":
        from api.services.auth import AuthService
        return AuthService
    elif name == "TaskService":
        from api.services.tasks import TaskService
        return TaskService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ['AuthService', 'TaskService']
