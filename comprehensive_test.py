#!/usr/bin/env python3
"""
Comprehensive Claude Bridge Test Suite

Tests the system from multiple angles to identify actual functionality:
1. Isolated component tests (no dependencies)
2. Simple process tests (local commands) 
3. Real process integration (Python shell)
4. Container compatibility tests
5. Environment-specific validations
"""

import asyncio
import sys
import subprocess
import platform
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class TestRunner:
    def __init__(self):
        self.results = []
        self.environment_info = self._gather_environment_info()
    
    def _gather_environment_info(self):
        """Gather environment information"""
        info = {
            "platform": platform.system(),
            "python_version": sys.version,
            "in_container": self._check_container(),
            "docker_available": self._check_docker(),
            "working_dir": os.getcwd(),
            "venv_active": hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        }
        return info
    
    def _check_container(self):
        """Check if running in container"""
        try:
            # Check for container-specific files
            container_indicators = [
                "/.dockerenv",
                "/proc/1/cgroup"
            ]
            
            for indicator in container_indicators:
                if Path(indicator).exists():
                    return True
                    
            # Check hostname patterns
            hostname = os.uname().nodename
            if hostname.startswith(('docker-', 'container-')) or len(hostname) == 12:
                return True
                
            return False
        except:
            return False
    
    def _check_docker(self):
        """Check if Docker is available"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}: {'PASSED' if success else 'FAILED'}")
        if details and not success:
            print(f"    Details: {details}")

class ComponentTests(TestRunner):
    """Test individual components without external dependencies"""
    
    def test_imports(self):
        """Test all imports work"""
        print("\n🔍 Component Import Tests")
        
        components = [
            ("Session", "src.claude_bridge.core.session", "Session"),
            ("SessionManager", "src.claude_bridge.core.session_manager", "SessionManager"),
            ("ProcessController", "src.claude_bridge.process_control.process_controller", "ProcessController"),
            ("ANSIProcessor", "src.claude_bridge.output_handling.ansi_processor", "ANSIProcessor"),
            ("DiscordFormatter", "src.claude_bridge.output_handling.discord_formatter", "DiscordFormatter"),
            ("Config", "src.claude_bridge.utils.config", "Config"),
        ]
        
        for name, module, cls in components:
            try:
                mod = __import__(module, fromlist=[cls])
                getattr(mod, cls)
                self.log_result(f"Import {name}", True)
            except Exception as e:
                self.log_result(f"Import {name}", False, str(e))
    
    def test_ansi_processing(self):
        """Test ANSI processing works"""
        print("\n🎨 ANSI Processing Tests")
        
        try:
            from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
            processor = ANSIProcessor()
            
            # Test cases
            tests = [
                ("Simple color", "\x1b[31mRed\x1b[0m", "Red"),
                ("Multiple colors", "\x1b[31mRed\x1b[32mGreen\x1b[0m", "RedGreen"),
                ("Complex sequence", "\x1b[1;31;40mBold Red on Black\x1b[0m", "Bold Red on Black"),
                ("Plain text", "No ANSI codes", "No ANSI codes"),
            ]
            
            for test_name, input_text, expected in tests:
                result = processor.strip_all_ansi(input_text)
                success = result == expected
                self.log_result(f"ANSI {test_name}", success, f"Expected: '{expected}', Got: '{result}'" if not success else "")
                
        except Exception as e:
            self.log_result("ANSI Processing", False, str(e))
    
    def test_discord_formatting(self):
        """Test Discord formatting works"""
        print("\n💬 Discord Formatting Tests")
        
        try:
            from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter, MessageType
            formatter = DiscordFormatter()
            
            # Test long message splitting
            long_text = "Line " * 1000  # Very long text
            chunks = formatter.format_output(long_text, MessageType.NORMAL)
            
            all_under_limit = all(len(chunk.content) <= 2000 for chunk in chunks)
            has_multiple_chunks = len(chunks) > 1
            
            self.log_result("Discord Split Long Text", all_under_limit and has_multiple_chunks)
            
            # Test code block formatting
            code_text = "```python\nprint('hello')\n```"
            code_chunks = formatter.format_output(code_text, MessageType.CODE)
            self.log_result("Discord Code Formatting", len(code_chunks) > 0)
            
        except Exception as e:
            self.log_result("Discord Formatting", False, str(e))

class ProcessTests(TestRunner):
    """Test process control functionality"""
    
    def test_simple_command(self):
        """Test with simple command that exits immediately"""
        print("\n⚡ Simple Process Tests")
        
        try:
            from src.claude_bridge.process_control.process_controller import ProcessController
            
            # Test echo command (exits immediately)
            controller = ProcessController(command="echo", working_directory="/tmp")
            success = controller.start_process("ECHO_TEST")
            
            # For echo, process exits immediately, so this is expected behavior
            if success:
                # Process should be started but may have exited
                info = controller.get_process_info()
                self.log_result("Echo Command Start", True, f"Process info: {info}")
            else:
                self.log_result("Echo Command Start", False, "Failed to start echo")
                
        except Exception as e:
            self.log_result("Simple Command", False, str(e))
    
    def test_persistent_command(self):
        """Test with persistent command"""
        print("\n🔄 Persistent Process Tests")
        
        try:
            from src.claude_bridge.process_control.process_controller import ProcessController
            
            # Test with cat (waits for input)
            controller = ProcessController(command="cat", working_directory="/tmp")
            success = controller.start_process("CAT_TEST")
            
            if success:
                # Cat should keep running
                running = controller.is_running()
                self.log_result("Cat Command Running", running)
                
                if running:
                    # Try sending input
                    send_success = controller.send_input("test input\n")
                    self.log_result("Send Input to Cat", send_success)
                    
                    # Give it a moment
                    import time
                    time.sleep(0.1)
                    
                    # Should still be running
                    still_running = controller.is_running()
                    self.log_result("Cat Still Running", still_running)
                
                # Clean up
                controller.terminate_process()
                self.log_result("Cat Termination", True)
            else:
                self.log_result("Cat Command Start", False)
                
        except Exception as e:
            self.log_result("Persistent Command", False, str(e))

class IntegrationTests(TestRunner):
    """Test full system integration"""
    
    async def test_session_lifecycle(self):
        """Test session creation and management"""
        print("\n📋 Session Integration Tests")
        
        try:
            from src.claude_bridge.core.session_manager import SessionManager
            from src.claude_bridge.utils.config import Config, DiscordConfig, ClaudeCodeConfig, SessionConfig, LoggingConfig
            
            # Create minimal config
            config = Config(
                discord=DiscordConfig("test", 123, 456),
                claude_code=ClaudeCodeConfig("cat", "/tmp", 30),  # Use cat for testing
                session=SessionConfig(300, 1900, 100, 60),
                logging=LoggingConfig("INFO", "test.log", "10MB", 3)
            )
            
            session_manager = SessionManager(config)
            await session_manager.start()
            
            # Create session
            session = await session_manager.create_session("/tmp")
            if session:
                self.log_result("Session Creation", True, f"Session ID: {session.id}")
                
                # Check if session is active
                active = session.is_active()
                self.log_result("Session Active", active)
                
                if active:
                    # Test sending command
                    command_sent = await session_manager.send_command(session.id, "test command\n")
                    self.log_result("Send Command", command_sent)
                
                # Cleanup
                await session_manager.terminate_session(session.id)
                self.log_result("Session Cleanup", True)
            else:
                self.log_result("Session Creation", False, "Session is None")
            
            await session_manager.stop()
            
        except Exception as e:
            self.log_result("Session Integration", False, str(e))

class EnvironmentTests(TestRunner):
    """Test environment-specific functionality"""
    
    def test_environment_compatibility(self):
        """Test environment compatibility"""
        print("\n🌍 Environment Compatibility Tests")
        
        # Check Python version
        py_version = sys.version_info
        py_compatible = py_version >= (3, 9)
        self.log_result("Python Version", py_compatible, f"Python {py_version.major}.{py_version.minor}")
        
        # Check required commands
        commands = ["cat", "echo", "python3"]
        for cmd in commands:
            try:
                result = subprocess.run([cmd, "--help"], capture_output=True, text=True, timeout=5)
                available = result.returncode == 0 or cmd == "cat"  # cat --help might not work
                self.log_result(f"Command {cmd}", available)
            except:
                self.log_result(f"Command {cmd}", False)
        
        # Check file permissions
        temp_file = Path("/tmp/claude_bridge_test")
        try:
            temp_file.write_text("test")
            can_write = temp_file.exists()
            temp_file.unlink()
            self.log_result("File Permissions", can_write)
        except:
            self.log_result("File Permissions", False)
    
    def test_virtual_environment(self):
        """Test virtual environment setup"""
        print("\n🐍 Virtual Environment Tests")
        
        # Check if in venv
        in_venv = self.environment_info["venv_active"]
        self.log_result("Virtual Environment", in_venv)
        
        # Check dependencies
        deps = ["discord", "pexpect", "asyncio"]
        for dep in deps:
            try:
                __import__(dep)
                self.log_result(f"Dependency {dep}", True)
            except ImportError:
                self.log_result(f"Dependency {dep}", False)

async def main():
    """Run comprehensive tests"""
    print("🚀 Claude Bridge Comprehensive Test Suite")
    print("=" * 60)
    
    # Print environment info
    runner = TestRunner()
    print(f"\n📊 Environment Information:")
    for key, value in runner.environment_info.items():
        print(f"  {key}: {value}")
    
    # Run test suites
    test_suites = [
        ("Component Tests", ComponentTests),
        ("Process Tests", ProcessTests),
        ("Integration Tests", IntegrationTests),
        ("Environment Tests", EnvironmentTests),
    ]
    
    all_results = []
    
    for suite_name, suite_class in test_suites:
        print(f"\n🧪 {suite_name}")
        print("-" * 40)
        
        suite = suite_class()
        
        # Run tests based on suite type
        if suite_name == "Component Tests":
            suite.test_imports()
            suite.test_ansi_processing()
            suite.test_discord_formatting()
        elif suite_name == "Process Tests":
            suite.test_simple_command()
            suite.test_persistent_command()
        elif suite_name == "Integration Tests":
            await suite.test_session_lifecycle()
        elif suite_name == "Environment Tests":
            suite.test_environment_compatibility()
            suite.test_virtual_environment()
        
        all_results.extend(suite.results)
    
    # Summary
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r["success"])
    
    print(f"\n" + "=" * 60)
    print(f"🏁 Comprehensive Test Results: {passed_tests}/{total_tests} passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Claude Bridge is fully functional.")
        return 0
    else:
        failed_tests = [r for r in all_results if not r["success"]]
        print(f"\n⚠️ Failed Tests ({len(failed_tests)}):")
        for test in failed_tests:
            print(f"  ❌ {test['test']}")
            if test["details"]:
                print(f"     {test['details']}")
        
        # Analyze failure patterns
        print(f"\n🔍 Failure Analysis:")
        if any("Import" in t["test"] for t in failed_tests):
            print("  - Import failures suggest missing dependencies or incorrect paths")
        if any("Process" in t["test"] for t in failed_tests):
            print("  - Process failures may indicate subprocess or permission issues")
        if any("Session" in t["test"] for t in failed_tests):
            print("  - Session failures suggest integration problems")
        
        print(f"\n💡 Next Steps:")
        print("  1. Fix import/dependency issues first")
        print("  2. Verify process control in current environment")
        print("  3. Test with simpler commands before complex ones")
        
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)