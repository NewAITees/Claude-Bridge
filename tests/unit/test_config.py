"""
Unit tests for Config
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from src.claude_bridge.utils.config import Config, DiscordConfig, ClaudeCodeConfig, SessionConfig, LoggingConfig


class TestConfig:
    """Test cases for configuration management"""
    
    def test_config_dataclasses(self):
        """Test configuration dataclass creation"""
        # Test DiscordConfig
        discord_config = DiscordConfig(
            token="test_token",
            guild_id=123456789,
            channel_id=987654321
        )
        assert discord_config.token == "test_token"
        assert discord_config.guild_id == 123456789
        assert discord_config.channel_id == 987654321
        
        # Test ClaudeCodeConfig with defaults
        claude_config = ClaudeCodeConfig()
        assert claude_config.command == "claude-code"
        assert claude_config.working_directory == "/workspace"
        assert claude_config.timeout == 120
        
        # Test SessionConfig with defaults
        session_config = SessionConfig()
        assert session_config.timeout == 3600
        assert session_config.max_output_length == 1900
        assert session_config.max_history_length == 100
        assert session_config.cleanup_interval == 300
        
        # Test LoggingConfig with defaults
        logging_config = LoggingConfig()
        assert logging_config.level == "INFO"
        assert logging_config.file == "claude_bridge.log"
        assert logging_config.max_size == "10MB"
        assert logging_config.backup_count == 5
    
    def test_load_from_file_basic(self):
        """Test basic configuration file loading"""
        # Create temporary config file
        config_data = {
            "discord": {
                "token": "test_discord_token",
                "guild_id": "123456789",
                "channel_id": "987654321"
            },
            "claude_code": {
                "command": "claude-code",
                "working_directory": "/test/workspace",
                "timeout": 60
            },
            "session": {
                "timeout": 7200,
                "max_output_length": 1800,
                "max_history_length": 50,
                "cleanup_interval": 600
            },
            "logging": {
                "level": "DEBUG",
                "file": "test.log",
                "max_size": "5MB",
                "backup_count": 3
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            config = Config.load_from_file(temp_path)
            
            # Test Discord config
            assert config.discord.token == "test_discord_token"
            assert config.discord.guild_id == 123456789
            assert config.discord.channel_id == 987654321
            
            # Test Claude Code config
            assert config.claude_code.command == "claude-code"
            assert config.claude_code.working_directory == "/test/workspace"
            assert config.claude_code.timeout == 60
            
            # Test Session config
            assert config.session.timeout == 7200
            assert config.session.max_output_length == 1800
            assert config.session.max_history_length == 50
            assert config.session.cleanup_interval == 600
            
            # Test Logging config
            assert config.logging.level == "DEBUG"
            assert config.logging.file == "test.log"
            assert config.logging.max_size == "5MB"
            assert config.logging.backup_count == 3
            
        finally:
            os.unlink(temp_path)
    
    def test_load_from_file_with_env_override(self):
        """Test configuration loading with environment variable override"""
        # Create basic config file
        config_data = {
            "discord": {
                "token": "config_token",
                "guild_id": "111",
                "channel_id": "222"
            },
            "claude_code": {
                "command": "claude-code",
                "working_directory": "/workspace",
                "timeout": 120
            },
            "session": {
                "timeout": 3600,
                "max_output_length": 1900,
                "max_history_length": 100,
                "cleanup_interval": 300
            },
            "logging": {
                "level": "INFO",
                "file": "claude_bridge.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        # Set environment variables
        env_vars = {
            'DISCORD_BOT_TOKEN': 'env_token',
            'DISCORD_GUILD_ID': '333',
            'DISCORD_CHANNEL_ID': '444',
            'CLAUDE_CODE_TIMEOUT': '90',
            'SESSION_TIMEOUT': '1800',
            'LOG_LEVEL': 'WARNING'
        }
        
        original_env = {}
        try:
            # Set environment variables
            for key, value in env_vars.items():
                original_env[key] = os.environ.get(key)
                os.environ[key] = value
            
            config = Config.load_from_file(temp_path)
            
            # Environment variables should override config file
            assert config.discord.token == "env_token"
            assert config.discord.guild_id == 333
            assert config.discord.channel_id == 444
            assert config.claude_code.timeout == 90
            assert config.session.timeout == 1800
            assert config.logging.level == "WARNING"
            
        finally:
            # Restore original environment
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            os.unlink(temp_path)
    
    def test_load_from_file_missing_token(self):
        """Test error handling for missing Discord token"""
        config_data = {
            "discord": {
                "token": "YOUR_DISCORD_BOT_TOKEN",  # Default placeholder
                "guild_id": "123456789",
                "channel_id": "987654321"
            },
            "claude_code": {
                "command": "claude-code",
                "working_directory": "/workspace",
                "timeout": 120
            },
            "session": {
                "timeout": 3600,
                "max_output_length": 1900,
                "max_history_length": 100,
                "cleanup_interval": 300
            },
            "logging": {
                "level": "INFO",
                "file": "claude_bridge.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ValueError, match="Discord bot token not configured"):
                Config.load_from_file(temp_path)
        finally:
            os.unlink(temp_path)
    
    def test_validate_config(self):
        """Test configuration validation"""
        # Create valid config
        config = Config(
            discord=DiscordConfig("valid_token", 123, 456),
            claude_code=ClaudeCodeConfig("claude-code", "/workspace", 120),
            session=SessionConfig(3600, 1900, 100, 300),
            logging=LoggingConfig("INFO", "test.log", "10MB", 5)
        )
        
        # Should validate successfully
        assert config.validate() == True
        
        # Test invalid Discord token
        config.discord.token = ""
        with pytest.raises(ValueError, match="Discord bot token is required"):
            config.validate()
        
        # Test invalid guild ID
        config.discord.token = "valid_token"
        config.discord.guild_id = 0
        with pytest.raises(ValueError, match="Discord guild ID must be a positive integer"):
            config.validate()
        
        # Test invalid channel ID
        config.discord.guild_id = 123
        config.discord.channel_id = -1
        with pytest.raises(ValueError, match="Discord channel ID must be a positive integer"):
            config.validate()
        
        # Test invalid Claude Code command
        config.discord.channel_id = 456
        config.claude_code.command = ""
        with pytest.raises(ValueError, match="Claude Code command is required"):
            config.validate()
        
        # Test invalid timeout
        config.claude_code.command = "claude-code"
        config.claude_code.timeout = 0
        with pytest.raises(ValueError, match="Claude Code timeout must be positive"):
            config.validate()
        
        # Test invalid session timeout
        config.claude_code.timeout = 120
        config.session.timeout = -1
        with pytest.raises(ValueError, match="Session timeout must be positive"):
            config.validate()
        
        # Test invalid max output length
        config.session.timeout = 3600
        config.session.max_output_length = 0
        with pytest.raises(ValueError, match="Session max output length must be positive"):
            config.validate()
    
    def test_file_not_found(self):
        """Test handling of missing configuration file"""
        non_existent_path = Path("/non/existent/config.json")
        
        with pytest.raises(FileNotFoundError):
            Config.load_from_file(non_existent_path)
    
    def test_invalid_json(self):
        """Test handling of invalid JSON in configuration file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(json.JSONDecodeError):
                Config.load_from_file(temp_path)
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__])