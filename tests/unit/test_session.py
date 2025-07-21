"""
Unit tests for Session
"""

import pytest
from datetime import datetime, timedelta
from src.claude_bridge.core.session import Session


class TestSession:
    """Test cases for Session data model"""
    
    def test_session_creation(self):
        """Test session creation with required parameters"""
        session = Session(id="TEST123")
        
        assert session.id == "TEST123"
        assert session.status == "inactive"
        assert session.command_history == []
        assert session.output_buffer == []
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
    
    def test_session_creation_empty_id(self):
        """Test that empty session ID raises ValueError"""
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            Session(id="")
    
    def test_is_active(self):
        """Test is_active method"""
        session = Session(id="TEST123")
        
        # Initially should not be active (no process)
        assert not session.is_active()
        
        # Set status to active but no process
        session.status = "active"
        assert not session.is_active()
        
        # Mock process would be needed for full test
        # This tests the basic logic
    
    def test_is_expired(self):
        """Test session expiration logic"""
        session = Session(id="TEST123")
        
        # Fresh session should not be expired
        assert not session.is_expired(3600)  # 1 hour timeout
        
        # Set old last_activity
        session.last_activity = datetime.now() - timedelta(hours=2)
        assert session.is_expired(3600)  # Should be expired
        
        # Terminated session should always be expired
        session.status = "terminated"
        session.last_activity = datetime.now()  # Even if recent
        assert session.is_expired(3600)
    
    def test_update_activity(self):
        """Test activity timestamp updating"""
        session = Session(id="TEST123")
        original_time = session.last_activity
        
        # Wait a bit to ensure time difference
        import time
        time.sleep(0.01)
        
        session.update_activity()
        assert session.last_activity > original_time
    
    def test_add_command(self):
        """Test command history management"""
        session = Session(id="TEST123")
        
        # Add some commands
        session.add_command("help")
        session.add_command("status")
        session.add_command("connect ABC123")
        
        assert len(session.command_history) == 3
        assert session.command_history[-1] == "connect ABC123"
        
        # Test history limit (should keep last 100)
        for i in range(150):
            session.add_command(f"command_{i}")
        
        assert len(session.command_history) <= 100
        assert "command_149" in session.command_history
        assert "command_0" not in session.command_history
    
    def test_add_output(self):
        """Test output buffer management"""
        session = Session(id="TEST123")
        
        # Add some output
        session.add_output("Starting Claude Code...")
        session.add_output("Ready for input")
        session.add_output("Processing command...")
        
        assert len(session.output_buffer) == 3
        assert session.output_buffer[-1] == "Processing command..."
        
        # Test output limit (should keep last 50)
        for i in range(80):
            session.add_output(f"Output line {i}")
        
        assert len(session.output_buffer) <= 50
        assert "Output line 79" in session.output_buffer
        assert "Output line 0" not in session.output_buffer
    
    def test_get_recent_commands(self):
        """Test getting recent commands"""
        session = Session(id="TEST123")
        
        # Add commands
        commands = ["help", "status", "connect ABC123", "output", "history"]
        for cmd in commands:
            session.add_command(cmd)
        
        # Get recent commands
        recent = session.get_recent_commands(3)
        assert len(recent) == 3
        assert recent == ["connect ABC123", "output", "history"]
        
        # Get more than available
        recent = session.get_recent_commands(10)
        assert len(recent) == 5
        assert recent == commands
        
        # Empty history
        empty_session = Session(id="EMPTY")
        assert empty_session.get_recent_commands(5) == []
    
    def test_get_recent_output(self):
        """Test getting recent output"""
        session = Session(id="TEST123")
        
        # Add output
        outputs = ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"]
        for output in outputs:
            session.add_output(output)
        
        # Get recent output
        recent = session.get_recent_output(3)
        assert len(recent) == 3
        assert recent == ["Line 3", "Line 4", "Line 5"]
        
        # Get more than available
        recent = session.get_recent_output(10)
        assert len(recent) == 5
        assert recent == outputs
        
        # Empty output
        empty_session = Session(id="EMPTY")
        assert empty_session.get_recent_output(5) == []
    
    def test_terminate(self):
        """Test session termination"""
        session = Session(id="TEST123")
        original_time = session.last_activity
        
        session.terminate()
        
        assert session.status == "terminated"
        assert session.last_activity > original_time
        
        # Process termination would be tested with mock process
    
    def test_to_dict(self):
        """Test dictionary conversion"""
        session = Session(id="TEST123", working_directory="/workspace")
        session.add_command("test command")
        session.add_output("test output")
        
        result = session.to_dict()
        
        assert result["id"] == "TEST123"
        assert result["status"] == "inactive"
        assert result["command_count"] == 1
        assert result["output_count"] == 1
        assert result["working_directory"] == "/workspace"
        assert result["is_active"] == False
        assert "created_at" in result
        assert "last_activity" in result
        
        # Check datetime serialization
        assert isinstance(result["created_at"], str)
        assert isinstance(result["last_activity"], str)


if __name__ == "__main__":
    pytest.main([__file__])