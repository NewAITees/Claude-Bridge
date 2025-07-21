"""
Real-time Output Buffering System for Claude Bridge

Manages buffering, aggregation, and intelligent delivery of Claude Code output.
"""

import asyncio
import time
from collections import deque
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import threading

from .discord_formatter import DiscordFormatter, MessageChunk, MessageType
from .ansi_processor import ANSIProcessor
from ..utils.logging_setup import get_logger

logger = get_logger('output_buffer')


class BufferStrategy(Enum):
    """Output buffering strategies"""
    IMMEDIATE = "immediate"      # Send immediately
    LINE_BUFFER = "line_buffer"  # Buffer by lines
    TIME_BUFFER = "time_buffer"  # Buffer for time interval
    SMART_BUFFER = "smart_buffer" # Intelligent buffering


@dataclass
class OutputLine:
    """Represents a line of output"""
    content: str
    timestamp: float
    session_id: str
    line_type: MessageType = MessageType.NORMAL
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()


class OutputBuffer:
    """Real-time output buffer with intelligent aggregation"""
    
    def __init__(self, 
                 session_id: str,
                 max_buffer_size: int = 1000,
                 flush_interval: float = 2.0,
                 strategy: BufferStrategy = BufferStrategy.SMART_BUFFER):
        
        self.session_id = session_id
        self.max_buffer_size = max_buffer_size
        self.flush_interval = flush_interval
        self.strategy = strategy
        
        # Buffer storage
        self.line_buffer: deque[OutputLine] = deque(maxlen=max_buffer_size)
        self.pending_buffer: List[OutputLine] = []
        
        # Processing components
        self.ansi_processor = ANSIProcessor()
        self.discord_formatter = DiscordFormatter()
        
        # State management
        self._lock = threading.RLock()
        self._last_flush = time.time()
        self._buffer_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self.output_callback: Optional[Callable[[List[MessageChunk]], None]] = None
        
        # Buffering intelligence
        self._consecutive_similar = 0
        self._last_line_type = None
        self._burst_mode = False
        self._burst_start = 0
        
    async def start(self):
        """Start the output buffer processing"""
        logger.info(f"Starting output buffer for session {self.session_id}")
        self._running = True
        self._buffer_task = asyncio.create_task(self._buffer_loop())
    
    async def stop(self):
        """Stop the output buffer and flush remaining content"""
        logger.info(f"Stopping output buffer for session {self.session_id}")
        self._running = False
        
        if self._buffer_task:
            self._buffer_task.cancel()
            try:
                await self._buffer_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush_buffer()
    
    def add_output(self, content: str, line_type: MessageType = MessageType.NORMAL):
        """Add new output to the buffer"""
        if not content:
            return
        
        # Create output line
        output_line = OutputLine(
            content=content,
            timestamp=time.time(),
            session_id=self.session_id,
            line_type=line_type
        )
        
        # Analyze content
        self._analyze_line(output_line)
        
        with self._lock:
            self.line_buffer.append(output_line)
            self.pending_buffer.append(output_line)
            
            # Update intelligence tracking
            self._update_burst_detection(output_line)
            
            # Trigger immediate flush if needed
            if self._should_flush_immediately(output_line):
                asyncio.create_task(self.flush_buffer())
    
    def _analyze_line(self, line: OutputLine):
        """Analyze line content for metadata"""
        content = line.content
        
        # Detect line characteristics
        analysis = self.ansi_processor.analyze_output_patterns(content)
        
        line.metadata.update({
            'has_ansi': analysis['has_ansi'],
            'has_progress': analysis['has_progress'],
            'clean_length': analysis['clean_length'],
            'ansi_overhead': analysis['ansi_overhead'],
            'semantic_types': analysis['semantic_types']
        })
        
        # Classify line type if not already set
        if line.line_type == MessageType.NORMAL:
            line.line_type = self._classify_line_type(content, analysis)
    
    def _classify_line_type(self, content: str, analysis: Dict) -> MessageType:
        """Classify the type of output line"""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ['error', 'failed', 'exception']):
            return MessageType.ERROR
        elif any(keyword in content_lower for keyword in ['warning', 'warn']):
            return MessageType.WARNING
        elif any(keyword in content_lower for keyword in ['success', 'complete', 'done', '✅']):
            return MessageType.SUCCESS
        elif analysis['has_progress']:
            return MessageType.PROGRESS
        elif any(semantic_type in ['file_created', 'file_modified', 'command_start'] 
                for semantic_type in analysis['semantic_types']):
            return MessageType.INFO
        elif analysis['has_ansi'] and len(analysis['semantic_types']) > 0:
            return MessageType.CODE
        else:
            return MessageType.NORMAL
    
    def _update_burst_detection(self, line: OutputLine):
        """Update burst mode detection"""
        current_time = time.time()
        
        # Detect similar consecutive lines
        if self._last_line_type == line.line_type:
            self._consecutive_similar += 1
        else:
            self._consecutive_similar = 0
            self._last_line_type = line.line_type
        
        # Enter burst mode if many similar lines in short time
        if (self._consecutive_similar > 5 and 
            current_time - self._burst_start < 2.0):
            self._burst_mode = True
            logger.debug(f"Entering burst mode for session {self.session_id}")
        elif current_time - self._burst_start > 5.0:
            # Exit burst mode after timeout
            self._burst_mode = False
            self._burst_start = current_time
    
    def _should_flush_immediately(self, line: OutputLine) -> bool:
        """Determine if buffer should be flushed immediately"""
        if self.strategy == BufferStrategy.IMMEDIATE:
            return True
        
        # High priority messages
        if line.line_type in [MessageType.ERROR, MessageType.SUCCESS]:
            return True
        
        # Interactive prompts or questions
        if any(indicator in line.content.lower() 
               for indicator in ['?', 'enter', 'continue', 'press', 'confirm']):
            return True
        
        # Buffer is getting full
        if len(self.pending_buffer) > 20:
            return True
        
        # Long time since last flush
        if time.time() - self._last_flush > self.flush_interval * 2:
            return True
        
        return False
    
    async def _buffer_loop(self):
        """Main buffer processing loop"""
        while self._running:
            try:
                current_time = time.time()
                
                # Check if it's time to flush
                should_flush = (
                    len(self.pending_buffer) > 0 and
                    current_time - self._last_flush >= self.flush_interval
                )
                
                if should_flush:
                    await self.flush_buffer()
                
                # Adjust sleep time based on activity
                sleep_time = 0.1 if self._burst_mode else 0.5
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in buffer loop: {e}")
                await asyncio.sleep(1.0)
    
    async def flush_buffer(self):
        """Flush the pending buffer"""
        with self._lock:
            if not self.pending_buffer:
                return
            
            lines_to_process = self.pending_buffer.copy()
            self.pending_buffer.clear()
            self._last_flush = time.time()
        
        # Process lines based on strategy
        chunks = await self._process_lines(lines_to_process)
        
        if chunks and self.output_callback:
            try:
                await self.output_callback(chunks)
            except Exception as e:
                logger.error(f"Error in output callback: {e}")
    
    async def _process_lines(self, lines: List[OutputLine]) -> List[MessageChunk]:
        """Process buffered lines into Discord message chunks"""
        if not lines:
            return []
        
        # Group lines by type and timing
        grouped_lines = self._group_lines_intelligently(lines)
        
        all_chunks = []
        
        for group in grouped_lines:
            # Combine lines in group
            combined_content = self._combine_lines(group)
            
            if not combined_content.strip():
                continue
            
            # Determine message type for group
            group_type = self._determine_group_type(group)
            
            # Format for Discord
            chunks = self.discord_formatter.format_output(combined_content, group_type)
            
            # Apply mobile optimization if many chunks
            if len(chunks) > 3:
                chunks = self.discord_formatter.optimize_for_mobile(chunks)
            
            all_chunks.extend(chunks)
        
        return all_chunks
    
    def _group_lines_intelligently(self, lines: List[OutputLine]) -> List[List[OutputLine]]:
        """Group lines intelligently for optimal presentation"""
        if not lines:
            return []
        
        groups = []
        current_group = [lines[0]]
        
        for line in lines[1:]:
            # Check if line should be in same group
            should_group = self._should_group_with_previous(current_group[-1], line)
            
            if should_group and len(current_group) < 20:  # Max group size
                current_group.append(line)
            else:
                groups.append(current_group)
                current_group = [line]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _should_group_with_previous(self, prev_line: OutputLine, current_line: OutputLine) -> bool:
        """Determine if lines should be grouped together"""
        # Time-based grouping
        time_diff = current_line.timestamp - prev_line.timestamp
        if time_diff > 3.0:  # More than 3 seconds apart
            return False
        
        # Type-based grouping
        if prev_line.line_type != current_line.line_type:
            # Don't group errors with normal output
            if prev_line.line_type == MessageType.ERROR or current_line.line_type == MessageType.ERROR:
                return False
            # Don't group success messages with other types
            if prev_line.line_type == MessageType.SUCCESS or current_line.line_type == MessageType.SUCCESS:
                return False
        
        # Progress lines should be grouped separately
        if (prev_line.line_type == MessageType.PROGRESS or 
            current_line.line_type == MessageType.PROGRESS):
            return prev_line.line_type == current_line.line_type
        
        # Content-based grouping
        if self._are_related_content(prev_line.content, current_line.content):
            return True
        
        return True  # Default to grouping
    
    def _are_related_content(self, content1: str, content2: str) -> bool:
        """Check if two content lines are related"""
        # Simple heuristics for related content
        
        # Both are file operations
        if (any(op in content1.lower() for op in ['created', 'modified', 'deleted']) and
            any(op in content2.lower() for op in ['created', 'modified', 'deleted'])):
            return True
        
        # Both contain similar file paths
        import re
        path_pattern = r'[/\\][\w/\\.-]+'
        paths1 = re.findall(path_pattern, content1)
        paths2 = re.findall(path_pattern, content2)
        
        if paths1 and paths2:
            # Check if paths share common directory
            for p1 in paths1:
                for p2 in paths2:
                    if len(set(p1.split('/')) & set(p2.split('/'))) > 1:
                        return True
        
        return False
    
    def _combine_lines(self, lines: List[OutputLine]) -> str:
        """Combine multiple lines into a single content string"""
        if not lines:
            return ""
        
        contents = []
        for line in lines:
            if line.content.strip():
                contents.append(line.content.rstrip())
        
        return '\n'.join(contents)
    
    def _determine_group_type(self, lines: List[OutputLine]) -> MessageType:
        """Determine the message type for a group of lines"""
        if not lines:
            return MessageType.NORMAL
        
        # Priority order for message types
        type_priority = {
            MessageType.ERROR: 100,
            MessageType.WARNING: 80,
            MessageType.SUCCESS: 60,
            MessageType.INFO: 40,
            MessageType.CODE: 30,
            MessageType.PROGRESS: 20,
            MessageType.NORMAL: 10
        }
        
        # Find highest priority type in group
        max_priority = 0
        group_type = MessageType.NORMAL
        
        for line in lines:
            priority = type_priority.get(line.line_type, 10)
            if priority > max_priority:
                max_priority = priority
                group_type = line.line_type
        
        return group_type
    
    def get_buffer_stats(self) -> Dict:
        """Get buffer statistics"""
        with self._lock:
            return {
                'session_id': self.session_id,
                'total_lines': len(self.line_buffer),
                'pending_lines': len(self.pending_buffer),
                'last_flush': self._last_flush,
                'flush_interval': self.flush_interval,
                'burst_mode': self._burst_mode,
                'consecutive_similar': self._consecutive_similar,
                'buffer_strategy': self.strategy.value
            }
    
    def set_output_callback(self, callback: Callable[[List[MessageChunk]], None]):
        """Set the callback for processed output"""
        self.output_callback = callback
    
    def get_recent_lines(self, count: int = 10) -> List[OutputLine]:
        """Get recent lines from buffer"""
        with self._lock:
            return list(self.line_buffer)[-count:]
    
    def clear_buffer(self):
        """Clear all buffered content"""
        with self._lock:
            self.line_buffer.clear()
            self.pending_buffer.clear()
            logger.info(f"Buffer cleared for session {self.session_id}")


class BufferManager:
    """Manages multiple output buffers for different sessions"""
    
    def __init__(self):
        self.buffers: Dict[str, OutputBuffer] = {}
        self._lock = threading.RLock()
    
    async def create_buffer(self, session_id: str, **kwargs) -> OutputBuffer:
        """Create a new output buffer for a session"""
        with self._lock:
            if session_id in self.buffers:
                await self.buffers[session_id].stop()
            
            buffer = OutputBuffer(session_id, **kwargs)
            self.buffers[session_id] = buffer
            await buffer.start()
            
            logger.info(f"Created output buffer for session {session_id}")
            return buffer
    
    def get_buffer(self, session_id: str) -> Optional[OutputBuffer]:
        """Get buffer for a session"""
        with self._lock:
            return self.buffers.get(session_id)
    
    async def remove_buffer(self, session_id: str):
        """Remove and stop buffer for a session"""
        with self._lock:
            if session_id in self.buffers:
                await self.buffers[session_id].stop()
                del self.buffers[session_id]
                logger.info(f"Removed output buffer for session {session_id}")
    
    async def stop_all_buffers(self):
        """Stop all active buffers"""
        with self._lock:
            buffer_ids = list(self.buffers.keys())
        
        for session_id in buffer_ids:
            await self.remove_buffer(session_id)
        
        logger.info("All output buffers stopped")
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all buffers"""
        with self._lock:
            return {
                session_id: buffer.get_buffer_stats()
                for session_id, buffer in self.buffers.items()
            }