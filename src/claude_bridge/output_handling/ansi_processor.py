"""
Advanced ANSI Escape Sequence Processor for Claude Bridge

Handles comprehensive ANSI escape sequence processing, color conversion,
and Claude Code specific output patterns.
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum

from ..utils.logging_setup import get_logger

logger = get_logger('ansi_processor')


class ANSIColor(Enum):
    """ANSI color codes mapping"""
    BLACK = 30
    RED = 31
    GREEN = 32
    YELLOW = 33
    BLUE = 34
    MAGENTA = 35
    CYAN = 36
    WHITE = 37
    BRIGHT_BLACK = 90
    BRIGHT_RED = 91
    BRIGHT_GREEN = 92
    BRIGHT_YELLOW = 93
    BRIGHT_BLUE = 94
    BRIGHT_MAGENTA = 95
    BRIGHT_CYAN = 96
    BRIGHT_WHITE = 97


class ANSIProcessor:
    """Advanced ANSI escape sequence processor"""
    
    # Comprehensive ANSI escape patterns
    ANSI_PATTERNS = {
        # Control Sequence Introducer (CSI) sequences
        'csi': re.compile(r'\x1B\[[0-9;]*[A-Za-z]'),
        # Operating System Commands (OSC)
        'osc': re.compile(r'\x1B\][^\x07\x1B]*(?:\x07|\x1B\\)'),
        # Single character escapes
        'single_char': re.compile(r'\x1B[#%()*+]'),
        # Private mode characters
        'private': re.compile(r'\x1B\[[?!><][0-9;]*[A-Za-z]'),
        # Device Control String (DCS)
        'dcs': re.compile(r'\x1BP[^\x1B]*(?:\x1B\\|\x9C)'),
        # Application Program Command (APC)
        'apc': re.compile(r'\x1B_[^\x1B]*(?:\x1B\\|\x9C)'),
        # Privacy Message (PM)
        'pm': re.compile(r'\x1B\^[^\x1B]*(?:\x1B\\|\x9C)'),
        # String Terminator (ST)
        'st': re.compile(r'\x1B\\'),
    }
    
    # Color code mappings for Discord conversion
    DISCORD_COLOR_MAP = {
        ANSIColor.BLACK: '```fix\n{text}\n```',
        ANSIColor.RED: '```diff\n- {text}\n```',
        ANSIColor.GREEN: '```diff\n+ {text}\n```',
        ANSIColor.YELLOW: '```fix\n{text}\n```',
        ANSIColor.BLUE: '```ini\n[{text}]\n```',
        ANSIColor.MAGENTA: '```css\n{text}\n```',
        ANSIColor.CYAN: '```yaml\n{text}: info\n```',
        ANSIColor.WHITE: '```\n{text}\n```',
    }
    
    # Claude Code specific patterns
    CLAUDE_PATTERNS = {
        # Progress indicators
        'progress_bar': re.compile(r'[█▉▊▋▌▍▎▏░▒▓]{10,}|\|[\/\-\\|]+\||\[[=#\-\.]+\]'),
        'percentage': re.compile(r'\b\d{1,3}%|\b\d{1,3}\.\d%'),
        'spinner': re.compile(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]|[|\/\-\\]'),
        
        # Status messages
        'thinking': re.compile(r'Thinking[\.]*|Processing[\.]*|Loading[\.]*', re.IGNORECASE),
        'working': re.compile(r'Working on it[\.]*|Please wait[\.]*', re.IGNORECASE),
        
        # File operations
        'file_created': re.compile(r'Created file:?\s+(.+)', re.IGNORECASE),
        'file_modified': re.compile(r'Modified file:?\s+(.+)', re.IGNORECASE),
        'file_deleted': re.compile(r'Deleted file:?\s+(.+)', re.IGNORECASE),
        
        # Command execution
        'command_start': re.compile(r'Running:?\s+(.+)', re.IGNORECASE),
        'command_complete': re.compile(r'Completed:?\s+(.+)', re.IGNORECASE),
        
        # Errors and warnings
        'error': re.compile(r'Error:?\s+(.+)', re.IGNORECASE),
        'warning': re.compile(r'Warning:?\s+(.+)', re.IGNORECASE),
        'success': re.compile(r'Success:?\s+(.+)|✅\s*(.+)', re.IGNORECASE),
    }
    
    def __init__(self):
        self.color_state = None
        self.style_state = set()
        self.preserve_semantics = True
        
    def strip_all_ansi(self, text: str) -> str:
        """Remove all ANSI escape sequences from text"""
        if not text:
            return text
            
        result = text
        
        # Apply all patterns
        for pattern_name, pattern in self.ANSI_PATTERNS.items():
            result = pattern.sub('', result)
            
        # Additional cleanup for any remaining escape sequences
        result = re.sub(r'\x1B[@-_][0-?]*[ -/]*[@-~]', '', result)
        
        return result
    
    def extract_ansi_info(self, text: str) -> List[Dict]:
        """Extract ANSI escape sequence information"""
        if not text:
            return []
            
        sequences = []
        
        for pattern_name, pattern in self.ANSI_PATTERNS.items():
            for match in pattern.finditer(text):
                sequences.append({
                    'type': pattern_name,
                    'sequence': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'length': match.end() - match.start()
                })
        
        # Sort by position
        sequences.sort(key=lambda x: x['start'])
        return sequences
    
    def convert_ansi_to_discord(self, text: str) -> str:
        """Convert ANSI colored text to Discord markdown"""
        if not text:
            return text
            
        # First, identify and preserve semantic content
        semantic_text = self.extract_semantic_content(text)
        
        # Remove ANSI sequences but try to preserve meaning
        clean_text = self.strip_all_ansi(text)
        
        # Apply Discord formatting based on semantic analysis
        if semantic_text['type']:
            return self.format_semantic_content(clean_text, semantic_text)
        
        return clean_text
    
    def extract_semantic_content(self, text: str) -> Dict:
        """Extract semantic meaning from Claude Code output"""
        result = {
            'type': None,
            'content': text,
            'metadata': {}
        }
        
        # Check for Claude-specific patterns
        for pattern_name, pattern in self.CLAUDE_PATTERNS.items():
            match = pattern.search(text)
            if match:
                result['type'] = pattern_name
                result['metadata']['match'] = match.group()
                if match.groups():
                    result['metadata']['groups'] = match.groups()
                break
        
        return result
    
    def format_semantic_content(self, text: str, semantic_info: Dict) -> str:
        """Format content based on semantic information"""
        content_type = semantic_info['type']
        
        if content_type in ['error']:
            return f"```diff\n- {text}\n```"
        elif content_type in ['success']:
            return f"```diff\n+ {text}\n```"
        elif content_type in ['warning']:
            return f"```fix\n{text}\n```"
        elif content_type in ['file_created', 'file_modified', 'file_deleted']:
            return f"```yaml\n{text}\n```"
        elif content_type in ['command_start', 'command_complete']:
            return f"```bash\n{text}\n```"
        elif content_type in ['thinking', 'working']:
            # These are usually filtered out, but if kept, format as info
            return f"*{text}*"
        else:
            return text
    
    def is_progress_line(self, line: str) -> bool:
        """Check if a line contains progress information"""
        if not line.strip():
            return False
            
        # Check for progress patterns
        for pattern_name in ['progress_bar', 'percentage', 'spinner', 'thinking', 'working']:
            if pattern_name in self.CLAUDE_PATTERNS:
                if self.CLAUDE_PATTERNS[pattern_name].search(line):
                    return True
        
        return False
    
    def should_suppress_line(self, line: str) -> bool:
        """Check if a line should be suppressed from output"""
        if not line.strip():
            return False
            
        # Suppress progress indicators and temporary status
        suppress_patterns = ['progress_bar', 'spinner', 'thinking']
        
        for pattern_name in suppress_patterns:
            if pattern_name in self.CLAUDE_PATTERNS:
                if self.CLAUDE_PATTERNS[pattern_name].search(line):
                    return True
        
        return False
    
    def process_claude_output(self, text: str) -> str:
        """Process Claude Code output with intelligent filtering"""
        if not text:
            return text
            
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Skip suppressed lines
            if self.should_suppress_line(line):
                continue
                
            # Convert ANSI to Discord format
            processed_line = self.convert_ansi_to_discord(line)
            processed_lines.append(processed_line)
        
        return '\n'.join(processed_lines)
    
    def get_clean_text_length(self, text: str) -> int:
        """Get the display length of text without ANSI sequences"""
        clean_text = self.strip_all_ansi(text)
        return len(clean_text)
    
    def truncate_with_ansi_awareness(self, text: str, max_length: int) -> str:
        """Truncate text while being aware of ANSI sequences"""
        if self.get_clean_text_length(text) <= max_length:
            return text
            
        # Extract ANSI sequences and their positions
        ansi_info = self.extract_ansi_info(text)
        
        # Calculate actual character positions
        clean_length = 0
        result_end = 0
        
        for i, char in enumerate(text):
            # Skip if character is part of ANSI sequence
            is_ansi = any(
                seq['start'] <= i < seq['end'] 
                for seq in ansi_info
            )
            
            if not is_ansi:
                clean_length += 1
                if clean_length >= max_length:
                    result_end = i
                    break
            result_end = i
        
        truncated = text[:result_end + 1]
        
        # Clean up any incomplete ANSI sequences at the end
        return self.cleanup_incomplete_ansi(truncated)
    
    def cleanup_incomplete_ansi(self, text: str) -> str:
        """Clean up incomplete ANSI sequences at the end of text"""
        if not text:
            return text
            
        # Look for incomplete escape sequence at the end
        incomplete_pattern = re.compile(r'\x1B[^\x1B]*$')
        match = incomplete_pattern.search(text)
        
        if match:
            # Remove incomplete sequence
            return text[:match.start()]
        
        return text
    
    def analyze_output_patterns(self, text: str) -> Dict:
        """Analyze output for patterns and provide recommendations"""
        analysis = {
            'has_ansi': bool(re.search(r'\x1B', text)),
            'has_progress': False,
            'has_colors': False,
            'semantic_types': [],
            'line_count': len(text.split('\n')),
            'clean_length': self.get_clean_text_length(text),
            'ansi_overhead': len(text) - self.get_clean_text_length(text)
        }
        
        # Check for progress indicators
        analysis['has_progress'] = any(
            self.is_progress_line(line) 
            for line in text.split('\n')
        )
        
        # Check for colors
        color_pattern = re.compile(r'\x1B\[[0-9;]*[3-4][0-9]m')
        analysis['has_colors'] = bool(color_pattern.search(text))
        
        # Identify semantic types
        for line in text.split('\n'):
            semantic = self.extract_semantic_content(line)
            if semantic['type']:
                analysis['semantic_types'].append(semantic['type'])
        
        # Remove duplicates
        analysis['semantic_types'] = list(set(analysis['semantic_types']))
        
        return analysis