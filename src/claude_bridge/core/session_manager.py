"""
Session Manager for Claude Bridge

Manages session lifecycle, pairing, and coordination between terminal and Discord interfaces.
"""

import asyncio
import random
import string
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable
from pathlib import Path

from .session import Session
from ..process_control.process_controller import ProcessController
from ..utils.config import Config
from ..utils.logging_setup import get_logger

logger = get_logger('session_manager')


class SessionManager:
    """Manages Claude Code sessions and their lifecycle"""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks for session events
        self.session_created_callback: Optional[Callable[[Session], None]] = None
        self.session_terminated_callback: Optional[Callable[[Session], None]] = None
        self.output_callback: Optional[Callable[[str, str], None]] = None  # (session_id, output)
        
    async def start(self):
        """Start the session manager"""
        logger.info("Starting Session Manager")
        self._running = True
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
    async def stop(self):
        """Stop the session manager and cleanup all sessions"""
        logger.info("Stopping Session Manager")
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Terminate all active sessions
        with self._lock:
            session_ids = list(self.sessions.keys())
        
        for session_id in session_ids:
            await self.terminate_session(session_id)
    
    def generate_session_id(self) -> str:
        """Generate a unique 6-character session ID"""
        while True:
            # Generate 6-character alphanumeric ID
            session_id = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=6
            ))
            
            # Ensure uniqueness
            if session_id not in self.sessions:
                return session_id
    
    async def create_session(self, working_directory: Optional[str] = None) -> Optional[Session]:
        """Create a new Claude Code session"""
        session_id = self.generate_session_id()
        
        # Use configured working directory if not specified
        if working_directory is None:
            working_directory = self.config.claude_code.working_directory
        
        logger.info(f"Creating new session {session_id} in {working_directory}")
        
        # Create session object
        session = Session(
            id=session_id,
            working_directory=working_directory
        )
        
        # Create process controller
        process_controller = ProcessController(
            command=self.config.claude_code.command,
            working_directory=working_directory
        )
        
        # Set up output callbacks
        process_controller.set_output_callback(
            lambda output: self._handle_process_output(session_id, output)
        )
        process_controller.set_error_callback(
            lambda error: self._handle_process_error(session_id, error)
        )
        
        # Start Claude Code process
        if not process_controller.start_process(session_id):
            logger.error(f"Failed to start Claude Code process for session {session_id}")
            return None
        
        # Store the process in the session
        session.claude_process = process_controller.process
        session.status = "active"
        
        # Store session with its process controller
        with self._lock:
            self.sessions[session_id] = session
            # Store process controller for later use
            setattr(session, '_process_controller', process_controller)
        
        logger.info(f"Session {session_id} created successfully")
        
        # Notify callback
        if self.session_created_callback:
            try:
                self.session_created_callback(session)
            except Exception as e:
                logger.error(f"Error in session created callback: {e}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        with self._lock:
            return self.sessions.get(session_id)
    
    def get_all_sessions(self) -> List[Session]:
        """Get all sessions"""
        with self._lock:
            return list(self.sessions.values())
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions"""
        with self._lock:
            return [s for s in self.sessions.values() if s.is_active()]
    
    async def connect_discord_channel(self, session_id: str, channel) -> bool:
        """Connect a Discord channel to a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for Discord connection")
            return False
        
        if not session.is_active():
            logger.warning(f"Session {session_id} is not active")
            return False
        
        session.discord_channel = channel
        session.update_activity()
        
        logger.info(f"Discord channel connected to session {session_id}")
        return True
    
    async def disconnect_discord_channel(self, session_id: str) -> bool:
        """Disconnect Discord channel from a session"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.discord_channel = None
        session.update_activity()
        
        logger.info(f"Discord channel disconnected from session {session_id}")
        return True
    
    async def send_command(self, session_id: str, command: str) -> bool:
        """Send a command to a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return False
        
        if not session.is_active():
            logger.warning(f"Session {session_id} is not active")
            return False
        
        # Get process controller
        process_controller = getattr(session, '_process_controller', None)
        if not process_controller:
            logger.error(f"Process controller not found for session {session_id}")
            return False
        
        # Send command
        success = process_controller.send_input(command)
        if success:
            session.add_command(command)
            logger.debug(f"Command sent to session {session_id}: {command}")
        else:
            logger.error(f"Failed to send command to session {session_id}")
        
        return success
    
    async def terminate_session(self, session_id: str) -> bool:
        """Terminate a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for termination")
            return False
        
        logger.info(f"Terminating session {session_id}")
        
        # Get process controller and terminate process
        process_controller = getattr(session, '_process_controller', None)
        if process_controller:
            process_controller.terminate_process()
        
        # Mark session as terminated
        session.terminate()
        
        # Remove from active sessions
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
        
        logger.info(f"Session {session_id} terminated")
        
        # Notify callback
        if self.session_terminated_callback:
            try:
                self.session_terminated_callback(session)
            except Exception as e:
                logger.error(f"Error in session terminated callback: {e}")
        
        return True
    
    async def restart_session(self, session_id: str) -> bool:
        """Restart a session"""
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for restart")
            return False
        
        logger.info(f"Restarting session {session_id}")
        
        # Get process controller
        process_controller = getattr(session, '_process_controller', None)
        if not process_controller:
            logger.error(f"Process controller not found for session {session_id}")
            return False
        
        # Restart process
        if process_controller.restart_process(session_id):
            session.claude_process = process_controller.process
            session.status = "active"
            session.update_activity()
            logger.info(f"Session {session_id} restarted successfully")
            return True
        else:
            logger.error(f"Failed to restart session {session_id}")
            session.status = "terminated"
            return False
    
    def _handle_process_output(self, session_id: str, output: str):
        """Handle output from Claude Code process"""
        session = self.get_session(session_id)
        if session:
            session.add_output(output)
            logger.debug(f"Output from session {session_id}: {output}")
            
            # Notify callback
            if self.output_callback:
                try:
                    asyncio.create_task(
                        self._async_output_callback(session_id, output)
                    )
                except Exception as e:
                    logger.error(f"Error creating output callback task: {e}")
    
    async def _async_output_callback(self, session_id: str, output: str):
        """Async wrapper for output callback"""
        if self.output_callback:
            try:
                await self.output_callback(session_id, output)
            except Exception as e:
                logger.error(f"Error in output callback: {e}")
    
    def _handle_process_error(self, session_id: str, error: str):
        """Handle error from Claude Code process"""
        session = self.get_session(session_id)
        if session:
            session.add_output(f"ERROR: {error}")
            logger.warning(f"Error from session {session_id}: {error}")
            
            # Also send to output callback
            self._handle_process_output(session_id, f"ERROR: {error}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(self.config.session.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_session_ids = []
        
        with self._lock:
            for session_id, session in self.sessions.items():
                if session.is_expired(self.config.session.timeout):
                    expired_session_ids.append(session_id)
        
        for session_id in expired_session_ids:
            logger.info(f"Cleaning up expired session {session_id}")
            await self.terminate_session(session_id)
    
    def get_session_stats(self) -> dict:
        """Get session statistics"""
        with self._lock:
            total_sessions = len(self.sessions)
            active_sessions = len([s for s in self.sessions.values() if s.is_active()])
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'inactive_sessions': total_sessions - active_sessions,
                'session_ids': list(self.sessions.keys())
            }
    
    def set_session_created_callback(self, callback: Callable[[Session], None]):
        """Set callback for session creation events"""
        self.session_created_callback = callback
    
    def set_session_terminated_callback(self, callback: Callable[[Session], None]):
        """Set callback for session termination events"""
        self.session_terminated_callback = callback
    
    def set_output_callback(self, callback: Callable[[str, str], None]):
        """Set callback for session output events"""
        self.output_callback = callback