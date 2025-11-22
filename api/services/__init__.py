"""
Services package - Business logic layer for the API
All functional logic should be implemented here, separate from HTTP routing
"""
from api.services.auth import AuthService

__all__ = ['AuthService']


