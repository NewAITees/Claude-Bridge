"""
Core components for Claude Bridge

Contains session management, data models, and core business logic.
"""

from .session import Session
from .session_manager import SessionManager

__all__ = ["Session", "SessionManager"]