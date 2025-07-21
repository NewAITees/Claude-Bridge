"""
Comprehensive Error Handling System for Claude Bridge

Manages error detection, classification, recovery strategies, and user notifications.
"""

import asyncio
import traceback
import time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import discord
import subprocess

from .logging_setup import get_logger

logger = get_logger('error_handler')


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"           # Minor issues, can continue
    MEDIUM = "medium"     # Significant issues, may impact functionality  
    HIGH = "high"         # Major issues, requires attention
    CRITICAL = "critical" # System-breaking issues, immediate action required


class ErrorCategory(Enum):
    """Categories of errors"""
    PROCESS = "process"         # Claude Code process issues
    DISCORD = "discord"         # Discord API issues
    NETWORK = "network"         # Network connectivity issues
    CONFIGURATION = "config"    # Configuration problems
    PERMISSION = "permission"   # Permission/access issues
    RESOURCE = "resource"       # Resource exhaustion (memory, disk, etc.)
    USER_INPUT = "user_input"   # Invalid user input
    INTERNAL = "internal"       # Internal application errors


class RecoveryAction(Enum):
    """Possible recovery actions"""
    IGNORE = "ignore"
    RETRY = "retry"
    RESTART_PROCESS = "restart_process"
    RECONNECT_DISCORD = "reconnect_discord"
    RESET_SESSION = "reset_session"
    NOTIFY_USER = "notify_user"
    ESCALATE = "escalate"


@dataclass
class ErrorInfo:
    """Information about an error"""
    error: Exception
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    context: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    retry_count: int = 0
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            'error_type': type(self.error).__name__,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp,
            'session_id': self.session_id,
            'retry_count': self.retry_count,
            'traceback': traceback.format_exc() if self.error else None
        }


class ErrorDetector:
    """Detects and classifies various types of errors"""
    
    # Error patterns for classification
    PATTERNS = {
        ErrorCategory.PROCESS: [
            r'claude.*not found',
            r'command not found.*claude',
            r'process.*terminated unexpectedly',
            r'broken pipe',
            r'connection reset',
        ],
        
        ErrorCategory.DISCORD: [
            r'discord.*forbidden',
            r'discord.*not found',
            r'discord.*rate limited',
            r'webhook.*error',
            r'missing permissions',
        ],
        
        ErrorCategory.NETWORK: [
            r'connection.*refused',
            r'network.*unreachable',
            r'timeout',
            r'dns.*resolution.*failed',
            r'ssl.*error',
        ],
        
        ErrorCategory.CONFIGURATION: [
            r'config.*not found',
            r'invalid.*config',
            r'missing.*token',
            r'invalid.*credentials',
        ],
        
        ErrorCategory.PERMISSION: [
            r'permission.*denied',
            r'access.*denied',
            r'unauthorized',
            r'forbidden',
        ],
        
        ErrorCategory.RESOURCE: [
            r'out of memory',
            r'disk.*full',
            r'no space left',
            r'resource.*exhausted',
        ]
    }
    
    @classmethod
    def classify_error(cls, error: Exception, context: Dict = None) -> ErrorInfo:
        """Classify an error and determine its properties"""
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Default classification
        category = ErrorCategory.INTERNAL
        severity = ErrorSeverity.MEDIUM
        
        # Classify by exception type
        if isinstance(error, subprocess.SubprocessError):
            category = ErrorCategory.PROCESS
            severity = ErrorSeverity.HIGH
        elif isinstance(error, discord.errors.DiscordException):
            category = ErrorCategory.DISCORD
            severity = ErrorSeverity.MEDIUM
        elif isinstance(error, (ConnectionError, TimeoutError)):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
        elif isinstance(error, PermissionError):
            category = ErrorCategory.PERMISSION
            severity = ErrorSeverity.HIGH
        elif isinstance(error, (FileNotFoundError, KeyError)):
            category = ErrorCategory.CONFIGURATION
            severity = ErrorSeverity.HIGH
        elif isinstance(error, MemoryError):
            category = ErrorCategory.RESOURCE
            severity = ErrorSeverity.CRITICAL
        
        # Refine classification using patterns
        for cat, patterns in cls.PATTERNS.items():
            import re
            for pattern in patterns:
                if re.search(pattern, error_message, re.IGNORECASE):
                    category = cat
                    break
        
        # Determine severity based on category
        if category in [ErrorCategory.RESOURCE, ErrorCategory.PROCESS]:
            if 'critical' in error_message or 'fatal' in error_message:
                severity = ErrorSeverity.CRITICAL
            else:
                severity = ErrorSeverity.HIGH
        elif category == ErrorCategory.CONFIGURATION:
            severity = ErrorSeverity.HIGH
        elif category in [ErrorCategory.DISCORD, ErrorCategory.NETWORK]:
            severity = ErrorSeverity.MEDIUM
        elif category == ErrorCategory.USER_INPUT:
            severity = ErrorSeverity.LOW
        
        # Create error info
        return ErrorInfo(
            error=error,
            category=category,
            severity=severity,
            message=str(error),
            context=context or {},
            recovery_actions=cls._determine_recovery_actions(category, severity)
        )
    
    @classmethod
    def _determine_recovery_actions(cls, category: ErrorCategory, 
                                  severity: ErrorSeverity) -> List[RecoveryAction]:
        """Determine appropriate recovery actions"""
        actions = []
        
        # Always notify user for high/critical errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            actions.append(RecoveryAction.NOTIFY_USER)
        
        # Category-specific actions
        if category == ErrorCategory.PROCESS:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.RESTART_PROCESS])
        elif category == ErrorCategory.DISCORD:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.RECONNECT_DISCORD])
        elif category == ErrorCategory.NETWORK:
            actions.append(RecoveryAction.RETRY)
        elif category == ErrorCategory.CONFIGURATION:
            actions.append(RecoveryAction.ESCALATE)
        elif category == ErrorCategory.RESOURCE:
            actions.extend([RecoveryAction.RESET_SESSION, RecoveryAction.ESCALATE])
        elif category == ErrorCategory.USER_INPUT:
            actions.append(RecoveryAction.NOTIFY_USER)
        else:
            actions.append(RecoveryAction.RETRY)
        
        # Critical errors always escalate
        if severity == ErrorSeverity.CRITICAL:
            actions.append(RecoveryAction.ESCALATE)
        
        return actions


class ErrorRecovery:
    """Handles error recovery strategies"""
    
    def __init__(self):
        self.retry_limits = {
            ErrorCategory.PROCESS: 3,
            ErrorCategory.DISCORD: 5,
            ErrorCategory.NETWORK: 3,
            ErrorCategory.CONFIGURATION: 1,
            ErrorCategory.PERMISSION: 1,
            ErrorCategory.RESOURCE: 1,
            ErrorCategory.USER_INPUT: 0,
            ErrorCategory.INTERNAL: 2
        }
        
        self.retry_delays = {
            ErrorCategory.PROCESS: [1, 3, 5],
            ErrorCategory.DISCORD: [2, 5, 10, 20, 40],
            ErrorCategory.NETWORK: [1, 2, 5],
            ErrorCategory.CONFIGURATION: [0],
            ErrorCategory.PERMISSION: [0],
            ErrorCategory.RESOURCE: [0],
            ErrorCategory.USER_INPUT: [],
            ErrorCategory.INTERNAL: [1, 3]
        }
    
    def can_retry(self, error_info: ErrorInfo) -> bool:
        """Check if error can be retried"""
        limit = self.retry_limits.get(error_info.category, 0)
        return error_info.retry_count < limit
    
    def get_retry_delay(self, error_info: ErrorInfo) -> float:
        """Get delay before retry"""
        delays = self.retry_delays.get(error_info.category, [1])
        index = min(error_info.retry_count, len(delays) - 1)
        return delays[index] if delays else 1.0
    
    async def execute_recovery(self, error_info: ErrorInfo, 
                              recovery_callbacks: Dict[RecoveryAction, Callable]) -> bool:
        """Execute recovery actions"""
        success = False
        
        for action in error_info.recovery_actions:
            if action in recovery_callbacks:
                try:
                    callback = recovery_callbacks[action]
                    if asyncio.iscoroutinefunction(callback):
                        result = await callback(error_info)
                    else:
                        result = callback(error_info)
                    
                    if result:
                        success = True
                        logger.info(f"Recovery action {action.value} succeeded for {error_info.category.value} error")
                    
                except Exception as recovery_error:
                    logger.error(f"Recovery action {action.value} failed: {recovery_error}")
        
        return success


class ErrorHandler:
    """Main error handling coordinator"""
    
    def __init__(self):
        self.detector = ErrorDetector()
        self.recovery = ErrorRecovery()
        self.error_history: List[ErrorInfo] = []
        self.recovery_callbacks: Dict[RecoveryAction, Callable] = {}
        self._lock = asyncio.Lock()
        
        # Statistics
        self.stats = {
            'total_errors': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity},
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }
    
    async def handle_error(self, error: Exception, context: Dict = None,
                          session_id: str = None) -> bool:
        """
        Handle an error with classification, recovery, and notification
        Returns True if error was successfully handled/recovered
        """
        async with self._lock:
            # Classify error
            error_info = self.detector.classify_error(error, context)
            error_info.session_id = session_id
            
            # Update statistics
            self._update_stats(error_info)
            
            # Add to history
            self.error_history.append(error_info)
            if len(self.error_history) > 1000:  # Limit history size
                self.error_history = self.error_history[-1000:]
            
            # Log error
            log_data = error_info.to_dict()
            if error_info.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"Critical error: {error_info.message}", extra=log_data)
            elif error_info.severity == ErrorSeverity.HIGH:
                logger.error(f"High severity error: {error_info.message}", extra=log_data)
            elif error_info.severity == ErrorSeverity.MEDIUM:
                logger.warning(f"Medium severity error: {error_info.message}", extra=log_data)
            else:
                logger.info(f"Low severity error: {error_info.message}", extra=log_data)
            
            # Attempt recovery
            return await self._attempt_recovery(error_info)
    
    async def _attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Attempt to recover from an error"""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts and self.recovery.can_retry(error_info):
            attempt += 1
            error_info.retry_count = attempt
            
            # Wait before retry
            if attempt > 1:
                delay = self.recovery.get_retry_delay(error_info)
                logger.info(f"Retrying error recovery in {delay}s (attempt {attempt})")
                await asyncio.sleep(delay)
            
            # Execute recovery actions
            success = await self.recovery.execute_recovery(error_info, self.recovery_callbacks)
            
            if success:
                self.stats['successful_recoveries'] += 1
                logger.info(f"Successfully recovered from {error_info.category.value} error")
                return True
            
        # Recovery failed
        self.stats['failed_recoveries'] += 1
        logger.error(f"Failed to recover from {error_info.category.value} error after {attempt} attempts")
        
        # Escalate if needed
        if RecoveryAction.ESCALATE in error_info.recovery_actions:
            await self._escalate_error(error_info)
        
        return False
    
    async def _escalate_error(self, error_info: ErrorInfo):
        """Escalate error to higher-level handling"""
        logger.critical(f"Escalating {error_info.severity.value} {error_info.category.value} error: {error_info.message}")
        
        # Could send to external monitoring, admin notifications, etc.
        if RecoveryAction.NOTIFY_USER in error_info.recovery_actions:
            callback = self.recovery_callbacks.get(RecoveryAction.NOTIFY_USER)
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(error_info)
                    else:
                        callback(error_info)
                except Exception as e:
                    logger.error(f"Failed to notify user of escalated error: {e}")
    
    def _update_stats(self, error_info: ErrorInfo):
        """Update error statistics"""
        self.stats['total_errors'] += 1
        self.stats['errors_by_category'][error_info.category.value] += 1
        self.stats['errors_by_severity'][error_info.severity.value] += 1
    
    def register_recovery_callback(self, action: RecoveryAction, callback: Callable):
        """Register a recovery callback function"""
        self.recovery_callbacks[action] = callback
    
    def get_recent_errors(self, count: int = 10) -> List[ErrorInfo]:
        """Get recent errors"""
        return self.error_history[-count:] if self.error_history else []
    
    def get_error_stats(self) -> Dict:
        """Get error statistics"""
        return self.stats.copy()
    
    def get_session_errors(self, session_id: str) -> List[ErrorInfo]:
        """Get errors for a specific session"""
        return [error for error in self.error_history if error.session_id == session_id]
    
    def clear_error_history(self):
        """Clear error history"""
        self.error_history.clear()
        self.stats = {
            'total_errors': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'errors_by_severity': {sev.value: 0 for sev in ErrorSeverity},
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }


class DiscordErrorNotifier:
    """Handles error notifications to Discord"""
    
    @staticmethod
    async def create_error_embed(error_info: ErrorInfo) -> discord.Embed:
        """Create Discord embed for error notification"""
        
        # Choose color based on severity
        colors = {
            ErrorSeverity.LOW: discord.Color.light_grey(),
            ErrorSeverity.MEDIUM: discord.Color.orange(),
            ErrorSeverity.HIGH: discord.Color.red(),
            ErrorSeverity.CRITICAL: discord.Color.dark_red()
        }
        
        # Choose emoji based on category
        emojis = {
            ErrorCategory.PROCESS: "⚙️",
            ErrorCategory.DISCORD: "📱",
            ErrorCategory.NETWORK: "🌐",
            ErrorCategory.CONFIGURATION: "⚠️",
            ErrorCategory.PERMISSION: "🔒",
            ErrorCategory.RESOURCE: "💾",
            ErrorCategory.USER_INPUT: "👤",
            ErrorCategory.INTERNAL: "🐛"
        }
        
        title_emoji = emojis.get(error_info.category, "❌")
        
        embed = discord.Embed(
            title=f"{title_emoji} {error_info.severity.value.title()} Error",
            description=error_info.message,
            color=colors.get(error_info.severity, discord.Color.red()),
            timestamp=discord.utils.utcfromtimestamp(error_info.timestamp)
        )
        
        embed.add_field(
            name="Category",
            value=error_info.category.value.title(),
            inline=True
        )
        
        embed.add_field(
            name="Severity",
            value=error_info.severity.value.title(),
            inline=True
        )
        
        if error_info.session_id:
            embed.add_field(
                name="Session",
                value=error_info.session_id,
                inline=True
            )
        
        if error_info.retry_count > 0:
            embed.add_field(
                name="Retry Count",
                value=str(error_info.retry_count),
                inline=True
            )
        
        # Add context if available
        if error_info.context:
            context_text = '\n'.join([f"**{k}**: {v}" for k, v in error_info.context.items()][:5])
            embed.add_field(
                name="Context",
                value=context_text[:1024],  # Discord limit
                inline=False
            )
        
        return embed
    
    @staticmethod
    async def notify_error(channel: discord.TextChannel, error_info: ErrorInfo) -> Optional[discord.Message]:
        """Send error notification to Discord channel"""
        try:
            embed = await DiscordErrorNotifier.create_error_embed(error_info)
            return await channel.send(embed=embed)
        except Exception as e:
            logger.error(f"Failed to send error notification to Discord: {e}")
            return None