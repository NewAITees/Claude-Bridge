"""
Progress Display System for Discord

Manages progress indicators, long-running task updates, and live status displays.
"""

import asyncio
import time
import re
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import discord

from ..utils.logging_setup import get_logger

logger = get_logger('progress_display')


class ProgressType(Enum):
    """Types of progress displays"""
    BAR = "bar"                 # Progress bar
    SPINNER = "spinner"         # Spinning indicator
    COUNTER = "counter"         # Number counting
    PERCENTAGE = "percentage"   # Percentage display
    STATUS = "status"          # Status message
    STEPS = "steps"            # Step-by-step progress


@dataclass
class ProgressState:
    """Represents the state of a progress display"""
    session_id: str
    progress_type: ProgressType
    current_value: float = 0.0
    max_value: float = 100.0
    message: str = ""
    status: str = "running"  # running, complete, error, cancelled
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """Calculate percentage completion"""
        if self.max_value <= 0:
            return 0.0
        return min(100.0, (self.current_value / self.max_value) * 100.0)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since start"""
        return time.time() - self.start_time
    
    @property
    def is_complete(self) -> bool:
        """Check if progress is complete"""
        return self.status == "complete" or self.current_value >= self.max_value


class ProgressDetector:
    """Detects progress indicators in output text"""
    
    # Progress patterns
    PATTERNS = {
        ProgressType.BAR: [
            re.compile(r'[█▉▊▋▌▍▎▏░▒▓]{5,}'),  # Unicode progress bars
            re.compile(r'\[[=#\-\.\s]{5,}\]'),    # ASCII progress bars
            re.compile(r'\|[\/\-\\|]{3,}\|'),     # Spinner bars
        ],
        
        ProgressType.PERCENTAGE: [
            re.compile(r'\b(\d{1,3}(?:\.\d+)?)\s*%'),
            re.compile(r'(\d{1,3}(?:\.\d+)?)\s*percent', re.IGNORECASE),
            re.compile(r'Progress:\s*(\d{1,3}(?:\.\d+)?)'),
        ],
        
        ProgressType.COUNTER: [
            re.compile(r'(\d+)\s*/\s*(\d+)'),
            re.compile(r'(\d+)\s+of\s+(\d+)', re.IGNORECASE),
            re.compile(r'Processed\s+(\d+)\s*/\s*(\d+)', re.IGNORECASE),
        ],
        
        ProgressType.SPINNER: [
            re.compile(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]'),
            re.compile(r'[|\/\-\\]'),
        ],
        
        ProgressType.STATUS: [
            re.compile(r'(Loading|Processing|Downloading|Installing|Building|Compiling)[\.]{0,3}', re.IGNORECASE),
            re.compile(r'(Working on|Preparing|Initializing|Setting up)[\.]{0,3}', re.IGNORECASE),
            re.compile(r'Please wait[\.]{0,3}', re.IGNORECASE),
        ],
        
        ProgressType.STEPS: [
            re.compile(r'Step\s+(\d+)\s*/\s*(\d+)', re.IGNORECASE),
            re.compile(r'Phase\s+(\d+)\s*/\s*(\d+)', re.IGNORECASE),
            re.compile(r'Stage\s+(\d+)\s*/\s*(\d+)', re.IGNORECASE),
        ]
    }
    
    @classmethod
    def detect_progress(cls, text: str) -> Optional[Dict]:
        """Detect progress indicators in text"""
        if not text or not text.strip():
            return None
        
        for progress_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    return cls._extract_progress_info(text, match, progress_type)
        
        return None
    
    @classmethod
    def _extract_progress_info(cls, text: str, match: re.Match, 
                             progress_type: ProgressType) -> Dict:
        """Extract progress information from matched text"""
        info = {
            'type': progress_type,
            'raw_text': text,
            'matched_text': match.group(),
            'groups': match.groups()
        }
        
        if progress_type == ProgressType.PERCENTAGE:
            try:
                info['percentage'] = float(match.group(1))
            except (ValueError, IndexError):
                info['percentage'] = 0.0
                
        elif progress_type == ProgressType.COUNTER:
            try:
                info['current'] = int(match.group(1))
                info['total'] = int(match.group(2))
                info['percentage'] = (info['current'] / info['total']) * 100.0 if info['total'] > 0 else 0.0
            except (ValueError, IndexError):
                info['current'] = 0
                info['total'] = 100
                info['percentage'] = 0.0
                
        elif progress_type == ProgressType.STEPS:
            try:
                info['current_step'] = int(match.group(1))
                info['total_steps'] = int(match.group(2))
                info['percentage'] = (info['current_step'] / info['total_steps']) * 100.0 if info['total_steps'] > 0 else 0.0
            except (ValueError, IndexError):
                info['current_step'] = 1
                info['total_steps'] = 1
                info['percentage'] = 0.0
        
        # Extract context message
        lines = text.split('\n')
        for line in lines:
            if match.group() in line:
                # Clean the line and use it as context
                clean_line = re.sub(r'[█▉▊▋▌▍▎▏░▒▓\[\]|\/\-\\=]+', '', line).strip()
                clean_line = re.sub(r'\d+\s*%', '', clean_line).strip()
                if clean_line:
                    info['context_message'] = clean_line
                break
        
        return info


class ProgressDisplay:
    """Manages a single progress display"""
    
    def __init__(self, session_id: str, channel: discord.TextChannel, 
                 initial_state: ProgressState):
        self.session_id = session_id
        self.channel = channel
        self.state = initial_state
        self.message: Optional[discord.Message] = None
        self._update_lock = asyncio.Lock()
        self._last_discord_update = 0
        self.update_interval = 2.0  # Minimum seconds between Discord updates
        
    async def update(self, new_info: Dict):
        """Update progress display"""
        async with self._update_lock:
            # Update state
            old_percentage = self.state.percentage
            self._update_state(new_info)
            
            # Check if we should update Discord message
            current_time = time.time()
            should_update = (
                current_time - self._last_discord_update >= self.update_interval or
                self.state.is_complete or
                abs(self.state.percentage - old_percentage) >= 5.0  # 5% change
            )
            
            if should_update:
                await self._update_discord_message()
                self._last_discord_update = current_time
    
    def _update_state(self, info: Dict):
        """Update progress state from detected info"""
        self.state.last_update = time.time()
        
        # Update based on progress type
        if 'percentage' in info:
            self.state.current_value = info['percentage']
            self.state.max_value = 100.0
            
        elif 'current' in info and 'total' in info:
            self.state.current_value = info['current']
            self.state.max_value = info['total']
            
        elif 'current_step' in info and 'total_steps' in info:
            self.state.current_value = info['current_step']
            self.state.max_value = info['total_steps']
        
        # Update message
        if 'context_message' in info:
            self.state.message = info['context_message']
        
        # Update metadata
        self.state.metadata.update({
            'last_raw_text': info.get('raw_text', ''),
            'last_matched': info.get('matched_text', ''),
            'detection_time': time.time()
        })
        
        # Check completion
        if self.state.percentage >= 100.0:
            self.state.status = "complete"
    
    async def _update_discord_message(self):
        """Update the Discord message"""
        embed = self._create_progress_embed()
        
        try:
            if self.message is None:
                self.message = await self.channel.send(embed=embed)
            else:
                await self.message.edit(embed=embed)
        except discord.errors.NotFound:
            # Message was deleted, create a new one
            self.message = await self.channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Error updating progress message: {e}")
    
    def _create_progress_embed(self) -> discord.Embed:
        """Create Discord embed for progress display"""
        # Choose color based on status
        if self.state.status == "complete":
            color = discord.Color.green()
            title_emoji = "✅"
        elif self.state.status == "error":
            color = discord.Color.red()
            title_emoji = "❌"
        elif self.state.status == "cancelled":
            color = discord.Color.orange()
            title_emoji = "⏹️"
        else:
            color = discord.Color.blue()
            title_emoji = "⏳"
        
        # Create embed
        embed = discord.Embed(
            title=f"{title_emoji} Progress Update",
            color=color,
            timestamp=discord.utils.utcfromtimestamp(self.state.last_update)
        )
        
        # Add progress bar
        progress_bar = self._create_progress_bar()
        embed.add_field(
            name="Progress",
            value=progress_bar,
            inline=False
        )
        
        # Add status message
        if self.state.message:
            embed.add_field(
                name="Status",
                value=self.state.message,
                inline=False
            )
        
        # Add statistics
        stats_text = f"**{self.state.percentage:.1f}%** complete"
        
        if self.state.progress_type == ProgressType.COUNTER:
            stats_text += f" ({int(self.state.current_value)}/{int(self.state.max_value)})"
        elif self.state.progress_type == ProgressType.STEPS:
            stats_text += f" (Step {int(self.state.current_value)}/{int(self.state.max_value)})"
        
        # Add time information
        elapsed = self.state.elapsed_time
        if elapsed > 60:
            elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
        else:
            elapsed_str = f"{int(elapsed)}s"
        
        stats_text += f"\nElapsed: {elapsed_str}"
        
        # Estimate remaining time
        if self.state.percentage > 0 and not self.state.is_complete:
            estimated_total = elapsed / (self.state.percentage / 100.0)
            remaining = estimated_total - elapsed
            if remaining > 60:
                remaining_str = f"{int(remaining // 60)}m {int(remaining % 60)}s"
            else:
                remaining_str = f"{int(remaining)}s"
            stats_text += f"\nEstimated remaining: {remaining_str}"
        
        embed.add_field(
            name="Statistics",
            value=stats_text,
            inline=True
        )
        
        return embed
    
    def _create_progress_bar(self) -> str:
        """Create a text-based progress bar"""
        bar_length = 20
        filled_length = int(bar_length * self.state.percentage / 100.0)
        
        # Unicode blocks for smooth progress
        blocks = ['░', '▏', '▎', '▍', '▌', '▋', '▊', '▉', '█']
        
        bar = '█' * filled_length
        
        # Add partial block if needed
        if filled_length < bar_length:
            remaining = (bar_length * self.state.percentage / 100.0) - filled_length
            partial_index = int(remaining * 8)
            if partial_index > 0 and partial_index < 8:
                bar += blocks[partial_index]
                filled_length += 1
        
        bar += '░' * (bar_length - len(bar))
        
        return f"```\n{bar} {self.state.percentage:.1f}%\n```"
    
    async def complete(self, message: str = "Task completed successfully"):
        """Mark progress as complete"""
        async with self._update_lock:
            self.state.status = "complete"
            self.state.current_value = self.state.max_value
            self.state.message = message
            await self._update_discord_message()
    
    async def error(self, message: str = "Task failed"):
        """Mark progress as error"""
        async with self._update_lock:
            self.state.status = "error"
            self.state.message = message
            await self._update_discord_message()
    
    async def cancel(self, message: str = "Task cancelled"):
        """Mark progress as cancelled"""
        async with self._update_lock:
            self.state.status = "cancelled"
            self.state.message = message
            await self._update_discord_message()


class ProgressManager:
    """Manages multiple progress displays across sessions"""
    
    def __init__(self):
        self.active_progress: Dict[str, ProgressDisplay] = {}
        self._lock = asyncio.Lock()
        
    async def handle_output(self, session_id: str, text: str, 
                          channel: discord.TextChannel) -> bool:
        """
        Handle output text and manage progress displays
        Returns True if text was handled as progress
        """
        # Detect progress in text
        progress_info = ProgressDetector.detect_progress(text)
        if not progress_info:
            return False
        
        async with self._lock:
            # Get or create progress display
            if session_id not in self.active_progress:
                # Create new progress state
                state = ProgressState(
                    session_id=session_id,
                    progress_type=progress_info['type']
                )
                
                # Create progress display
                self.active_progress[session_id] = ProgressDisplay(
                    session_id, channel, state
                )
                
                logger.info(f"Created progress display for session {session_id}")
            
            # Update existing progress
            await self.active_progress[session_id].update(progress_info)
        
        return True
    
    async def complete_progress(self, session_id: str, message: str = None):
        """Mark progress as complete for a session"""
        async with self._lock:
            if session_id in self.active_progress:
                await self.active_progress[session_id].complete(message)
                # Keep for a bit then remove
                await asyncio.sleep(5)
                del self.active_progress[session_id]
    
    async def error_progress(self, session_id: str, message: str = None):
        """Mark progress as error for a session"""
        async with self._lock:
            if session_id in self.active_progress:
                await self.active_progress[session_id].error(message)
                await asyncio.sleep(5)
                del self.active_progress[session_id]
    
    async def cancel_progress(self, session_id: str, message: str = None):
        """Cancel progress for a session"""
        async with self._lock:
            if session_id in self.active_progress:
                await self.active_progress[session_id].cancel(message)
                del self.active_progress[session_id]
    
    def has_active_progress(self, session_id: str) -> bool:
        """Check if session has active progress display"""
        return session_id in self.active_progress
    
    def get_progress_state(self, session_id: str) -> Optional[ProgressState]:
        """Get current progress state for a session"""
        if session_id in self.active_progress:
            return self.active_progress[session_id].state
        return None
    
    async def cleanup_inactive(self, max_age: float = 600):  # 10 minutes
        """Clean up inactive progress displays"""
        current_time = time.time()
        to_remove = []
        
        async with self._lock:
            for session_id, display in self.active_progress.items():
                if (current_time - display.state.last_update > max_age and
                    not display.state.is_complete):
                    to_remove.append(session_id)
            
            for session_id in to_remove:
                await self.active_progress[session_id].cancel("Progress timeout")
                del self.active_progress[session_id]
                logger.info(f"Cleaned up inactive progress for session {session_id}")
    
    def get_all_active(self) -> List[str]:
        """Get all sessions with active progress"""
        return list(self.active_progress.keys())