"""
Discord Message Formatter for Claude Bridge

Handles intelligent message splitting, formatting, and Discord-specific optimizations.
"""

import re
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import discord

from .ansi_processor import ANSIProcessor
from ..utils.logging_setup import get_logger

logger = get_logger('discord_formatter')


class MessageType(Enum):
    """Types of messages for different formatting"""
    NORMAL = "normal"
    CODE = "code" 
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"


@dataclass
class MessageChunk:
    """Represents a chunk of message to be sent"""
    content: str
    message_type: MessageType
    priority: int = 0
    timestamp: float = 0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}


class DiscordFormatter:
    """Advanced Discord message formatter"""
    
    # Discord limits
    MAX_MESSAGE_LENGTH = 2000
    MAX_EMBED_DESCRIPTION = 4096
    MAX_EMBED_FIELD_VALUE = 1024
    MAX_EMBEDS = 10
    
    # Formatting templates
    CODE_BLOCK_TEMPLATE = "```{language}\n{content}\n```"
    INLINE_CODE_TEMPLATE = "`{content}`"
    
    # Message splitting strategies
    SPLIT_STRATEGIES = {
        'line_break': lambda text: text.split('\n'),
        'sentence': lambda text: re.split(r'[.!?]+\s+', text),
        'word': lambda text: text.split(' '),
        'character': lambda text: [text[i:i+1] for i in range(len(text))]
    }
    
    def __init__(self, max_message_length: int = 1900):  # Leave buffer for formatting
        self.max_length = max_message_length
        self.ansi_processor = ANSIProcessor()
        
        # Message queue for rate limiting
        self.message_queue: List[MessageChunk] = []
        self.last_sent = 0
        self.rate_limit_delay = 0.5  # 500ms between messages
        
    def format_output(self, text: str, message_type: MessageType = MessageType.NORMAL) -> List[MessageChunk]:
        """Format output text into Discord-ready chunks"""
        if not text or not text.strip():
            return []
        
        # Process ANSI sequences
        processed_text = self.ansi_processor.process_claude_output(text)
        
        # Analyze content for optimal formatting
        analysis = self._analyze_content(processed_text, message_type)
        
        # Split into appropriate chunks
        chunks = self._split_content(processed_text, analysis)
        
        # Format each chunk
        formatted_chunks = []
        for i, chunk in enumerate(chunks):
            formatted_chunk = self._format_chunk(
                chunk, message_type, analysis, 
                chunk_index=i, total_chunks=len(chunks)
            )
            formatted_chunks.append(formatted_chunk)
        
        return formatted_chunks
    
    def _analyze_content(self, text: str, message_type: MessageType) -> Dict:
        """Analyze content to determine optimal formatting strategy"""
        analysis = {
            'length': len(text),
            'line_count': len(text.split('\n')),
            'has_code': self._detect_code_content(text),
            'has_file_paths': bool(re.search(r'[/\\][\w/\\.-]+\.\w+', text)),
            'has_urls': bool(re.search(r'https?://\S+', text)),
            'has_commands': bool(re.search(r'^\s*[$#>]\s*\w+', text, re.MULTILINE)),
            'structure': self._analyze_structure(text),
            'priority': self._calculate_priority(text, message_type),
            'recommended_format': self._recommend_format(text, message_type)
        }
        
        return analysis
    
    def _detect_code_content(self, text: str) -> bool:
        """Detect if text contains code"""
        code_indicators = [
            r'def\s+\w+\(',           # Python functions
            r'function\s+\w+\(',      # JavaScript functions  
            r'class\s+\w+',          # Class definitions
            r'import\s+\w+',         # Import statements
            r'from\s+\w+\s+import',  # Python imports
            r'#include\s*<',         # C/C++ includes
            r'package\s+\w+',        # Go/Java packages
            r'{\s*\n.*\n\s*}',       # Code blocks with braces
            r'^\s*[{}()\[\];,]',     # Programming punctuation
            r'\w+\.\w+\(',           # Method calls
        ]
        
        return any(re.search(pattern, text, re.MULTILINE) for pattern in code_indicators)
    
    def _analyze_structure(self, text: str) -> Dict:
        """Analyze text structure"""
        lines = text.split('\n')
        
        structure = {
            'empty_lines': sum(1 for line in lines if not line.strip()),
            'long_lines': sum(1 for line in lines if len(line) > 100),
            'avg_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
            'indentation_levels': len(set(len(line) - len(line.lstrip()) for line in lines if line.strip())),
            'bullet_points': sum(1 for line in lines if re.match(r'^\s*[-*+•]\s', line)),
            'numbered_lists': sum(1 for line in lines if re.match(r'^\s*\d+\.\s', line)),
        }
        
        return structure
    
    def _calculate_priority(self, text: str, message_type: MessageType) -> int:
        """Calculate message priority for queue management"""
        priority = 0
        
        # Base priority by message type
        type_priorities = {
            MessageType.ERROR: 100,
            MessageType.WARNING: 80,
            MessageType.SUCCESS: 60,
            MessageType.INFO: 40,
            MessageType.CODE: 30,
            MessageType.NORMAL: 20,
            MessageType.PROGRESS: 10
        }
        
        priority += type_priorities.get(message_type, 20)
        
        # Boost priority for short messages
        if len(text) < 100:
            priority += 10
        
        # Boost priority for interactive content
        if any(keyword in text.lower() for keyword in ['error', 'failed', 'success', 'complete']):
            priority += 20
        
        return priority
    
    def _recommend_format(self, text: str, message_type: MessageType) -> str:
        """Recommend formatting style"""
        if message_type == MessageType.CODE or self._detect_code_content(text):
            return 'code_block'
        elif message_type in [MessageType.ERROR, MessageType.WARNING]:
            return 'embed'
        elif len(text) < 50 and '\n' not in text:
            return 'inline_code'
        else:
            return 'normal'
    
    def _split_content(self, text: str, analysis: Dict) -> List[str]:
        """Split content using the most appropriate strategy"""
        if analysis['length'] <= self.max_length:
            return [text]
        
        # Choose splitting strategy based on analysis
        if analysis['structure']['bullet_points'] > 0 or analysis['structure']['numbered_lists'] > 0:
            strategy = 'line_break'
        elif analysis['has_code']:
            strategy = 'line_break'  # Preserve code structure
        elif analysis['length'] > self.max_length * 3:
            strategy = 'sentence'  # For very long text
        else:
            strategy = 'line_break'
        
        return self._apply_split_strategy(text, strategy)
    
    def _apply_split_strategy(self, text: str, strategy: str) -> List[str]:
        """Apply the chosen splitting strategy"""
        if strategy not in self.SPLIT_STRATEGIES:
            strategy = 'line_break'
        
        parts = self.SPLIT_STRATEGIES[strategy](text)
        chunks = []
        current_chunk = ""
        
        for part in parts:
            # Add separator back (except for character splitting)
            if strategy == 'line_break':
                test_chunk = current_chunk + ('\n' if current_chunk else '') + part
            elif strategy == 'sentence':
                test_chunk = current_chunk + ('. ' if current_chunk else '') + part
            elif strategy == 'word':
                test_chunk = current_chunk + (' ' if current_chunk else '') + part
            else:  # character
                test_chunk = current_chunk + part
            
            if len(test_chunk) <= self.max_length:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Handle parts that are too long even by themselves
                if len(part) > self.max_length:
                    # Force character-level splitting
                    for i in range(0, len(part), self.max_length):
                        chunks.append(part[i:i + self.max_length])
                    current_chunk = ""
                else:
                    current_chunk = part
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _format_chunk(self, content: str, message_type: MessageType, 
                     analysis: Dict, chunk_index: int = 0, 
                     total_chunks: int = 1) -> MessageChunk:
        """Format a single chunk"""
        
        formatted_content = content
        recommended_format = analysis['recommended_format']
        
        # Apply formatting based on recommendation
        if recommended_format == 'code_block':
            # Detect language for syntax highlighting
            language = self._detect_language(content)
            formatted_content = self.CODE_BLOCK_TEMPLATE.format(
                language=language, content=content.strip()
            )
        elif recommended_format == 'inline_code':
            formatted_content = self.INLINE_CODE_TEMPLATE.format(content=content.strip())
        elif recommended_format == 'embed':
            # This will be handled at the Discord sending level
            pass
        
        # Add chunk indicators for multi-part messages
        if total_chunks > 1:
            prefix = f"**Part {chunk_index + 1}/{total_chunks}**\n"
            if len(prefix + formatted_content) <= self.max_length:
                formatted_content = prefix + formatted_content
        
        return MessageChunk(
            content=formatted_content,
            message_type=message_type,
            priority=analysis['priority'],
            metadata={
                'chunk_index': chunk_index,
                'total_chunks': total_chunks,
                'original_length': len(content),
                'format': recommended_format
            }
        )
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language for syntax highlighting"""
        # Simple language detection based on patterns
        language_patterns = {
            'python': [r'def\s+\w+\(', r'import\s+\w+', r'from\s+\w+\s+import', r'if\s+__name__\s*=='],
            'javascript': [r'function\s+\w+\(', r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'=>'],
            'bash': [r'#!/bin/bash', r'^\s*\$\s+', r'cd\s+', r'ls\s+'],
            'json': [r'^\s*{', r'"\w+":', r'^\s*\['],
            'yaml': [r'^\s*\w+:', r'^\s*-\s+\w+'],
            'xml': [r'<\w+[^>]*>', r'<\/\w+>'],
            'sql': [r'SELECT\s+', r'FROM\s+', r'WHERE\s+', r'INSERT\s+'],
        }
        
        for language, patterns in language_patterns.items():
            if any(re.search(pattern, content, re.MULTILINE | re.IGNORECASE) for pattern in patterns):
                return language
        
        return ''  # No language detection
    
    def create_embed(self, chunk: MessageChunk) -> discord.Embed:
        """Create Discord embed for special message types"""
        embed_colors = {
            MessageType.ERROR: discord.Color.red(),
            MessageType.SUCCESS: discord.Color.green(),
            MessageType.WARNING: discord.Color.orange(),
            MessageType.INFO: discord.Color.blue(),
            MessageType.CODE: discord.Color.dark_grey(),
            MessageType.NORMAL: discord.Color.light_grey(),
            MessageType.PROGRESS: discord.Color.purple()
        }
        
        embed_titles = {
            MessageType.ERROR: "❌ Error",
            MessageType.SUCCESS: "✅ Success", 
            MessageType.WARNING: "⚠️ Warning",
            MessageType.INFO: "ℹ️ Information",
            MessageType.CODE: "💻 Code",
            MessageType.NORMAL: "📄 Output",
            MessageType.PROGRESS: "⏳ Progress"
        }
        
        embed = discord.Embed(
            title=embed_titles.get(chunk.message_type, "Output"),
            color=embed_colors.get(chunk.message_type, discord.Color.light_grey()),
            timestamp=discord.utils.utcfromtimestamp(chunk.timestamp)
        )
        
        # Truncate content if too long for embed
        content = chunk.content
        if len(content) > self.MAX_EMBED_DESCRIPTION:
            content = content[:self.MAX_EMBED_DESCRIPTION-50] + "\n... (truncated)"
        
        embed.description = content
        
        # Add metadata as fields if available
        if chunk.metadata.get('total_chunks', 1) > 1:
            embed.add_field(
                name="Part",
                value=f"{chunk.metadata['chunk_index'] + 1} of {chunk.metadata['total_chunks']}",
                inline=True
            )
        
        return embed
    
    def should_use_embed(self, chunk: MessageChunk) -> bool:
        """Determine if chunk should use embed format"""
        return chunk.message_type in [
            MessageType.ERROR, 
            MessageType.SUCCESS, 
            MessageType.WARNING,
            MessageType.INFO
        ]
    
    def optimize_for_mobile(self, chunks: List[MessageChunk]) -> List[MessageChunk]:
        """Optimize message chunks for mobile Discord viewing"""
        optimized = []
        
        for chunk in chunks:
            # Break very long code blocks for mobile
            if chunk.message_type == MessageType.CODE and len(chunk.content) > 1000:
                # Split code blocks more aggressively
                lines = chunk.content.split('\n')
                current_block = ""
                
                for line in lines:
                    if len(current_block + line + '\n') > 800:
                        if current_block:
                            optimized.append(MessageChunk(
                                content=f"```\n{current_block.strip()}\n```",
                                message_type=chunk.message_type,
                                priority=chunk.priority,
                                metadata={**chunk.metadata, 'mobile_optimized': True}
                            ))
                        current_block = line + '\n'
                    else:
                        current_block += line + '\n'
                
                if current_block:
                    optimized.append(MessageChunk(
                        content=f"```\n{current_block.strip()}\n```",
                        message_type=chunk.message_type,
                        priority=chunk.priority,
                        metadata={**chunk.metadata, 'mobile_optimized': True}
                    ))
            else:
                optimized.append(chunk)
        
        return optimized
    
    def add_message_to_queue(self, chunks: List[MessageChunk]):
        """Add message chunks to the sending queue"""
        for chunk in chunks:
            self.message_queue.append(chunk)
        
        # Sort queue by priority
        self.message_queue.sort(key=lambda x: x.priority, reverse=True)
    
    def get_next_message(self) -> Optional[MessageChunk]:
        """Get next message from queue respecting rate limits"""
        if not self.message_queue:
            return None
        
        current_time = time.time()
        if current_time - self.last_sent < self.rate_limit_delay:
            return None
        
        self.last_sent = current_time
        return self.message_queue.pop(0)
    
    def estimate_send_time(self) -> float:
        """Estimate time to send all queued messages"""
        return len(self.message_queue) * self.rate_limit_delay