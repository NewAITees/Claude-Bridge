#!/usr/bin/env python3
"""
Debug Test for Claude Bridge

Tests individual components to identify real issues.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_process_control():
    """Test basic process control"""
    print("🔧 Testing Process Control...")
    
    try:
        from src.claude_bridge.process_control.process_controller import ProcessController
        
        # Test with simple echo command
        controller = ProcessController(command="echo", working_directory="/tmp")
        
        print("  📝 Starting echo process...")
        success = controller.start_process("DEBUG")
        print(f"  📊 Process started: {success}")
        
        if success and controller.process:
            print(f"  📊 Process PID: {controller.process.pid}")
            print(f"  📊 Process poll: {controller.process.poll()}")
            
            # Try to send input
            print("  📝 Sending test input...")
            send_success = controller.send_input("hello world")
            print(f"  📊 Input sent: {send_success}")
            
            # Wait a bit
            await asyncio.sleep(0.5)
            
            # Check if still running
            running = controller.is_running()
            print(f"  📊 Still running: {running}")
            
            # Get process info
            info = controller.get_process_info()
            print(f"  📊 Process info: {info}")
            
            # Terminate
            term_success = controller.terminate_process()
            print(f"  📊 Terminated: {term_success}")
        
        return success
        
    except Exception as e:
        print(f"  ❌ Process control failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_basic():
    """Test basic session functionality"""
    print("\n📋 Testing Session Management...")
    
    try:
        from src.claude_bridge.core.session import Session
        
        # Create session
        session = Session(id="DEBUG001")
        print(f"  📊 Session created: {session.id}")
        print(f"  📊 Session active: {session.is_active()}")
        
        # Add some data
        session.add_command("test command")
        session.add_output("test output")
        
        print(f"  📊 Commands: {len(session.command_history)}")
        print(f"  📊 Outputs: {len(session.output_buffer)}")
        print(f"  📊 Recent commands: {session.get_recent_commands()}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Session test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_output_processing():
    """Test output processing components"""
    print("\n🎨 Testing Output Processing...")
    
    try:
        from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
        from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter, MessageType
        
        processor = ANSIProcessor()
        formatter = DiscordFormatter()
        
        # Test ANSI processing
        test_text = "\x1b[31mError: Test message\x1b[0m"
        cleaned = processor.strip_all_ansi(test_text)
        print(f"  📊 ANSI removal: '{test_text}' -> '{cleaned}'")
        
        # Test formatting
        chunks = formatter.format_output("Test message", MessageType.NORMAL)
        print(f"  📊 Formatting: {len(chunks)} chunks created")
        
        if chunks:
            print(f"  📊 First chunk: '{chunks[0].content[:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Output processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_detection():
    """Test UI detection"""
    print("\n🎯 Testing UI Detection...")
    
    try:
        from src.claude_bridge.discord_bot.ui_components import PromptDetector
        from src.claude_bridge.discord_bot.progress_display import ProgressDetector
        
        # Test prompt detection
        prompts = [
            "Do you want to continue? (y/n)",
            "Select:\n1. Option A\n2. Option B",
            "Enter your name:",
        ]
        
        for prompt in prompts:
            detection = PromptDetector.detect_prompt(prompt)
            print(f"  📊 '{prompt[:30]}...' -> {detection[0].value if detection else 'None'}")
        
        # Test progress detection
        progress_texts = [
            "Processing... 80%",
            "████████░░ 80%",
            "Step 3/5",
        ]
        
        for progress in progress_texts:
            detection = ProgressDetector.detect_progress(progress)
            print(f"  📊 '{progress}' -> {detection['type'].value if detection else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ UI detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run debug tests"""
    print("🔍 Claude Bridge Debug Test")
    print("=" * 40)
    
    tests = [
        ("Process Control", test_process_control),
        ("Session Basic", test_session_basic),
        ("Output Processing", test_output_processing),
        ("UI Detection", test_ui_detection),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
            
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n" + "=" * 40)
    print(f"🏁 Debug Results: {passed}/{total}")
    
    if passed < total:
        print(f"⚠️ {total - passed} components have issues")
        print("🔧 These need to be fixed for the system to work properly")
    else:
        print("🎉 All core components are working!")

if __name__ == "__main__":
    asyncio.run(main())