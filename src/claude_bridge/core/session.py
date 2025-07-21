"""
Session data model for Claude Bridge

Defines the Session dataclass that represents an active Claude Code session.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Any
import subprocess
import discord


@dataclass
class Session:
    """Represents an active Claude Code session"""
    
    id: str
    claude_process: Optional[subprocess.Popen] = None
    discord_channel: Optional[discord.TextChannel] = None
    status: str = "inactive"  # "active", "inactive", "terminated"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    command_history: List[str] = field(default_factory=list)
    output_buffer: List[str] = field(default_factory=list)
    working_directory: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup"""
        if not self.id:
            raise ValueError("Session ID cannot be empty")
    
    def is_active(self) -> bool:
        """Check if the session is currently active"""
        return (
            self.status == "active" and 
            self.claude_process is not None and 
            self.claude_process.poll() is None
        )
    
    def is_expired(self, timeout_seconds: int = 3600) -> bool:
        """Check if the session has expired based on last activity"""
        if self.status == "terminated":
            return True
            
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        return elapsed > timeout_seconds
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
    
    def add_command(self, command: str):
        """Add a command to the history"""
        self.command_history.append(command)
        self.update_activity()
        
        # Keep only last 100 commands
        if len(self.command_history) > 100:
            self.command_history = self.command_history[-100:]
    
    def add_output(self, output: str):
        """Add output to the buffer"""
        self.output_buffer.append(output)
        self.update_activity()
        
        # Keep only last 50 outputs
        if len(self.output_buffer) > 50:
            self.output_buffer = self.output_buffer[-50:]
    
    def get_recent_commands(self, count: int = 10) -> List[str]:
        """Get recent commands from history"""
        return self.command_history[-count:] if self.command_history else []
    
    def get_recent_output(self, count: int = 10) -> List[str]:
        """Get recent output from buffer"""
        return self.output_buffer[-count:] if self.output_buffer else []
    
    def terminate(self):
        """Mark the session as terminated and clean up"""
        self.status = "terminated"
        self.update_activity()
        
        if self.claude_process and self.claude_process.poll() is None:
            try:
                self.claude_process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.claude_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    self.claude_process.kill()
            except Exception:
                # Process might already be dead
                pass
    
    def to_dict(self) -> dict:
        """Convert session to dictionary representation"""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "command_count": len(self.command_history),
            "output_count": len(self.output_buffer),
            "working_directory": self.working_directory,
            "is_active": self.is_active()
        }