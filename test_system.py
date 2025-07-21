#!/usr/bin/env python3
"""
Quick System Test for Claude Bridge

Performs basic system validation without external dependencies.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        # Core components
        from src.claude_bridge.core.session import Session
        from src.claude_bridge.core.session_manager import SessionManager
        print("  ✅ Core components")
        
        # Output handling
        from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
        from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter
        from src.claude_bridge.output_handling.output_buffer import OutputBuffer
        print("  ✅ Output handling")
        
        # Discord bot
        from src.claude_bridge.discord_bot.bot import ClaudeBridgeBot
        from src.claude_bridge.discord_bot.ui_components import UIConverter
        from src.claude_bridge.discord_bot.progress_display import ProgressManager
        print("  ✅ Discord bot")
        
        # Utils
        from src.claude_bridge.utils.config import Config
        from src.claude_bridge.utils.error_handler import ErrorHandler
        from src.claude_bridge.utils.performance_monitor import PerformanceMonitor
        print("  ✅ Utilities")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality without external dependencies"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test ANSI processor
        from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
        processor = ANSIProcessor()
        
        test_text = "\x1b[31mRed text\x1b[0m normal text"
        cleaned = processor.strip_all_ansi(test_text)
        assert "Red text normal text" == cleaned
        print("  ✅ ANSI processing")
        
        # Test Discord formatter
        from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter, MessageType
        formatter = DiscordFormatter()
        
        long_text = "Test " * 500  # Create long text
        chunks = formatter.format_output(long_text, MessageType.NORMAL)
        assert len(chunks) > 1
        assert all(len(chunk.content) <= 2000 for chunk in chunks)
        print("  ✅ Discord formatting")
        
        # Test UI detection
        from src.claude_bridge.discord_bot.ui_components import PromptDetector
        
        prompt = "Do you want to continue? (y/n)"
        detection = PromptDetector.detect_prompt(prompt)
        assert detection is not None
        assert detection[0].value == 'yes_no'
        print("  ✅ UI detection")
        
        # Test progress detection
        from src.claude_bridge.discord_bot.progress_display import ProgressDetector
        
        progress = "Processing... ████████░░ 80%"
        info = ProgressDetector.detect_progress(progress)
        assert info is not None
        assert 'percentage' in info
        print("  ✅ Progress detection")
        
        # Test error handling
        from src.claude_bridge.utils.error_handler import ErrorDetector
        
        test_error = ConnectionError("Network timeout")
        error_info = ErrorDetector.classify_error(test_error)
        assert error_info.category.value == 'network'
        print("  ✅ Error handling")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Functionality test failed: {e}")
        return False


async def test_async_components():
    """Test async components"""
    print("\n⚡ Testing async components...")
    
    try:
        # Test session creation (using mock)
        from src.claude_bridge.core.session import Session
        
        session = Session(id="TEST123")
        assert session.id == "TEST123"
        assert not session.is_active()  # No process attached
        print("  ✅ Session creation")
        
        # Test buffer system
        from src.claude_bridge.output_handling.output_buffer import OutputBuffer, BufferStrategy
        
        buffer = OutputBuffer("TEST123", strategy=BufferStrategy.IMMEDIATE)
        buffer.add_output("Test output")
        
        recent = buffer.get_recent_lines(5)
        assert len(recent) > 0
        print("  ✅ Output buffering")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Async test failed: {e}")
        return False


def test_configuration():
    """Test configuration system"""
    print("\n⚙️ Testing configuration...")
    
    try:
        from src.claude_bridge.utils.config import (
            Config, DiscordConfig, ClaudeCodeConfig, 
            SessionConfig, LoggingConfig
        )
        
        # Create test configuration
        config = Config(
            discord=DiscordConfig("test_token", 123456789, 987654321),
            claude_code=ClaudeCodeConfig("echo", "/tmp", 30),
            session=SessionConfig(300, 1900, 100, 60),
            logging=LoggingConfig("INFO", "test.log", "10MB", 3)
        )
        
        # Test validation
        config.validate()  # Should not raise
        print("  ✅ Configuration validation")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Claude Bridge System Test")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Functionality Test", test_basic_functionality),
        ("Async Test", lambda: asyncio.run(test_async_components())),
        ("Configuration Test", test_configuration)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    # Summary
    print(f"\n" + "=" * 40)
    print(f"🏁 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! System is functional.")
        return 0
    else:
        print("⚠️ Some tests failed. Check implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())