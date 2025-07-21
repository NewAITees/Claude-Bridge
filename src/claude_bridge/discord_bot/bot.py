"""
Discord Bot for Claude Bridge

Main Discord bot implementation with command handlers for session management.
"""

import asyncio
import discord
from discord.ext import commands
from typing import Optional

from ..core.session_manager import SessionManager
from ..output_handling.output_handler import OutputHandler
from ..utils.config import Config
from ..utils.logging_setup import get_logger

logger = get_logger('discord_bot')


class ClaudeBridgeBot(commands.Bot):
    """Discord bot for Claude Bridge session management"""
    
    def __init__(self, session_manager: SessionManager, config: Config):
        # Initialize Discord bot with command prefix
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='/',
            intents=intents,
            help_command=None
        )
        
        self.session_manager = session_manager
        self.config = config
        self.output_handler = OutputHandler()
        
        # Track user sessions (user_id -> session_id)
        self.user_sessions: dict[int, str] = {}
        
        # Set up session manager callbacks
        self.session_manager.set_output_callback(self._handle_session_output)
        
        # Add commands
        self.add_commands()
    
    def add_commands(self):
        """Add all Discord commands"""
        
        @self.command(name='connect')
        async def connect_command(ctx: commands.Context, session_id: str):
            """Connect to a Claude Code session"""
            await self._connect_session(ctx, session_id)
        
        @self.command(name='disconnect')
        async def disconnect_command(ctx: commands.Context):
            """Disconnect from current session"""
            await self._disconnect_session(ctx)
        
        @self.command(name='status')
        async def status_command(ctx: commands.Context):
            """Show current session status"""
            await self._show_status(ctx)
        
        @self.command(name='output')
        async def output_command(ctx: commands.Context, count: int = 10):
            """Get recent output from current session"""
            await self._show_output(ctx, count)
        
        @self.command(name='history')
        async def history_command(ctx: commands.Context, count: int = 10):
            """Show command history from current session"""
            await self._show_history(ctx, count)
        
        @self.command(name='sessions')
        async def sessions_command(ctx: commands.Context):
            """List all active sessions"""
            await self._list_sessions(ctx)
        
        @self.command(name='help')
        async def help_command(ctx: commands.Context):
            """Show help information"""
            await self._show_help(ctx)
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Claude Code sessions"
        )
        await self.change_presence(activity=activity)
    
    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Check if this is a command
        if message.content.startswith('/'):
            await self.process_commands(message)
            return
        
        # Check if user is in a session and this is a direct command
        user_id = message.author.id
        if user_id in self.user_sessions:
            session_id = self.user_sessions[user_id]
            
            # Send message as command to Claude Code
            success = await self.session_manager.send_command(session_id, message.content)
            if not success:
                await message.channel.send("⚠️ Failed to send command to Claude Code session")
    
    async def _connect_session(self, ctx: commands.Context, session_id: str):
        """Handle session connection"""
        user_id = ctx.author.id
        
        # Check if user is already connected
        if user_id in self.user_sessions:
            current_session = self.user_sessions[user_id]
            if current_session == session_id:
                await ctx.send(f"You are already connected to session `{session_id}`")
                return
            else:
                await ctx.send(f"You are already connected to session `{current_session}`. Disconnect first or use a different session ID.")
                return
        
        # Check if session exists
        session = self.session_manager.get_session(session_id)
        if not session:
            await ctx.send(f"❌ Session `{session_id}` not found")
            return
        
        # Check if session is active
        if not session.is_active():
            await ctx.send(f"❌ Session `{session_id}` is not active")
            return
        
        # Connect Discord channel to session
        success = await self.session_manager.connect_discord_channel(session_id, ctx.channel)
        if not success:
            await ctx.send(f"❌ Failed to connect to session `{session_id}`")
            return
        
        # Track user session
        self.user_sessions[user_id] = session_id
        
        # Send success message
        embed = discord.Embed(
            title="✅ Session Connected",
            description=f"Connected to Claude Code session `{session_id}`",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Status", 
            value=session.status.title(), 
            inline=True
        )
        embed.add_field(
            name="Created", 
            value=session.created_at.strftime("%Y-%m-%d %H:%M:%S"), 
            inline=True
        )
        embed.add_field(
            name="Commands", 
            value=len(session.command_history), 
            inline=True
        )
        
        await ctx.send(embed=embed)
        
        # Show recent output if available
        recent_output = session.get_recent_output(3)
        if recent_output:
            output_text = '\n'.join(recent_output)
            formatted_output = self.output_handler.format_for_discord(output_text)
            await ctx.send(f"**Recent Output:**\n```\n{formatted_output}\n```")
    
    async def _disconnect_session(self, ctx: commands.Context):
        """Handle session disconnection"""
        user_id = ctx.author.id
        
        if user_id not in self.user_sessions:
            await ctx.send("❌ You are not connected to any session")
            return
        
        session_id = self.user_sessions[user_id]
        
        # Disconnect from session
        await self.session_manager.disconnect_discord_channel(session_id)
        
        # Remove user session tracking
        del self.user_sessions[user_id]
        
        embed = discord.Embed(
            title="✅ Session Disconnected",
            description=f"Disconnected from session `{session_id}`",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed)
    
    async def _show_status(self, ctx: commands.Context):
        """Show current session status"""
        user_id = ctx.author.id
        
        if user_id not in self.user_sessions:
            await ctx.send("❌ You are not connected to any session")
            return
        
        session_id = self.user_sessions[user_id]
        session = self.session_manager.get_session(session_id)
        
        if not session:
            await ctx.send(f"❌ Session `{session_id}` not found")
            # Remove invalid session
            del self.user_sessions[user_id]
            return
        
        # Create status embed
        embed = discord.Embed(
            title=f"📊 Session Status: `{session_id}`",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Status", value=session.status.title(), inline=True)
        embed.add_field(name="Active", value="✅" if session.is_active() else "❌", inline=True)
        embed.add_field(name="Commands", value=len(session.command_history), inline=True)
        embed.add_field(name="Output Lines", value=len(session.output_buffer), inline=True)
        embed.add_field(
            name="Created", 
            value=session.created_at.strftime("%Y-%m-%d %H:%M:%S"), 
            inline=True
        )
        embed.add_field(
            name="Last Activity", 
            value=session.last_activity.strftime("%Y-%m-%d %H:%M:%S"), 
            inline=True
        )
        embed.add_field(
            name="Working Directory", 
            value=session.working_directory or "Not set", 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    async def _show_output(self, ctx: commands.Context, count: int = 10):
        """Show recent output"""
        user_id = ctx.author.id
        
        if user_id not in self.user_sessions:
            await ctx.send("❌ You are not connected to any session")
            return
        
        session_id = self.user_sessions[user_id]
        session = self.session_manager.get_session(session_id)
        
        if not session:
            await ctx.send(f"❌ Session `{session_id}` not found")
            del self.user_sessions[user_id]
            return
        
        # Get recent output
        recent_output = session.get_recent_output(min(count, 20))  # Max 20 lines
        
        if not recent_output:
            await ctx.send("No output available")
            return
        
        # Format output for Discord
        output_text = '\n'.join(recent_output)
        formatted_output = self.output_handler.format_for_discord(output_text)
        
        # Split if too long
        chunks = self.output_handler.split_long_output(formatted_output, 1900)
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                await ctx.send(f"**Recent Output (last {len(recent_output)} lines):**\n```\n{chunk}\n```")
            else:
                await ctx.send(f"```\n{chunk}\n```")
    
    async def _show_history(self, ctx: commands.Context, count: int = 10):
        """Show command history"""
        user_id = ctx.author.id
        
        if user_id not in self.user_sessions:
            await ctx.send("❌ You are not connected to any session")
            return
        
        session_id = self.user_sessions[user_id]
        session = self.session_manager.get_session(session_id)
        
        if not session:
            await ctx.send(f"❌ Session `{session_id}` not found")
            del self.user_sessions[user_id]
            return
        
        # Get recent commands
        recent_commands = session.get_recent_commands(min(count, 20))  # Max 20 commands
        
        if not recent_commands:
            await ctx.send("No command history available")
            return
        
        # Format commands
        history_text = '\n'.join([f"{i+1}. {cmd}" for i, cmd in enumerate(recent_commands)])
        formatted_history = self.output_handler.format_for_discord(history_text)
        
        await ctx.send(f"**Command History (last {len(recent_commands)} commands):**\n```\n{formatted_history}\n```")
    
    async def _list_sessions(self, ctx: commands.Context):
        """List all active sessions"""
        stats = self.session_manager.get_session_stats()
        
        if stats['total_sessions'] == 0:
            await ctx.send("No active sessions")
            return
        
        # Create sessions embed
        embed = discord.Embed(
            title="📋 Active Sessions",
            color=discord.Color.purple()
        )
        
        embed.add_field(name="Total Sessions", value=stats['total_sessions'], inline=True)
        embed.add_field(name="Active Sessions", value=stats['active_sessions'], inline=True)
        embed.add_field(name="Inactive Sessions", value=stats['inactive_sessions'], inline=True)
        
        # List session IDs
        if stats['session_ids']:
            session_list = ', '.join([f"`{sid}`" for sid in stats['session_ids'][:10]])  # Max 10
            if len(stats['session_ids']) > 10:
                session_list += f" and {len(stats['session_ids']) - 10} more..."
            embed.add_field(name="Session IDs", value=session_list, inline=False)
        
        await ctx.send(embed=embed)
    
    async def _show_help(self, ctx: commands.Context):
        """Show help information"""
        embed = discord.Embed(
            title="🤖 Claude Bridge Help",
            description="Multi-Interface Session Bridge for Claude Code",
            color=discord.Color.gold()
        )
        
        commands_text = """
        `/connect <session_id>` - Connect to a Claude Code session
        `/disconnect` - Disconnect from current session
        `/status` - Show current session status
        `/output [count]` - Get recent output (default: 10 lines)
        `/history [count]` - Show command history (default: 10 commands)
        `/sessions` - List all active sessions
        `/help` - Show this help message
        """
        
        embed.add_field(name="Commands", value=commands_text, inline=False)
        
        usage_text = """
        1. Connect to a session using `/connect <session_id>`
        2. Send messages directly to interact with Claude Code
        3. Use `/output` to see recent responses
        4. Use `/disconnect` when done
        """
        
        embed.add_field(name="Usage", value=usage_text, inline=False)
        
        await ctx.send(embed=embed)
    
    async def _handle_session_output(self, session_id: str, output: str):
        """Handle output from session manager"""
        # Find users connected to this session
        connected_users = [
            user_id for user_id, sid in self.user_sessions.items() 
            if sid == session_id
        ]
        
        if not connected_users:
            return
        
        # Get session to find Discord channel
        session = self.session_manager.get_session(session_id)
        if not session or not session.discord_channel:
            return
        
        # Format output for Discord
        formatted_output = self.output_handler.format_for_discord(output)
        
        # Send to Discord channel
        try:
            if formatted_output.strip():
                await session.discord_channel.send(f"```\n{formatted_output}\n```")
        except discord.errors.HTTPException as e:
            logger.error(f"Failed to send output to Discord: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending output to Discord: {e}")
    
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❌ Unknown command. Use `/help` for available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: `{error.param.name}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        else:
            logger.error(f"Unhandled command error: {error}")
            await ctx.send("❌ An error occurred while processing the command.")