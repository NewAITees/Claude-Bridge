"""
Unit tests for OutputHandler
"""

import pytest
from src.claude_bridge.output_handling.output_handler import OutputHandler


class TestOutputHandler:
    """Test cases for OutputHandler"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = OutputHandler()
    
    def test_strip_ansi_sequences(self):
        """Test ANSI escape sequence removal"""
        # Test with ANSI color codes
        text_with_ansi = "\x1b[31mRed text\x1b[0m normal text \x1b[1mBold\x1b[0m"
        expected = "Red text normal text Bold"
        assert self.handler.strip_ansi_sequences(text_with_ansi) == expected
        
        # Test with no ANSI codes
        normal_text = "Just normal text"
        assert self.handler.strip_ansi_sequences(normal_text) == normal_text
        
        # Test with empty string
        assert self.handler.strip_ansi_sequences("") == ""
        
        # Test with None
        assert self.handler.strip_ansi_sequences(None) is None
    
    def test_filter_progress_lines(self):
        """Test progress line filtering"""
        text_with_progress = """
        Starting process...
        ████████░░ 80%
        Loading...
        Processing file.txt
        ........................
        Task completed successfully
        """
        
        result = self.handler.filter_progress_lines(text_with_progress)
        
        # Should remove progress bars and loading indicators
        assert "████████░░ 80%" not in result
        assert "Loading..." not in result
        assert "........................" not in result
        
        # Should keep actual content
        assert "Starting process..." in result
        assert "Processing file.txt" in result
        assert "Task completed successfully" in result
    
    def test_clean_whitespace(self):
        """Test whitespace cleaning"""
        messy_text = """

        Line 1


        Line 2



        Line 3    

        """
        
        result = self.handler.clean_whitespace(messy_text)
        
        # Should remove leading and trailing empty lines
        assert not result.startswith('\n')
        assert not result.endswith('\n')
        
        # Should reduce excessive empty lines
        lines = result.split('\n')
        empty_count = 0
        max_consecutive_empty = 0
        
        for line in lines:
            if line.strip() == '':
                empty_count += 1
                max_consecutive_empty = max(max_consecutive_empty, empty_count)
            else:
                empty_count = 0
        
        assert max_consecutive_empty <= 2
    
    def test_format_for_discord(self):
        """Test complete Discord formatting"""
        complex_text = "\x1b[31mError:\x1b[0m File not found\n████████░░ 80%\nProcessing continues..."
        
        result = self.handler.format_for_discord(complex_text)
        
        # Should remove ANSI and progress lines
        assert "\x1b[31m" not in result
        assert "████████░░ 80%" not in result
        assert "Error: File not found" in result or "Error:\\: File not found" in result
        assert "Processing continues..." in result
    
    def test_split_long_output(self):
        """Test output splitting for Discord"""
        # Short text should remain unchanged
        short_text = "Short message"
        result = self.handler.split_long_output(short_text, 100)
        assert result == [short_text]
        
        # Long text should be split
        long_text = "Line " + ("x" * 2000)  # Very long line
        result = self.handler.split_long_output(long_text, 100)
        assert len(result) > 1
        assert all(len(chunk) <= 150 for chunk in result)  # Allow some overhead for truncation message
        
        # Empty text
        result = self.handler.split_long_output("", 100)
        assert result == []
        
        # Multi-line text
        lines = ["Line " + str(i) for i in range(100)]
        multi_line_text = '\n'.join(lines)
        result = self.handler.split_long_output(multi_line_text, 100)
        
        # Should split at reasonable points
        assert len(result) > 1
        combined = '\n'.join(result)
        # Most content should be preserved (some may be truncated)
        assert len(combined) >= len(multi_line_text) * 0.8
    
    def test_escape_discord_markdown(self):
        """Test Discord markdown escaping"""
        markdown_text = "This is *bold* and _italic_ and `code` and ~strikethrough~"
        result = self.handler.escape_discord_markdown(markdown_text)
        
        # Should escape special characters
        assert "\\*bold\\*" in result
        assert "\\_italic\\_" in result
        assert "\\`code\\`" in result
        assert "\\~strikethrough\\~" in result
    
    def test_truncate_output_smart(self):
        """Test smart output truncation"""
        # Short text should remain unchanged
        short_text = "Short message"
        result = self.handler.truncate_output_smart(short_text, 100)
        assert result == short_text
        
        # Long text should be truncated with beginning and end
        long_text = '\n'.join([f"Line {i}" for i in range(1000)])
        result = self.handler.truncate_output_smart(long_text, 200)
        
        assert len(result) <= 200
        assert "Line 1" in result or "Line 0" in result  # Should have beginning
        assert "truncated" in result  # Should have truncation notice
        # Should have some content from the end (hard to test exactly which lines)
    
    def test_format_code_block(self):
        """Test code block formatting"""
        code = "def hello():\n    print('Hello, World!')"
        result = self.handler.format_code_block(code, "python")
        
        assert result.startswith("```python\n")
        assert result.endswith("\n```")
        assert code in result
        
        # Test with backticks in content
        code_with_backticks = "console.log(`Hello ${name}`);"
        result = self.handler.format_code_block(code_with_backticks)
        assert "```" in result
        # Should handle backticks in content
    
    def test_format_inline_code(self):
        """Test inline code formatting"""
        code = "print('hello')"
        result = self.handler.format_inline_code(code)
        
        assert result.startswith("`")
        assert result.endswith("`")
        assert code in result or "print(\\'hello\\')" in result  # May be escaped
        
        # Test with backticks in content
        code_with_backtick = "`backtick`"
        result = self.handler.format_inline_code(code_with_backtick)
        assert result.startswith("`")
        assert result.endswith("`")


if __name__ == "__main__":
    pytest.main([__file__])