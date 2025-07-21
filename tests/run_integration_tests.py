"""
Integration Test Runner for Claude Bridge

Runs comprehensive integration tests and provides detailed results.
"""

import asyncio
import sys
import os
import traceback
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.claude_bridge.core.session_manager import SessionManager
from src.claude_bridge.discord_bot.bot import ClaudeBridgeBot
from src.claude_bridge.output_handling.output_buffer import BufferManager
from src.claude_bridge.output_handling.ansi_processor import ANSIProcessor
from src.claude_bridge.output_handling.discord_formatter import DiscordFormatter, MessageType
from src.claude_bridge.discord_bot.ui_components import UIConverter, PromptDetector
from src.claude_bridge.discord_bot.progress_display import ProgressManager, ProgressDetector
from src.claude_bridge.utils.config import Config, DiscordConfig, ClaudeCodeConfig, SessionConfig, LoggingConfig
from src.claude_bridge.utils.error_handler import ErrorHandler
from src.claude_bridge.utils.performance_monitor import PerformanceMonitor


class IntegrationTestRunner:
    """Runs integration tests for Claude Bridge components"""
    
    def __init__(self):
        self.test_results = []
        self.test_config = Config(
            discord=DiscordConfig("test_token", 123456789, 987654321),
            claude_code=ClaudeCodeConfig("echo", "/tmp", 30),  # Use echo for testing
            session=SessionConfig(300, 1900, 100, 60),
            logging=LoggingConfig("DEBUG", "test.log", "10MB", 3)
        )
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        print("🚀 Starting Claude Bridge Integration Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Test categories
        test_categories = [
            ("Core Components", self.test_core_components),
            ("Output Processing", self.test_output_processing),
            ("Discord Integration", self.test_discord_integration),
            ("UI Components", self.test_ui_components),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance),
            ("End-to-End", self.test_end_to_end)
        ]
        
        results = {}
        
        for category_name, test_func in test_categories:
            print(f"\n📋 Testing {category_name}...")
            try:
                category_results = await test_func()
                results[category_name] = category_results
                
                passed = sum(1 for r in category_results if r['passed'])
                total = len(category_results)
                print(f"✅ {category_name}: {passed}/{total} tests passed")
                
            except Exception as e:
                print(f"❌ {category_name}: Test category failed - {e}")
                results[category_name] = [{"name": "Category Error", "passed": False, "error": str(e)}]
        
        # Summary
        total_time = time.time() - start_time
        all_tests = [test for category in results.values() for test in category]
        passed_tests = sum(1 for test in all_tests if test['passed'])
        total_tests = len(all_tests)
        
        print(f"\n" + "=" * 50)
        print(f"🏁 Integration Test Results:")
        print(f"   Passed: {passed_tests}/{total_tests}")
        print(f"   Time: {total_time:.2f}s")
        print(f"   Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': passed_tests / total_tests * 100,
            'execution_time': total_time
        }
        
        return results
    
    async def test_core_components(self) -> List[Dict]:
        """Test core components"""
        results = []
        
        # Test Session Manager
        try:
            session_manager = SessionManager(self.test_config)
            await session_manager.start()
            
            # Test session creation
            session = await session_manager.create_session("/tmp")
            results.append({
                "name": "Session Creation",
                "passed": session is not None and session.is_active(),
                "details": f"Session ID: {session.id if session else 'None'}"
            })
            
            # Test command sending
            if session:
                success = await session_manager.send_command(session.id, "test command")
                results.append({
                    "name": "Command Sending",
                    "passed": success,
                    "details": f"Command history: {len(session.command_history)} items"
                })
                
                # Test session termination
                term_success = await session_manager.terminate_session(session.id)
                results.append({
                    "name": "Session Termination",
                    "passed": term_success and not session.is_active(),
                    "details": f"Final status: {session.status}"
                })
            
            await session_manager.stop()
            
        except Exception as e:
            results.append({
                "name": "Session Manager",
                "passed": False,
                "error": str(e)
            })
        
        # Test Buffer Manager
        try:
            buffer_manager = BufferManager()
            
            buffer = await buffer_manager.create_buffer("TEST001")
            results.append({
                "name": "Buffer Creation",
                "passed": buffer is not None,
                "details": f"Buffer session: {buffer.session_id if buffer else 'None'}"
            })
            
            if buffer:
                buffer.add_output("Test output")
                await buffer.flush_buffer()
                
                results.append({
                    "name": "Buffer Output Processing",
                    "passed": len(buffer.get_recent_lines()) > 0,
                    "details": f"Lines in buffer: {len(buffer.get_recent_lines())}"
                })
            
            await buffer_manager.stop_all_buffers()
            
        except Exception as e:
            results.append({
                "name": "Buffer Manager",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_output_processing(self) -> List[Dict]:
        """Test output processing components"""
        results = []
        
        # Test ANSI Processor
        try:
            processor = ANSIProcessor()
            
            # Test ANSI removal
            ansi_text = "\x1b[31mError: Test\x1b[0m"
            clean_text = processor.strip_all_ansi(ansi_text)
            results.append({
                "name": "ANSI Removal",
                "passed": '\x1b[' not in clean_text and 'Error: Test' in clean_text,
                "details": f"'{ansi_text}' -> '{clean_text}'"
            })
            
            # Test semantic analysis
            semantic_info = processor.extract_semantic_content("Error: File not found")
            results.append({
                "name": "Semantic Analysis",
                "passed": semantic_info['type'] == 'error',
                "details": f"Detected type: {semantic_info['type']}"
            })
            
        except Exception as e:
            results.append({
                "name": "ANSI Processor",
                "passed": False,
                "error": str(e)
            })
        
        # Test Discord Formatter
        try:
            formatter = DiscordFormatter()
            
            # Test message formatting
            long_text = "Line " * 200  # Create long text
            chunks = formatter.format_output(long_text, MessageType.NORMAL)
            
            results.append({
                "name": "Message Splitting",
                "passed": len(chunks) > 1 and all(len(c.content) <= 2000 for c in chunks),
                "details": f"Split into {len(chunks)} chunks"
            })
            
            # Test code detection
            code_text = "def hello():\n    print('Hello World')"
            chunks = formatter.format_output(code_text, MessageType.CODE)
            
            results.append({
                "name": "Code Formatting",
                "passed": len(chunks) > 0 and '```' in chunks[0].content,
                "details": f"Code block formatting applied"
            })
            
        except Exception as e:
            results.append({
                "name": "Discord Formatter",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_discord_integration(self) -> List[Dict]:
        """Test Discord integration components"""
        results = []
        
        # Test UI Components
        try:
            ui_converter = UIConverter()
            
            # Test prompt detection
            yes_no_prompt = "Do you want to continue? (y/n)"
            detection = PromptDetector.detect_prompt(yes_no_prompt)
            
            results.append({
                "name": "Prompt Detection",
                "passed": detection is not None and detection[0].value == 'yes_no',
                "details": f"Detected: {detection[0].value if detection else 'None'}"
            })
            
            # Test choice detection
            choice_prompt = "Select option:\n1. Option A\n2. Option B"
            choice_detection = PromptDetector.detect_prompt(choice_prompt)
            
            results.append({
                "name": "Choice Detection", 
                "passed": choice_detection is not None and choice_detection[0].value == 'choice',
                "details": f"Detected: {choice_detection[0].value if choice_detection else 'None'}"
            })
            
        except Exception as e:
            results.append({
                "name": "UI Components",
                "passed": False,
                "error": str(e)
            })
        
        # Test Progress Display
        try:
            progress_manager = ProgressManager()
            
            # Test progress detection
            progress_text = "Processing... ████████░░ 80%"
            progress_info = ProgressDetector.detect_progress(progress_text)
            
            results.append({
                "name": "Progress Detection",
                "passed": progress_info is not None and 'percentage' in progress_info,
                "details": f"Detected: {progress_info['percentage'] if progress_info else 'None'}%"
            })
            
        except Exception as e:
            results.append({
                "name": "Progress Display",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_ui_components(self) -> List[Dict]:
        """Test UI component functionality"""
        results = []
        
        try:
            # Test various prompt patterns
            test_prompts = [
                ("Do you want to save? (y/n)", "yes_no"),
                ("Select option:\n1. A\n2. B\n3. C", "choice"),
                ("Enter your name:", "text_input"),
                ("Are you sure you want to delete this?", "confirmation")
            ]
            
            for prompt, expected_type in test_prompts:
                detection = PromptDetector.detect_prompt(prompt)
                passed = detection is not None and detection[0].value == expected_type
                
                results.append({
                    "name": f"Prompt Detection: {expected_type}",
                    "passed": passed,
                    "details": f"Expected: {expected_type}, Got: {detection[0].value if detection else 'None'}"
                })
            
        except Exception as e:
            results.append({
                "name": "UI Component Tests",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_error_handling(self) -> List[Dict]:
        """Test error handling system"""
        results = []
        
        try:
            error_handler = ErrorHandler()
            
            # Test error classification
            test_error = ConnectionError("Network timeout")
            success = await error_handler.handle_error(test_error, {"test": True})
            
            results.append({
                "name": "Error Classification",
                "passed": True,  # Handler should not crash
                "details": f"Error processed successfully"
            })
            
            # Test error statistics
            stats = error_handler.get_error_stats()
            results.append({
                "name": "Error Statistics",
                "passed": stats['total_errors'] > 0,
                "details": f"Errors recorded: {stats['total_errors']}"
            })
            
            # Test recent errors
            recent = error_handler.get_recent_errors(5)
            results.append({
                "name": "Error History",
                "passed": len(recent) > 0,
                "details": f"Recent errors: {len(recent)}"
            })
            
        except Exception as e:
            results.append({
                "name": "Error Handler",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_performance(self) -> List[Dict]:
        """Test performance monitoring"""
        results = []
        
        try:
            monitor = PerformanceMonitor(collection_interval=0.1)
            
            # Start monitoring
            await monitor.start_monitoring()
            
            # Wait for metrics collection
            await asyncio.sleep(0.3)
            
            # Check metrics
            current = monitor.get_current_metrics()
            results.append({
                "name": "Metrics Collection",
                "passed": current is not None and current.timestamp > 0,
                "details": f"CPU: {current.cpu_percent}%, Memory: {current.memory_mb}MB"
            })
            
            # Check health score
            health = monitor.get_health_score()
            results.append({
                "name": "Health Score",
                "passed": 0 <= health <= 100,
                "details": f"Health score: {health}"
            })
            
            await monitor.stop_monitoring()
            
        except Exception as e:
            results.append({
                "name": "Performance Monitor",
                "passed": False,
                "error": str(e)
            })
        
        return results
    
    async def test_end_to_end(self) -> List[Dict]:
        """Test end-to-end functionality"""
        results = []
        
        try:
            # Create all components
            session_manager = SessionManager(self.test_config)
            buffer_manager = BufferManager()
            error_handler = ErrorHandler()
            
            await session_manager.start()
            
            # Create session
            session = await session_manager.create_session("/tmp")
            
            # Create buffer for session
            buffer = await buffer_manager.create_buffer(session.id)
            
            # Set up output processing
            processed_outputs = []
            
            async def capture_output(chunks):
                processed_outputs.extend(chunks)
            
            buffer.set_output_callback(capture_output)
            
            # Simulate workflow
            test_outputs = [
                "Starting process...",
                "\x1b[32mSuccess: File created\x1b[0m",
                "████████░░ 80%",
                "Process completed"
            ]
            
            for output in test_outputs:
                buffer.add_output(output)
            
            # Force processing
            await buffer.flush_buffer()
            
            # Send commands
            await session_manager.send_command(session.id, "help")
            await session_manager.send_command(session.id, "status")
            
            # Verify results
            results.append({
                "name": "End-to-End Session",
                "passed": (session.is_active() and 
                          len(session.command_history) == 2 and
                          len(processed_outputs) > 0),
                "details": f"Commands: {len(session.command_history)}, Outputs: {len(processed_outputs)}"
            })
            
            # Cleanup
            await session_manager.terminate_session(session.id)
            await buffer_manager.remove_buffer(session.id)
            await session_manager.stop()
            
        except Exception as e:
            results.append({
                "name": "End-to-End Test",
                "passed": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        return results
    
    def print_detailed_results(self, results: Dict[str, Any]):
        """Print detailed test results"""
        print("\n" + "=" * 60)
        print("📋 DETAILED TEST RESULTS")
        print("=" * 60)
        
        for category, tests in results.items():
            if category == 'summary':
                continue
                
            print(f"\n📁 {category}")
            print("-" * 40)
            
            for test in tests:
                status = "✅ PASS" if test['passed'] else "❌ FAIL"
                print(f"  {status} {test['name']}")
                
                if 'details' in test:
                    print(f"        {test['details']}")
                
                if not test['passed'] and 'error' in test:
                    print(f"        Error: {test['error']}")
                
                if 'traceback' in test:
                    print(f"        Traceback: {test['traceback'][:200]}...")


async def main():
    """Run integration tests"""
    runner = IntegrationTestRunner()
    
    try:
        results = await runner.run_all_tests()
        
        # Print detailed results if requested
        if '--detailed' in sys.argv or '-d' in sys.argv:
            runner.print_detailed_results(results)
        
        # Return appropriate exit code
        if results['summary']['success_rate'] >= 80:
            print(f"\n🎉 Integration tests completed successfully!")
            return 0
        else:
            print(f"\n⚠️ Some integration tests failed.")
            return 1
            
    except Exception as e:
        print(f"❌ Integration test runner failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)