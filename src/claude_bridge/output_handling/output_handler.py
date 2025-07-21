"""
Output Handler for Claude Bridge

Handles formatting, ANSI escape sequence removal, and Discord message preparation.
"""

import re
from typing import List
import discord

from ..utils.logging_setup import get_logger

logger = get_logger('output_handler')


class OutputHandler:
    """Handles output formatting and Discord adaptations"""
    
    # ANSI escape sequence pattern
    ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    # Common progress indicators that should be filtered
    PROGRESS_PATTERNS = [
        re.compile(r'^\s*[\|\-\/\\]*\s*\d+%\s*[\|\-\/\\]*\s*$'),
        re.compile(r'^\s*[█▉▊▋▌▍▎▏░▒▓]+\s*\d*%?\s*$'),
        re.compile(r'^\s*[\.]{3,}\s*$'),
        re.compile(r'^\s*Loading[\.]*\s*$', re.IGNORECASE),
        re.compile(r'^\s*Processing[\.]*\s*$', re.IGNORECASE),
    ]
    
    def __init__(self):
        pass
    
    @staticmethod
    def strip_ansi_sequences(text: str) -> str:
        """Remove ANSI escape sequences from text"""
        if not text:
            return text
        
        return OutputHandler.ANSI_ESCAPE.sub('', text)
    
    @staticmethod
    def filter_progress_lines(text: str) -> str:
        """Filter out progress indicator lines"""
        if not text:
            return text
        
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Check if line matches any progress pattern
            is_progress = any(pattern.match(line) for pattern in OutputHandler.PROGRESS_PATTERNS)
            
            if not is_progress:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    @staticmethod
    def clean_whitespace(text: str) -> str:
        """Clean excessive whitespace"""
        if not text:
            return text
        
        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in text.split('\n')]
        
        # Remove excessive empty lines (more than 2 consecutive)
        cleaned_lines = []
        empty_count = 0
        
        for line in lines:
            if line.strip() == '':
                empty_count += 1
                if empty_count <= 2:
                    cleaned_lines.append(line)
            else:
                empty_count = 0
                cleaned_lines.append(line)
        
        # Remove leading and trailing empty lines
        while cleaned_lines and cleaned_lines[0].strip() == '':
            cleaned_lines.pop(0)
        while cleaned_lines and cleaned_lines[-1].strip() == '':
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def format_for_discord(self, text: str) -> str:
        """Format text for Discord display"""
        if not text:
            return text
        
        # Step 1: Remove ANSI sequences
        cleaned = self.strip_ansi_sequences(text)
        
        # Step 2: Filter progress lines
        cleaned = self.filter_progress_lines(cleaned)
        
        # Step 3: Clean whitespace
        cleaned = self.clean_whitespace(cleaned)
        
        # Step 4: Escape Discord markdown if needed
        cleaned = self.escape_discord_markdown(cleaned)
        
        return cleaned
    
    @staticmethod
    def escape_discord_markdown(text: str) -> str:
        """Escape Discord markdown characters in text"""
        if not text:
            return text
        
        # Characters that need escaping in Discord
        escape_chars = ['*', '_', '`', '~', '|', '\\']
        
        # Only escape if the text contains markdown-like patterns
        # and is not already in a code block context
        for char in escape_chars:
            # Simple escape - could be made more sophisticated
            text = text.replace(char, f'\\{char}')
        
        return text
    
    def split_long_output(self, text: str, max_length: int = 1900) -> List[str]:
        """Split long output into Discord-friendly chunks"""
        if not text or len(text) <= max_length:
            return [text] if text else []
        
        chunks = []
        lines = text.split('\n')
        current_chunk = ""
        
        for line in lines:
            # If adding this line would exceed the limit
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.rstrip())
                    current_chunk = ""
                
                # If a single line is too long, truncate it
                if len(line) > max_length:
                    truncated = line[:max_length-50] + "... [truncated]"
                    chunks.append(truncated)
                else:
                    current_chunk = line
            else:
                if current_chunk:
                    current_chunk += '\n'
                current_chunk += line
        
        # Add remaining content
        if current_chunk:
            chunks.append(current_chunk.rstrip())
        
        return chunks
    
    def create_progress_embed(self, progress: float, message: str, 
                            title: str = "Processing...") -> discord.Embed:
        """Create a Discord embed for progress display"""
        
        # Create progress bar
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.orange()
        )
        
        progress_text = f"```\n{bar} {progress:.1f}%\n```"
        embed.add_field(name="Progress", value=progress_text, inline=False)
        
        if message:
            embed.add_field(name="Status", value=message, inline=False)
        
        return embed
    
    def create_error_embed(self, error_message: str, 
                          title: str = "Error") -> discord.Embed:
        """Create a Discord embed for error messages"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=error_message,
            color=discord.Color.red()
        )
        return embed
    
    def create_success_embed(self, message: str, 
                           title: str = "Success") -> discord.Embed:
        """Create a Discord embed for success messages"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=message,
            color=discord.Color.green()
        )
        return embed
    
    def create_info_embed(self, message: str, 
                         title: str = "Information") -> discord.Embed:
        """Create a Discord embed for informational messages"""
        embed = discord.Embed(
            title=f"ℹ️ {title}",
            description=message,
            color=discord.Color.blue()
        )
        return embed
    
    @staticmethod
    def truncate_output_smart(text: str, max_length: int = 1900) -> str:
        """Smart truncation showing beginning and end"""
        if len(text) <= max_length:
            return text
        
        # Calculate split points
        truncation_notice = "\n... [output truncated] ...\n"
        available_length = max_length - len(truncation_notice)
        
        if available_length < 100:
            # If too short, just truncate normally
            return text[:max_length-20] + "... [truncated]"
        
        # Split available length between beginning and end
        start_length = available_length // 2
        end_length = available_length - start_length
        
        # Try to break at line boundaries
        lines = text.split('\n')
        
        # Get beginning lines
        start_text = ""
        start_lines = 0
        for line in lines:
            if len(start_text) + len(line) + 1 <= start_length:
                start_text += line + '\n'
                start_lines += 1
            else:
                break
        
        # Get ending lines
        end_text = ""
        end_lines = 0
        for line in reversed(lines[start_lines:]):
            if len(end_text) + len(line) + 1 <= end_length:
                end_text = line + '\n' + end_text
                end_lines += 1
            else:
                break
        
        # Combine
        result = start_text.rstrip() + truncation_notice + end_text.rstrip()
        
        return result
    
    def format_code_block(self, text: str, language: str = "") -> str:
        """Format text as Discord code block"""
        if not text:
            return "```\n\n```"
        
        # Ensure text doesn't break out of code block
        text = text.replace('```', '`‍``')  # Use zero-width joiner to break
        
        return f"```{language}\n{text}\n```"
    
    def format_inline_code(self, text: str) -> str:
        """Format text as inline code"""
        if not text:
            return "`​`"  # Zero-width space
        
        # Escape backticks
        text = text.replace('`', '`​`')  # Zero-width space
        
        return f"`{text}`"