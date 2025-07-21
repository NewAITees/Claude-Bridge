#!/usr/bin/env python3
"""
Claude Bridge - Main Entry Point

Starts the Claude Bridge application with session management,
Discord bot, and Claude Code process control.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from .core.session_manager import SessionManager
from .discord_bot.bot import ClaudeBridgeBot
from .utils.config import Config
from .utils.logging_setup import setup_logging


async def main(config_path: Optional[str] = None) -> int:
    """Main application entry point"""
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Claude Bridge...")
    
    try:
        # Load configuration
        if config_path is None:
            config_path = Path("config") / "config.json"
        
        config = Config.load_from_file(Path(config_path))
        logger.info(f"Configuration loaded from {config_path}")
        
        # Initialize session manager
        session_manager = SessionManager(config)
        logger.info("Session manager initialized")
        
        # Initialize Discord bot
        bot = ClaudeBridgeBot(session_manager, config)
        logger.info("Discord bot initialized")
        
        # Start the bot
        logger.info("Starting Discord bot...")
        await bot.start(config.discord_token)
        
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    
    return 0


def cli_main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Claude Bridge - Multi-Interface Session Bridge")
    parser.add_argument(
        "--config", 
        type=str,
        default=None,
        help="Path to configuration file (default: config/config.json)"
    )
    
    args = parser.parse_args()
    
    try:
        exit_code = asyncio.run(main(args.config))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nClaude Bridge stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()