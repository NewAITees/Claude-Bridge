"""
Integration tests for Claude Bridge system components

Tests the interaction between different components and end-to-end functionality.
"""

import asyncio
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import discord
from discord.ext import commands

from src.claude_bridge.core.session_manager import SessionManager
from src.claude_bridge.discord_bot.bot import ClaudeBridgeBot
from src.claude_bridge.output_handling.output_buffer import BufferManager
from src.claude_bridge.discord_bot.ui_components import UIConverter
from src.claude_bridge.discord_bot.progress_display import ProgressManager
from src.claude_bridge.utils.config import Config
from src.claude_bridge.utils.error_handler import ErrorHandler
from src.claude_bridge.utils.performance_monitor import PerformanceMonitor


@pytest.fixture
async def test_config():
    """Create test configuration"""
    config_data = {
        "discord": {
            "token": "test_token",
            "guild_id": "123456789",
            "channel_id": "987654321"
        },
        "claude_code": {
            "command": "echo",  # Use echo instead of claude-code for testing
            "working_directory": "/tmp",
            "timeout": 30
        },
        "session": {
            "timeout": 300,
            "max_output_length": 1900,
            "max_history_length": 100,
            "cleanup_interval": 60
        },
        "logging": {
            "level": "DEBUG",
            "file": "test.log",
            "max_size": "10MB",
            "backup_count": 3
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    
    try:
        config = Config.load_from_file(temp_path)
        yield config
    finally:
        temp_path.unlink()


@pytest.fixture
async def session_manager(test_config):
    """Create test session manager"""
    manager = SessionManager(test_config)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
async def mock_discord_channel():
    """Create mock Discord channel"""
    mock_guild = Mock()
    mock_guild.id = 123456789
    mock_guild.me = Mock()
    mock_guild.me.name = "ClaudeBridge"
    
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.id = 987654321
    mock_channel.guild = mock_guild
    mock_channel.send = AsyncMock()
    
    return mock_channel


@pytest.fixture 
async def buffer_manager():
    """Create test buffer manager"""
    manager = BufferManager()
    yield manager
    await manager.stop_all_buffers()


class TestSystemIntegration:
    """Test system integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_session_lifecycle(self, session_manager):
        """Test complete session lifecycle"""
        # Create session
        session = await session_manager.create_session("/tmp")
        assert session is not None
        assert session.is_active()
        
        # Send command
        success = await session_manager.send_command(session.id, "test command")
        assert success
        assert len(session.command_history) > 0
        
        # Terminate session
        success = await session_manager.terminate_session(session.id)
        assert success
        assert not session.is_active()
    
    @pytest.mark.asyncio
    async def test_output_processing_pipeline(self, buffer_manager, mock_discord_channel):
        """Test the complete output processing pipeline"""
        from src.claude_bridge.output_handling.discord_formatter import MessageType
        
        # Create output buffer
        buffer = await buffer_manager.create_buffer("TEST001")
        
        # Set up callback to capture processed output
        processed_chunks = []
        
        async def capture_output(chunks):
            processed_chunks.extend(chunks)
        
        buffer.set_output_callback(capture_output)
        
        # Test different types of output
        test_outputs = [
            ("Starting process...", MessageType.INFO),
            ("\x1b[32mSuccess: File created\x1b[0m", MessageType.SUCCESS),
            ("\x1b[31mError: File not found\x1b[0m", MessageType.ERROR),
            ("████████░░ 80%", MessageType.PROGRESS),
            ("def hello():\n    print('Hello')", MessageType.CODE)
        ]
        
        for output, expected_type in test_outputs:
            buffer.add_output(output, expected_type)
        
        # Force flush
        await buffer.flush_buffer()
        
        # Verify processing
        assert len(processed_chunks) > 0
        
        # Check ANSI removal
        for chunk in processed_chunks:
            assert '\x1b[' not in chunk.content
        
        # Check message types are preserved
        message_types = [chunk.message_type for chunk in processed_chunks]
        assert MessageType.SUCCESS in message_types
        assert MessageType.ERROR in message_types
    
    @pytest.mark.asyncio
    async def test_discord_ui_conversion(self, mock_discord_channel):
        """Test Discord UI component conversion"""
        ui_converter = UIConverter()
        
        # Test yes/no prompt
        yes_no_prompt = "Do you want to continue? (y/n)"
        
        # Mock the interaction
        with patch.object(ui_converter, '_handle_yes_no', return_value="yes") as mock_yes_no:
            result = await ui_converter.handle_prompt(yes_no_prompt, mock_discord_channel, "TEST001")
            mock_yes_no.assert_called_once()
        
        # Test choice prompt
        choice_prompt = """Select an option:
        1. Option A
        2. Option B
        3. Option C"""
        
        with patch.object(ui_converter, '_handle_choice', return_value="1") as mock_choice:
            result = await ui_converter.handle_prompt(choice_prompt, mock_discord_channel, "TEST001")
            mock_choice.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_progress_display_integration(self, mock_discord_channel):
        """Test progress display system"""
        progress_manager = ProgressManager()
        
        # Test progress detection and display
        progress_outputs = [
            "Processing files... ████████░░ 80%",
            "Upload progress: 85%",
            "Step 3/5: Compiling sources",
            "████████████░░░░░░ 60%"
        ]
        
        for output in progress_outputs:
            handled = await progress_manager.handle_output("TEST001", output, mock_discord_channel)
            if handled:
                # Verify Discord message was sent
                assert mock_discord_channel.send.called
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, session_manager):
        """Test error handling across components"""
        error_handler = ErrorHandler()
        
        # Test error callback registration
        error_notifications = []
        
        def notify_error(error_info):
            error_notifications.append(error_info)
        
        from src.claude_bridge.utils.error_handler import RecoveryAction
        error_handler.register_recovery_callback(RecoveryAction.NOTIFY_USER, notify_error)
        
        # Simulate different types of errors
        test_errors = [
            (ConnectionError("Network timeout"), "network_error"),
            (PermissionError("Access denied"), "permission_error"),
            (FileNotFoundError("Config not found"), "config_error")
        ]
        
        for error, context in test_errors:
            success = await error_handler.handle_error(error, {"context": context})
            
            # Verify error was processed
            recent_errors = error_handler.get_recent_errors(1)
            assert len(recent_errors) > 0
            assert recent_errors[0].error == error
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_integration(self):
        """Test performance monitoring system"""
        monitor = PerformanceMonitor(collection_interval=0.1)
        
        # Start monitoring
        await monitor.start_monitoring()
        
        # Wait for a few metrics collections
        await asyncio.sleep(0.3)
        
        # Check metrics collection
        current_metrics = monitor.get_current_metrics()
        assert current_metrics is not None
        assert current_metrics.timestamp > 0
        
        # Test performance summary
        summary = monitor.get_performance_summary(minutes=1)
        assert 'averages' in summary
        assert 'peaks' in summary
        
        # Test health score
        health_score = monitor.get_health_score()
        assert 0 <= health_score <= 100
        
        # Stop monitoring
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_end_to_end_session_flow(self, session_manager, buffer_manager, mock_discord_channel):
        """Test complete end-to-end session flow"""
        
        # 1. Create session
        session = await session_manager.create_session("/tmp")
        assert session is not None
        
        # 2. Connect Discord channel
        success = await session_manager.connect_discord_channel(session.id, mock_discord_channel)
        assert success
        
        # 3. Create output buffer for session
        buffer = await buffer_manager.create_buffer(session.id)
        
        # 4. Set up output processing
        processed_messages = []
        
        async def process_output(chunks):
            processed_messages.extend(chunks)
        
        buffer.set_output_callback(process_output)
        
        # 5. Simulate Claude Code output
        test_outputs = [
            "Claude Code started successfully",
            "Working directory: /tmp",
            "\x1b[32mReady for commands\x1b[0m",
            "Processing request...",
            "████████████░░░░░░ 60%",
            "\x1b[32mTask completed successfully!\x1b[0m"
        ]
        
        for output in test_outputs:
            buffer.add_output(output)
        
        # 6. Force processing
        await buffer.flush_buffer()
        
        # 7. Send command to session
        success = await session_manager.send_command(session.id, "help")
        assert success
        
        # 8. Verify session state
        assert len(session.command_history) > 0
        assert session.command_history[-1] == "help"
        
        # 9. Verify output processing
        assert len(processed_messages) > 0
        
        # 10. Cleanup
        await session_manager.terminate_session(session.id)
        await buffer_manager.remove_buffer(session.id)


class TestMockClaudeCode:
    """Test with mock Claude Code process"""
    
    @pytest.mark.asyncio
    async def test_mock_claude_process_interaction(self, session_manager):
        """Test interaction with mock Claude Code process"""
        
        # Create session (using echo command as mock)
        session = await session_manager.create_session("/tmp")
        assert session is not None
        
        # The echo command should be running
        assert session.is_active()
        
        # Send commands and verify they're recorded
        commands = ["help", "status", "exit"]
        
        for cmd in commands:
            success = await session_manager.send_command(session.id, cmd)
            assert success
        
        # Verify command history
        assert len(session.command_history) == len(commands)
        assert session.command_history == commands
        
        # Terminate session
        await session_manager.terminate_session(session.id)


class TestComponentInteraction:
    """Test interaction between different components"""
    
    @pytest.mark.asyncio
    async def test_ansi_processor_with_discord_formatter(self):
        """Test ANSI processor working with Discord formatter"""
        from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
        from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter, MessageType
        
        ansi_processor = ANSIProcessor()
        discord_formatter = DiscordFormatter()
        
        # Test complex ANSI output
        complex_output = """
        \x1b[32mStarting build process...\x1b[0m
        \x1b[33mWarning: Deprecated function used\x1b[0m
        \x1b[31mError: Build failed at step 3\x1b[0m
        \x1b[32m✅ Tests passed (15/15)\x1b[0m
        """
        
        # Process through ANSI processor
        cleaned_output = ansi_processor.process_claude_output(complex_output)
        assert '\x1b[' not in cleaned_output
        
        # Format for Discord
        chunks = discord_formatter.format_output(cleaned_output, MessageType.CODE)
        assert len(chunks) > 0
        
        # Verify all chunks are within Discord limits
        for chunk in chunks:
            assert len(chunk.content) <= 2000
    
    @pytest.mark.asyncio 
    async def test_buffer_with_ui_converter(self, buffer_manager, mock_discord_channel):
        """Test output buffer working with UI converter"""
        from src.claude_bridge.discord_bot.ui_components import UIConverter
        
        buffer = await buffer_manager.create_buffer("TEST001")
        ui_converter = UIConverter()
        
        # Add interactive prompt to buffer
        interactive_output = "Do you want to save changes? (y/n)"
        buffer.add_output(interactive_output)
        
        # Process through UI converter
        with patch.object(ui_converter, '_handle_yes_no', return_value="yes"):
            result = await ui_converter.handle_prompt(
                interactive_output, mock_discord_channel, "TEST001"
            )
            # UI converter should handle interactive prompts
            # Buffer should handle non-interactive output
        
        # Cleanup
        await buffer_manager.remove_buffer("TEST001")


# Test fixtures for running integration tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for session-scoped async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])