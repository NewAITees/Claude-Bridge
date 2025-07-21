"""
Claude Bridge - Multi-Interface Session Bridge for Claude Code

A bridge application that allows interactive sessions with Claude Code
to be operated simultaneously from both PC Terminal and Discord app.
"""

__version__ = "1.0.0"
__author__ = "Claude Bridge Team"
__email__ = "support@claude-bridge.dev"

from .core.session_manager import SessionManager
from .core.session import Session
from .process_control.process_controller import ProcessController
from .discord_bot.bot import ClaudeBridgeBot
from .output_handling.output_handler import OutputHandler

__all__ = [
    "SessionManager",
    "Session", 
    "ProcessController",
    "ClaudeBridgeBot",
    "OutputHandler"
]