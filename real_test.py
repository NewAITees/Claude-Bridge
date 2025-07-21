#!/usr/bin/env python3
"""
Real functionality test with proper long-running process
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_with_python_process():
    """Test with Python interactive shell"""
    print("🐍 Testing with Python Interactive Process...")
    
    try:
        from src.claude_bridge.process_control.process_controller import ProcessController
        
        # Use Python interactive shell
        controller = ProcessController(command="python3", working_directory="/tmp")
        
        print("  📝 Starting Python process...")
        success = controller.start_process("PYTHON_TEST")
        
        if success:
            print(f"  ✅ Process started with PID: {controller.process.pid}")
            
            # Wait for process to initialize
            await asyncio.sleep(0.5)
            
            print(f"  📊 Process running: {controller.is_running()}")
            
            if controller.is_running():
                # Send Python commands
                commands = [
                    "print('Hello from Claude Bridge!')",
                    "x = 2 + 2", 
                    "print(f'Result: {x}')",
                ]
                
                for cmd in commands:
                    print(f"  📝 Sending: {cmd}")
                    send_success = controller.send_input(cmd)
                    print(f"  📊 Sent: {send_success}")
                    await asyncio.sleep(0.2)
                
                # Wait for output
                await asyncio.sleep(1.0)
                
                print(f"  📊 Still running: {controller.is_running()}")
            
            # Terminate
            controller.terminate_process()
            print("  ✅ Process terminated")
            
        return success
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_session_with_process():
    """Test session manager with real process"""
    print("\n📋 Testing Session Manager with Real Process...")
    
    try:
        from src.claude_bridge.core.session_manager import SessionManager
        from src.claude_bridge.utils.config import Config, DiscordConfig, ClaudeCodeConfig, SessionConfig, LoggingConfig
        
        # Create config with Python as the command
        config = Config(
            discord=DiscordConfig("test", 123, 456),
            claude_code=ClaudeCodeConfig("python3", "/tmp", 30),
            session=SessionConfig(300, 1900, 100, 60),
            logging=LoggingConfig("INFO", "test.log", "10MB", 3)
        )
        
        session_manager = SessionManager(config)
        await session_manager.start()
        
        print("  📝 Creating session...")
        session = await session_manager.create_session("/tmp")
        
        if session:
            print(f"  ✅ Session created: {session.id}")
            print(f"  📊 Session active: {session.is_active()}")
            
            if session.is_active():
                # Send commands
                await asyncio.sleep(0.5)  # Let process initialize
                
                commands = ["print('Session test')", "2+2"]
                for cmd in commands:
                    print(f"  📝 Sending command: {cmd}")
                    success = await session_manager.send_command(session.id, cmd)
                    print(f"  📊 Command sent: {success}")
                    await asyncio.sleep(0.2)
                
                print(f"  📊 Command history: {len(session.command_history)}")
                print(f"  📊 Commands: {session.command_history}")
            
            # Cleanup
            await session_manager.terminate_session(session.id)
            print("  ✅ Session terminated")
        
        await session_manager.stop()
        return True
        
    except Exception as e:
        print(f"  ❌ Session manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_output_capture():
    """Test output capturing"""
    print("\n📡 Testing Output Capture...")
    
    try:
        from src.claude_bridge.process_control.process_controller import ProcessController
        
        controller = ProcessController(command="python3", working_directory="/tmp")
        
        # Capture output
        outputs = []
        def capture_output(output):
            outputs.append(output)
            print(f"  📥 Captured: {output.strip()}")
        
        controller.set_output_callback(capture_output)
        
        print("  📝 Starting process with output capture...")
        success = controller.start_process("OUTPUT_TEST")
        
        if success:
            await asyncio.sleep(0.5)
            
            if controller.is_running():
                # Send commands that produce output
                controller.send_input("print('Test output capture')")
                await asyncio.sleep(0.5)
                
                controller.send_input("for i in range(3): print(f'Line {i}')")
                await asyncio.sleep(0.5)
                
                print(f"  📊 Captured {len(outputs)} output lines")
            
            controller.terminate_process()
        
        return len(outputs) > 0
        
    except Exception as e:
        print(f"  ❌ Output capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run real functionality tests"""
    print("🚀 Claude Bridge Real Functionality Test")
    print("=" * 50)
    
    tests = [
        ("Python Process", test_with_python_process),
        ("Session Manager", test_session_with_process), 
        ("Output Capture", test_output_capture),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
            
        except Exception as e:
            print(f"❌ {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\n" + "=" * 50)
    print(f"🏁 Real Test Results: {passed}/{total}")
    
    if passed == total:
        print("🎉 System is actually working with real processes!")
    else:
        print(f"⚠️ {total - passed} tests failed - need investigation")

if __name__ == "__main__":
    asyncio.run(main())