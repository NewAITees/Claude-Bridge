"""
Discord Bot Integration Tests

Tests Discord bot functionality with mock Discord components.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import discord
from discord.ext import commands

from src.claude_bridge.discord_bot.bot import ClaudeBridgeBot
from src.claude_bridge.core.session_manager import SessionManager
from src.claude_bridge.utils.config import Config, DiscordConfig, ClaudeCodeConfig, SessionConfig, LoggingConfig
from src.claude_bridge.discord_bot.ui_components import UIConverter
from src.claude_bridge.discord_bot.progress_display import ProgressManager


@pytest.fixture
def mock_config():
    """Create mock configuration for testing"""
    return Config(
        discord=DiscordConfig("test_token", 123456789, 987654321),
        claude_code=ClaudeCodeConfig("echo", "/tmp", 30),
        session=SessionConfig(300, 1900, 100, 60),
        logging=LoggingConfig("DEBUG", "test.log", "10MB", 3)
    )


@pytest.fixture
async def session_manager(mock_config):
    """Create test session manager"""
    manager = SessionManager(mock_config)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def mock_discord_context():
    """Create mock Discord context"""
    mock_guild = Mock()
    mock_guild.id = 123456789
    mock_guild.me = Mock()
    mock_guild.me.name = "ClaudeBridge"
    
    mock_channel = AsyncMock(spec=discord.TextChannel)
    mock_channel.id = 987654321
    mock_channel.guild = mock_guild
    mock_channel.send = AsyncMock()
    
    mock_author = Mock()
    mock_author.id = 555666777
    mock_author.mention = "<@555666777>"
    
    mock_message = Mock()
    mock_message.author = mock_author
    mock_message.channel = mock_channel
    mock_message.guild = mock_guild
    mock_message.content = ""
    
    mock_context = AsyncMock(spec=commands.Context)
    mock_context.author = mock_author
    mock_context.channel = mock_channel
    mock_context.guild = mock_guild
    mock_context.message = mock_message
    mock_context.send = AsyncMock()
    
    return mock_context


@pytest.fixture
def mock_bot(session_manager, mock_config):
    """Create mock Discord bot"""
    with patch('discord.ext.commands.Bot.__init__'), \
         patch('discord.ext.commands.Bot.add_command'), \
         patch('discord.ext.commands.Bot.command'), \
         patch('discord.Client.login'), \
         patch('discord.Client.connect'):
        
        bot = ClaudeBridgeBot(session_manager, mock_config)
        bot.user = Mock()
        bot.user.id = 999888777
        bot.guilds = []
        
        return bot


class TestDiscordBotIntegration:
    """Test Discord bot integration with various components"""
    
    @pytest.mark.asyncio
    async def test_bot_initialization(self, mock_bot):
        """Test bot initialization with components"""
        assert mock_bot.session_manager is not None
        assert mock_bot.config is not None
        assert mock_bot.output_handler is not None
        assert isinstance(mock_bot.user_sessions, dict)
    
    @pytest.mark.asyncio
    async def test_connect_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /connect command functionality"""
        # Create a test session first
        session = await session_manager.create_session("/tmp")
        session_id = session.id
        
        # Mock the context
        mock_discord_context.send = AsyncMock()
        
        # Test connect command
        await mock_bot._connect_session(mock_discord_context, session_id)
        
        # Verify connection was made
        assert mock_discord_context.author.id in mock_bot.user_sessions
        assert mock_bot.user_sessions[mock_discord_context.author.id] == session_id
        
        # Verify Discord response was sent
        mock_discord_context.send.assert_called()
        
        # Check that embed was created
        call_args = mock_discord_context.send.call_args
        assert 'embed' in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_disconnect_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /disconnect command functionality"""
        # Set up connected session
        session = await session_manager.create_session("/tmp")
        mock_bot.user_sessions[mock_discord_context.author.id] = session.id
        
        # Test disconnect command
        await mock_bot._disconnect_session(mock_discord_context)
        
        # Verify disconnection
        assert mock_discord_context.author.id not in mock_bot.user_sessions
        
        # Verify response was sent
        mock_discord_context.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_status_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /status command functionality"""
        # Create and connect to session
        session = await session_manager.create_session("/tmp")
        mock_bot.user_sessions[mock_discord_context.author.id] = session.id
        
        # Test status command
        await mock_bot._show_status(mock_discord_context)
        
        # Verify status response was sent
        mock_discord_context.send.assert_called()
        
        # Check embed content
        call_args = mock_discord_context.send.call_args
        embed = call_args.kwargs['embed']
        assert embed.title.startswith('📊 Session Status:')
    
    @pytest.mark.asyncio
    async def test_output_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /output command functionality"""
        # Create session with output
        session = await session_manager.create_session("/tmp")
        session.add_output("Test output line 1")
        session.add_output("Test output line 2")
        session.add_output("Test output line 3")
        
        mock_bot.user_sessions[mock_discord_context.author.id] = session.id
        
        # Test output command
        await mock_bot._show_output(mock_discord_context, 10)
        
        # Verify output was sent
        mock_discord_context.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_history_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /history command functionality"""
        # Create session with command history
        session = await session_manager.create_session("/tmp")
        session.add_command("help")
        session.add_command("status")
        session.add_command("list files")
        
        mock_bot.user_sessions[mock_discord_context.author.id] = session.id
        
        # Test history command
        await mock_bot._show_history(mock_discord_context, 10)
        
        # Verify history was sent
        mock_discord_context.send.assert_called()
    
    @pytest.mark.asyncio
    async def test_sessions_command(self, mock_bot, mock_discord_context, session_manager):
        """Test /sessions command functionality"""
        # Create multiple sessions
        session1 = await session_manager.create_session("/tmp")
        session2 = await session_manager.create_session("/home")
        
        # Test sessions command
        await mock_bot._list_sessions(mock_discord_context)
        
        # Verify sessions list was sent
        mock_discord_context.send.assert_called()
        
        # Check embed shows session count
        call_args = mock_discord_context.send.call_args
        embed = call_args.kwargs['embed']
        assert 'Active Sessions' in embed.title
    
    @pytest.mark.asyncio
    async def test_help_command(self, mock_bot, mock_discord_context):
        """Test /help command functionality"""
        # Test help command
        await mock_bot._show_help(mock_discord_context)
        
        # Verify help was sent
        mock_discord_context.send.assert_called()
        
        # Check help content
        call_args = mock_discord_context.send.call_args
        embed = call_args.kwargs['embed']
        assert 'Claude Bridge Help' in embed.title
    
    @pytest.mark.asyncio
    async def test_message_handling(self, mock_bot, session_manager):
        """Test non-command message handling"""
        # Create session and connect user
        session = await session_manager.create_session("/tmp")
        user_id = 555666777
        mock_bot.user_sessions[user_id] = session.id
        
        # Create mock message
        mock_message = Mock()
        mock_message.author = Mock()
        mock_message.author.id = user_id
        mock_message.content = "test command"
        mock_message.channel = Mock()
        
        # Mock session manager send_command
        with patch.object(session_manager, 'send_command', return_value=True) as mock_send:
            await mock_bot.on_message(mock_message)
            
            # Verify command was sent to session
            mock_send.assert_called_with(session.id, "test command")
    
    @pytest.mark.asyncio
    async def test_session_output_callback(self, mock_bot, mock_discord_context, session_manager):
        """Test session output callback handling"""
        # Create session with Discord channel
        session = await session_manager.create_session("/tmp")
        session.discord_channel = mock_discord_context.channel
        
        # Test output callback
        test_output = "Test output from Claude Code"
        await mock_bot._handle_session_output(session.id, test_output)
        
        # Verify output was sent to Discord
        mock_discord_context.channel.send.assert_called()


class TestUIComponentsIntegration:
    """Test UI components integration"""
    
    @pytest.mark.asyncio
    async def test_ui_converter_with_discord(self, mock_discord_context):
        """Test UI converter with Discord interactions"""
        ui_converter = UIConverter()
        
        # Mock Discord interactions
        mock_view = Mock()
        mock_view.responded = asyncio.Event()
        mock_view.result = True
        
        with patch('src.claude_bridge.discord_bot.ui_components.ConfirmationView', return_value=mock_view):
            with patch.object(asyncio, 'wait_for') as mock_wait:
                # Set the event to simulate user response
                mock_view.responded.set()
                mock_wait.return_value = None
                
                result = await ui_converter._handle_yes_no(
                    {'prompt': 'Test confirmation'}, 
                    mock_discord_context.channel, 
                    "TEST001"
                )
                
                assert result == "yes"
    
    @pytest.mark.asyncio
    async def test_progress_manager_with_discord(self, mock_discord_context):
        """Test progress manager with Discord"""
        progress_manager = ProgressManager()
        
        # Test progress detection
        progress_text = "Processing files... ████████░░ 80%"
        
        with patch.object(mock_discord_context.channel, 'send') as mock_send:
            handled = await progress_manager.handle_output(
                "TEST001", 
                progress_text, 
                mock_discord_context.channel
            )
            
            if handled:
                # Verify progress embed was sent
                assert mock_send.called


class TestErrorHandling:
    """Test error handling in Discord context"""
    
    @pytest.mark.asyncio
    async def test_command_error_handling(self, mock_bot, mock_discord_context):
        """Test command error handling"""
        # Test unknown command
        error = commands.CommandNotFound()
        await mock_bot.on_command_error(mock_discord_context, error)
        
        # Verify error message was sent
        mock_discord_context.send.assert_called()
        
        # Check error message content
        call_args = mock_discord_context.send.call_args
        assert "Unknown command" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_missing_argument_error(self, mock_bot, mock_discord_context):
        """Test missing argument error handling"""
        # Create mock parameter
        mock_param = Mock()
        mock_param.name = "session_id"
        
        error = commands.MissingRequiredArgument(mock_param)
        await mock_bot.on_command_error(mock_discord_context, error)
        
        # Verify error response
        mock_discord_context.send.assert_called()
        call_args = mock_discord_context.send.call_args
        assert "Missing required argument" in call_args[0][0]


class TestEndToEndDiscordFlow:
    """Test complete Discord interaction flows"""
    
    @pytest.mark.asyncio
    async def test_complete_session_flow(self, mock_bot, mock_discord_context, session_manager):
        """Test complete session interaction flow"""
        
        # 1. Create session
        session = await session_manager.create_session("/tmp")
        
        # 2. Connect via Discord
        await mock_bot._connect_session(mock_discord_context, session.id)
        assert mock_discord_context.author.id in mock_bot.user_sessions
        
        # 3. Send some commands through session
        await session_manager.send_command(session.id, "help")
        await session_manager.send_command(session.id, "status")
        
        # 4. Check status via Discord
        await mock_bot._show_status(mock_discord_context)
        
        # 5. Get command history
        await mock_bot._show_history(mock_discord_context)
        
        # 6. Get output
        session.add_output("Test output")
        await mock_bot._show_output(mock_discord_context)
        
        # 7. Disconnect
        await mock_bot._disconnect_session(mock_discord_context)
        assert mock_discord_context.author.id not in mock_bot.user_sessions
        
        # Verify all Discord interactions occurred
        assert mock_discord_context.send.call_count >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])