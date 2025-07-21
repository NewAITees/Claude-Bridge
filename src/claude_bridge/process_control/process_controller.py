"""
Claude Code Process Controller

Manages Claude Code process lifecycle, input/output handling, and monitoring.
"""

import asyncio
import os
import subprocess
import signal
import threading
from typing import Optional, Callable, Any
from pathlib import Path

from ..utils.logging_setup import get_logger

logger = get_logger('process_controller')


class ProcessController:
    """Controls Claude Code process execution and I/O"""
    
    def __init__(self, command: str = "claude-code", working_directory: str = "/workspace"):
        self.command = command
        self.working_directory = Path(working_directory)
        self.process: Optional[subprocess.Popen] = None
        self.output_callback: Optional[Callable[[str], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        self._output_thread: Optional[threading.Thread] = None
        self._error_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
    def start_process(self, session_id: str) -> bool:
        """Start Claude Code process"""
        try:
            # Ensure working directory exists
            self.working_directory.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Starting Claude Code process for session {session_id}")
            logger.info(f"Command: {self.command}")
            logger.info(f"Working directory: {self.working_directory}")
            
            # Start Claude Code process
            self.process = subprocess.Popen(
                [self.command],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.working_directory,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                env=dict(os.environ, PYTHONUNBUFFERED="1")
            )
            
            # Start output monitoring threads
            self._start_output_monitoring()
            
            logger.info(f"Claude Code process started with PID {self.process.pid}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Claude Code command not found: {self.command}")
            return False
        except Exception as e:
            logger.error(f"Failed to start Claude Code process: {e}")
            return False
    
    def _start_output_monitoring(self):
        """Start threads to monitor stdout and stderr"""
        if not self.process:
            return
            
        self._stop_event.clear()
        
        # Start stdout monitoring thread
        self._output_thread = threading.Thread(
            target=self._monitor_stdout,
            daemon=True
        )
        self._output_thread.start()
        
        # Start stderr monitoring thread
        self._error_thread = threading.Thread(
            target=self._monitor_stderr,
            daemon=True
        )
        self._error_thread.start()
    
    def _monitor_stdout(self):
        """Monitor stdout in a separate thread"""
        if not self.process or not self.process.stdout:
            return
            
        try:
            while not self._stop_event.is_set() and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    line = line.rstrip('\n\r')
                    logger.debug(f"Claude stdout: {line}")
                    if self.output_callback:
                        self.output_callback(line)
                else:
                    # No output, sleep briefly
                    self._stop_event.wait(0.1)
        except Exception as e:
            logger.error(f"Error monitoring stdout: {e}")
    
    def _monitor_stderr(self):
        """Monitor stderr in a separate thread"""
        if not self.process or not self.process.stderr:
            return
            
        try:
            while not self._stop_event.is_set() and self.process.poll() is None:
                line = self.process.stderr.readline()
                if line:
                    line = line.rstrip('\n\r')
                    logger.debug(f"Claude stderr: {line}")
                    if self.error_callback:
                        self.error_callback(line)
                else:
                    # No error output, sleep briefly
                    self._stop_event.wait(0.1)
        except Exception as e:
            logger.error(f"Error monitoring stderr: {e}")
    
    def send_input(self, command: str) -> bool:
        """Send input to Claude Code process"""
        if not self.process or not self.process.stdin:
            logger.warning("Cannot send input: process not running")
            return False
        
        try:
            # Ensure command ends with newline
            if not command.endswith('\n'):
                command += '\n'
            
            logger.debug(f"Sending input to Claude: {command.rstrip()}")
            self.process.stdin.write(command)
            self.process.stdin.flush()
            return True
            
        except BrokenPipeError:
            logger.error("Cannot send input: process stdin is closed")
            return False
        except Exception as e:
            logger.error(f"Error sending input to process: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if Claude Code process is running"""
        return self.process is not None and self.process.poll() is None
    
    def get_process_info(self) -> dict:
        """Get process information"""
        if not self.process:
            return {"status": "not_started", "pid": None}
        
        poll_result = self.process.poll()
        if poll_result is None:
            return {"status": "running", "pid": self.process.pid}
        else:
            return {"status": "terminated", "pid": self.process.pid, "exit_code": poll_result}
    
    def terminate_process(self) -> bool:
        """Gracefully terminate Claude Code process"""
        if not self.process:
            return True
        
        try:
            logger.info(f"Terminating Claude Code process (PID: {self.process.pid})")
            
            # Stop output monitoring
            self._stop_event.set()
            
            # Send SIGTERM first
            self.process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.process.wait(timeout=5)
                logger.info("Claude Code process terminated gracefully")
                return True
            except subprocess.TimeoutExpired:
                logger.warning("Claude Code process did not terminate gracefully, forcing kill")
                self.process.kill()
                self.process.wait()
                logger.info("Claude Code process killed")
                return True
                
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
            return False
        finally:
            self.process = None
            
            # Wait for monitoring threads to finish
            if self._output_thread and self._output_thread.is_alive():
                self._output_thread.join(timeout=1)
            if self._error_thread and self._error_thread.is_alive():
                self._error_thread.join(timeout=1)
    
    def restart_process(self, session_id: str) -> bool:
        """Restart Claude Code process"""
        logger.info(f"Restarting Claude Code process for session {session_id}")
        
        # Terminate existing process
        self.terminate_process()
        
        # Start new process
        return self.start_process(session_id)
    
    def set_output_callback(self, callback: Callable[[str], None]):
        """Set callback function for stdout"""
        self.output_callback = callback
    
    def set_error_callback(self, callback: Callable[[str], None]):
        """Set callback function for stderr"""
        self.error_callback = callback
    
    def __del__(self):
        """Cleanup on deletion"""
        self.terminate_process()