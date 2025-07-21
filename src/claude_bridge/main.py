#!/usr/bin/env python3
"""
Claude Bridge - Main Entry Point

Multi-Interface Session Bridge for Claude Code
Enables simultaneous operation from PC Terminal and Discord app.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from claude_bridge.core.session_manager import SessionManager
from claude_bridge.discord_bot.bot import ClaudeBridgeBot
from claude_bridge.utils.config import Config
from claude_bridge.utils.error_handler import ErrorHandler
from claude_bridge.utils.performance_monitor import PerformanceMonitor


def setup_logging(config: Config) -> None:
    """Setup logging configuration"""
    log_dir = Path(config.logging.file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.logging.file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file"""
    if config_path is None:
        config_path = "config/discord_config.json"
    
    config_file = Path(config_path)
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("📖 Please follow DISCORD_SETUP.md to create the configuration file.")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        return Config.from_dict(config_data)
    
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("📖 Please check your configuration file format.")
        sys.exit(1)


async def startup_checks(config: Config) -> bool:
    """Perform startup checks"""
    logger = logging.getLogger(__name__)
    
    print("🔍 Performing startup checks...")
    
    # Check Discord token
    if not config.discord.token or config.discord.token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Discord bot token not configured")
        print("📖 Please set your Discord bot token in the configuration file")
        return False
    
    # Check Guild and Channel IDs
    if config.discord.guild_id == 123 or config.discord.channel_id == 456:
        print("❌ Discord guild_id or channel_id not configured")
        print("📖 Please set your Discord server and channel IDs")
        return False
    
    # Check Claude Code command
    import shutil
    if not shutil.which(config.claude_code.command):
        print(f"⚠️ Claude Code command '{config.claude_code.command}' not found in PATH")
        print("🔧 Installing Claude Code CLI...")
        
        import subprocess
        try:
            subprocess.run([
                "npm", "install", "-g", "@anthropic-ai/claude-code@latest"
            ], check=True, capture_output=True)
            print("✅ Claude Code CLI installed successfully")
        except subprocess.CalledProcessError:
            print("❌ Failed to install Claude Code CLI")
            print("🔧 Please install manually: npm install -g @anthropic-ai/claude-code@latest")
            return False
    
    # Check working directory
    work_dir = Path(config.claude_code.working_directory)
    if not work_dir.exists():
        print(f"🔧 Creating working directory: {work_dir}")
        work_dir.mkdir(parents=True, exist_ok=True)
    
    # Test Claude Code
    print("🧪 Testing Claude Code connectivity...")
    try:
        import subprocess
        result = subprocess.run([
            config.claude_code.command, "--version"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Claude Code is working")
        else:
            print("⚠️ Claude Code version check failed, but proceeding...")
            
    except Exception as e:
        print(f"⚠️ Claude Code test failed: {e}")
        print("🔧 Make sure Claude Code is properly authenticated")
    
    print("✅ Startup checks completed")
    return True


class ClaudeBridgeApp:
    """Main Claude Bridge Application"""
    
    def __init__(self, config: Config):
        self.config = config
        self.session_manager: Optional[SessionManager] = None
        self.discord_bot: Optional[ClaudeBridgeBot] = None
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.error_handler = ErrorHandler()
        self.logger = logging.getLogger(__name__)
        self.running = False
    
    async def start(self) -> None:
        """Start Claude Bridge application"""
        self.logger.info("🚀 Starting Claude Bridge...")
        
        try:
            # Initialize performance monitoring
            self.performance_monitor = PerformanceMonitor()
            await self.performance_monitor.start()
            
            # Initialize session manager
            self.logger.info("📋 Initializing session manager...")
            self.session_manager = SessionManager(self.config)
            await self.session_manager.start()
            
            # Initialize Discord bot
            self.logger.info("🤖 Initializing Discord bot...")
            self.discord_bot = ClaudeBridgeBot(
                config=self.config,
                session_manager=self.session_manager
            )
            
            # Start Discord bot (this will block)
            self.running = True
            self.logger.info("✅ Claude Bridge started successfully")
            print("🎉 Claude Bridge is now running!")
            print(f"🔗 Connected to Discord server: {self.config.discord.guild_id}")
            print(f"📢 Active channel: {self.config.discord.channel_id}")
            print("📱 Use Discord slash commands to interact with Claude Code")
            print("🛑 Press Ctrl+C to stop")
            
            await self.discord_bot.start(self.config.discord.token)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Claude Bridge: {e}")
            await self.error_handler.handle_startup_error(e)
            raise
    
    async def stop(self) -> None:
        """Stop Claude Bridge application"""
        if not self.running:
            return
        
        self.logger.info("🛑 Stopping Claude Bridge...")
        self.running = False
        
        try:
            # Stop Discord bot
            if self.discord_bot:
                self.logger.info("🤖 Stopping Discord bot...")
                await self.discord_bot.close()
            
            # Stop session manager
            if self.session_manager:
                self.logger.info("📋 Stopping session manager...")
                await self.session_manager.stop()
            
            # Stop performance monitor
            if self.performance_monitor:
                await self.performance_monitor.stop()
            
            self.logger.info("✅ Claude Bridge stopped successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
            raise


async def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Claude Bridge - Multi-Interface Session Bridge for Claude Code"
    )
    parser.add_argument(
        "--config", "-c",
        help="Configuration file path (default: config/discord_config.json)",
        default=None
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run system tests instead of starting the application"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Claude Bridge 0.1.0"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except SystemExit:
        return
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    if args.test:
        # Run system tests
        print("🧪 Running system tests...")
        import subprocess
        try:
            result = subprocess.run([
                sys.executable, "comprehensive_test.py"
            ], cwd=Path(__file__).parent.parent.parent)
            sys.exit(result.returncode)
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            sys.exit(1)
    
    # Perform startup checks
    if not await startup_checks(config):
        sys.exit(1)
    
    # Create and start application
    app = ClaudeBridgeApp(config)
    
    try:
        await app.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received interrupt signal")
        print("\n🛑 Shutting down Claude Bridge...")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await app.stop()
        print("👋 Claude Bridge stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)