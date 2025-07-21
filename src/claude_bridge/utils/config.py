"""
Configuration management for Claude Bridge

Handles loading and validation of configuration from JSON files and environment variables.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class DiscordConfig:
    """Discord bot configuration"""
    token: str
    guild_id: int
    channel_id: int


@dataclass
class ClaudeCodeConfig:
    """Claude Code process configuration"""
    command: str = "claude-code"
    working_directory: str = "/workspace"
    timeout: int = 120


@dataclass
class SessionConfig:
    """Session management configuration"""
    timeout: int = 3600
    max_output_length: int = 1900
    max_history_length: int = 100
    cleanup_interval: int = 300


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: str = "claude_bridge.log"
    max_size: str = "10MB"
    backup_count: int = 5


@dataclass
class Config:
    """Main configuration class"""
    discord: DiscordConfig
    claude_code: ClaudeCodeConfig
    session: SessionConfig
    logging: LoggingConfig
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'Config':
        """Load configuration from JSON file with environment variable override"""
        
        # Load environment variables from .env file if it exists
        env_file = config_path.parent / ".env"
        if env_file.exists():
            load_dotenv(env_file)
        
        # Load base configuration from JSON
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Override with environment variables if present
        discord_token = os.getenv('DISCORD_BOT_TOKEN', data['discord']['token'])
        if discord_token == "YOUR_DISCORD_BOT_TOKEN":
            raise ValueError(
                "Discord bot token not configured. Set DISCORD_BOT_TOKEN environment variable "
                "or update config.json"
            )
        
        discord_guild_id = int(os.getenv('DISCORD_GUILD_ID', data['discord']['guild_id']))
        discord_channel_id = int(os.getenv('DISCORD_CHANNEL_ID', data['discord']['channel_id']))
        
        # Create configuration objects
        discord_config = DiscordConfig(
            token=discord_token,
            guild_id=discord_guild_id,
            channel_id=discord_channel_id
        )
        
        claude_code_config = ClaudeCodeConfig(
            command=os.getenv('CLAUDE_CODE_COMMAND', data['claude_code']['command']),
            working_directory=os.getenv('CLAUDE_CODE_WORKDIR', data['claude_code']['working_directory']),
            timeout=int(os.getenv('CLAUDE_CODE_TIMEOUT', data['claude_code']['timeout']))
        )
        
        session_config = SessionConfig(
            timeout=int(os.getenv('SESSION_TIMEOUT', data['session']['timeout'])),
            max_output_length=int(os.getenv('SESSION_MAX_OUTPUT', data['session']['max_output_length'])),
            max_history_length=int(os.getenv('SESSION_MAX_HISTORY', data['session']['max_history_length'])),
            cleanup_interval=int(os.getenv('SESSION_CLEANUP_INTERVAL', data['session']['cleanup_interval']))
        )
        
        logging_config = LoggingConfig(
            level=os.getenv('LOG_LEVEL', data['logging']['level']),
            file=os.getenv('LOG_FILE', data['logging']['file']),
            max_size=os.getenv('LOG_MAX_SIZE', data['logging']['max_size']),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', data['logging']['backup_count']))
        )
        
        return cls(
            discord=discord_config,
            claude_code=claude_code_config,
            session=session_config,
            logging=logging_config
        )
    
    def validate(self) -> bool:
        """Validate configuration values"""
        errors = []
        
        # Discord validation
        if not self.discord.token or self.discord.token == "YOUR_DISCORD_BOT_TOKEN":
            errors.append("Discord bot token is required")
        
        if self.discord.guild_id <= 0:
            errors.append("Discord guild ID must be a positive integer")
            
        if self.discord.channel_id <= 0:
            errors.append("Discord channel ID must be a positive integer")
        
        # Claude Code validation
        if not self.claude_code.command:
            errors.append("Claude Code command is required")
        
        if self.claude_code.timeout <= 0:
            errors.append("Claude Code timeout must be positive")
        
        # Session validation
        if self.session.timeout <= 0:
            errors.append("Session timeout must be positive")
            
        if self.session.max_output_length <= 0:
            errors.append("Session max output length must be positive")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        return True