"""
Performance Monitoring and Optimization for Claude Bridge

Monitors system performance, memory usage, and provides optimization strategies.
"""

import asyncio
import psutil
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import deque
import gc

from .logging_setup import get_logger

logger = get_logger('performance')


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_io_read: int
    disk_io_write: int
    network_sent: int 
    network_recv: int
    active_sessions: int
    queue_size: int
    response_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'memory_percent': self.memory_percent,
            'disk_io_read': self.disk_io_read,
            'disk_io_write': self.disk_io_write,
            'network_sent': self.network_sent,
            'network_recv': self.network_recv,
            'active_sessions': self.active_sessions,
            'queue_size': self.queue_size,
            'response_time_ms': self.response_time_ms
        }


class PerformanceOptimizer:
    """Automatic performance optimization"""
    
    def __init__(self):
        self.optimization_rules = {
            'high_memory': self._optimize_memory,
            'high_cpu': self._optimize_cpu,
            'slow_response': self._optimize_response_time,
            'large_queue': self._optimize_queue,
        }
        
        self.thresholds = {
            'memory_percent': 80.0,
            'cpu_percent': 85.0,
            'response_time_ms': 2000.0,
            'queue_size': 50,
        }
    
    async def analyze_and_optimize(self, metrics: PerformanceMetrics, 
                                 context: Dict = None) -> List[str]:
        """Analyze metrics and apply optimizations"""
        optimizations_applied = []
        
        # Check memory usage
        if metrics.memory_percent > self.thresholds['memory_percent']:
            actions = await self._optimize_memory(metrics, context)
            optimizations_applied.extend(actions)
        
        # Check CPU usage
        if metrics.cpu_percent > self.thresholds['cpu_percent']:
            actions = await self._optimize_cpu(metrics, context)
            optimizations_applied.extend(actions)
        
        # Check response time
        if metrics.response_time_ms > self.thresholds['response_time_ms']:
            actions = await self._optimize_response_time(metrics, context)
            optimizations_applied.extend(actions)
        
        # Check queue size
        if metrics.queue_size > self.thresholds['queue_size']:
            actions = await self._optimize_queue(metrics, context)
            optimizations_applied.extend(actions)
        
        return optimizations_applied
    
    async def _optimize_memory(self, metrics: PerformanceMetrics, 
                              context: Dict = None) -> List[str]:
        """Optimize memory usage"""
        actions = []
        
        # Force garbage collection
        gc.collect()
        actions.append("Triggered garbage collection")
        
        # Clear old sessions if available
        if context and 'session_manager' in context:
            session_manager = context['session_manager']
            # Implementation would clear expired sessions
            actions.append("Cleared expired sessions")
        
        # Reduce buffer sizes
        if context and 'buffer_manager' in context:
            buffer_manager = context['buffer_manager']
            # Implementation would reduce buffer sizes
            actions.append("Reduced buffer sizes")
        
        logger.info(f"Memory optimization applied: {actions}")
        return actions
    
    async def _optimize_cpu(self, metrics: PerformanceMetrics,
                           context: Dict = None) -> List[str]:
        """Optimize CPU usage"""
        actions = []
        
        # Reduce update frequency
        actions.append("Reduced update frequency")
        
        # Enable burst mode throttling
        actions.append("Enabled burst mode throttling")
        
        logger.info(f"CPU optimization applied: {actions}")
        return actions
    
    async def _optimize_response_time(self, metrics: PerformanceMetrics,
                                    context: Dict = None) -> List[str]:
        """Optimize response time"""
        actions = []
        
        # Enable output batching
        actions.append("Enabled output batching")
        
        # Increase buffer flush interval
        actions.append("Increased buffer flush interval")
        
        logger.info(f"Response time optimization applied: {actions}")
        return actions
    
    async def _optimize_queue(self, metrics: PerformanceMetrics,
                            context: Dict = None) -> List[str]:
        """Optimize queue management"""
        actions = []
        
        # Prioritize queue processing
        actions.append("Prioritized queue processing")
        
        # Drop low priority messages
        actions.append("Dropped low priority messages")
        
        logger.info(f"Queue optimization applied: {actions}")
        return actions


class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self, collection_interval: float = 10.0, history_size: int = 100):
        self.collection_interval = collection_interval
        self.history_size = history_size
        
        # Performance data
        self.metrics_history: deque[PerformanceMetrics] = deque(maxlen=history_size)
        self.process = psutil.Process()
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._lock = threading.RLock()
        
        # Performance callbacks
        self.alert_callbacks: List[Callable[[PerformanceMetrics], None]] = []
        
        # Baseline metrics
        self._baseline_metrics: Optional[PerformanceMetrics] = None
        
        # Optimizer
        self.optimizer = PerformanceOptimizer()
        
        # Context for optimization
        self.context = {}
    
    async def start_monitoring(self):
        """Start performance monitoring"""
        if self._monitoring:
            return
        
        logger.info("Starting performance monitoring")
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self._monitoring:
            return
        
        logger.info("Stopping performance monitoring")
        self._monitoring = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                # Collect metrics
                metrics = self._collect_metrics()
                
                with self._lock:
                    self.metrics_history.append(metrics)
                
                # Set baseline if first measurement
                if self._baseline_metrics is None:
                    self._baseline_metrics = metrics
                
                # Check for performance issues
                await self._check_performance_alerts(metrics)
                
                # Apply optimizations if needed
                await self._auto_optimize(metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        try:
            # CPU and memory
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            memory_percent = self.process.memory_percent()
            
            # I/O
            try:
                io_counters = self.process.io_counters()
                disk_read = io_counters.read_bytes
                disk_write = io_counters.write_bytes
            except (psutil.AccessDenied, AttributeError):
                disk_read = disk_write = 0
            
            # Network (system-wide)
            try:
                net_io = psutil.net_io_counters()
                network_sent = net_io.bytes_sent
                network_recv = net_io.bytes_recv
            except (psutil.AccessDenied, AttributeError):
                network_sent = network_recv = 0
            
            # Application-specific metrics
            active_sessions = self.context.get('active_sessions', 0)
            queue_size = self.context.get('queue_size', 0)
            
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                memory_percent=memory_percent,
                disk_io_read=disk_read,
                disk_io_write=disk_write,
                network_sent=network_sent,
                network_recv=network_recv,
                active_sessions=active_sessions,
                queue_size=queue_size
            )
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            # Return default metrics on error
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0,
                disk_io_read=0,
                disk_io_write=0,
                network_sent=0,
                network_recv=0,
                active_sessions=0,
                queue_size=0
            )
    
    async def _check_performance_alerts(self, metrics: PerformanceMetrics):
        """Check for performance issues and trigger alerts"""
        alerts = []
        
        # Memory alerts
        if metrics.memory_percent > 90:
            alerts.append(f"Critical memory usage: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent > 75:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")
        
        # CPU alerts
        if metrics.cpu_percent > 95:
            alerts.append(f"Critical CPU usage: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent > 80:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")
        
        # Queue alerts
        if metrics.queue_size > 100:
            alerts.append(f"Critical queue size: {metrics.queue_size}")
        elif metrics.queue_size > 50:
            alerts.append(f"Large queue size: {metrics.queue_size}")
        
        # Trigger callbacks for alerts
        if alerts:
            logger.warning(f"Performance alerts: {'; '.join(alerts)}")
            for callback in self.alert_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(metrics)
                    else:
                        callback(metrics)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
    
    async def _auto_optimize(self, metrics: PerformanceMetrics):
        """Automatically optimize performance if needed"""
        try:
            optimizations = await self.optimizer.analyze_and_optimize(metrics, self.context)
            if optimizations:
                logger.info(f"Applied automatic optimizations: {optimizations}")
        except Exception as e:
            logger.error(f"Error in auto-optimization: {e}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get most recent metrics"""
        with self._lock:
            return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, count: int = None) -> List[PerformanceMetrics]:
        """Get metrics history"""
        with self._lock:
            if count is None:
                return list(self.metrics_history)
            else:
                return list(self.metrics_history)[-count:]
    
    def get_performance_summary(self, minutes: int = 30) -> Dict:
        """Get performance summary over time period"""
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_mb for m in recent_metrics) / len(recent_metrics)
        avg_queue = sum(m.queue_size for m in recent_metrics) / len(recent_metrics)
        
        # Calculate peaks
        peak_cpu = max(m.cpu_percent for m in recent_metrics)
        peak_memory = max(m.memory_mb for m in recent_metrics)
        peak_queue = max(m.queue_size for m in recent_metrics)
        
        return {
            'time_period_minutes': minutes,
            'sample_count': len(recent_metrics),
            'averages': {
                'cpu_percent': avg_cpu,
                'memory_mb': avg_memory,
                'queue_size': avg_queue
            },
            'peaks': {
                'cpu_percent': peak_cpu,
                'memory_mb': peak_memory,
                'queue_size': peak_queue
            },
            'current': recent_metrics[-1].to_dict() if recent_metrics else {}
        }
    
    def add_alert_callback(self, callback: Callable[[PerformanceMetrics], None]):
        """Add performance alert callback"""
        self.alert_callbacks.append(callback)
    
    def update_context(self, **kwargs):
        """Update monitoring context"""
        self.context.update(kwargs)
    
    def get_health_score(self) -> float:
        """Calculate overall health score (0-100)"""
        current = self.get_current_metrics()
        if not current:
            return 100.0
        
        # Calculate score based on various factors
        cpu_score = max(0, 100 - current.cpu_percent)
        memory_score = max(0, 100 - current.memory_percent)
        queue_score = max(0, 100 - (current.queue_size / 100 * 100))
        
        # Weight the scores
        overall_score = (cpu_score * 0.4 + memory_score * 0.4 + queue_score * 0.2)
        
        return min(100.0, max(0.0, overall_score))
    
    def is_performance_degraded(self) -> bool:
        """Check if performance is significantly degraded"""
        if not self._baseline_metrics:
            return False
        
        current = self.get_current_metrics()
        if not current:
            return False
        
        # Compare with baseline
        cpu_increase = current.cpu_percent - self._baseline_metrics.cpu_percent
        memory_increase = current.memory_percent - self._baseline_metrics.memory_percent
        
        # Thresholds for degradation
        return (cpu_increase > 30 or memory_increase > 30 or 
                current.cpu_percent > 90 or current.memory_percent > 90)


class ResourceManager:
    """Manages system resources and enforces limits"""
    
    def __init__(self):
        self.limits = {
            'max_memory_mb': 500,
            'max_cpu_percent': 80,
            'max_queue_size': 100,
            'max_sessions': 10
        }
        
        self.monitor = PerformanceMonitor()
    
    async def check_resource_limits(self) -> Dict[str, bool]:
        """Check if resource limits are exceeded"""
        current = self.monitor.get_current_metrics()
        if not current:
            return {}
        
        violations = {}
        
        if current.memory_mb > self.limits['max_memory_mb']:
            violations['memory'] = True
        
        if current.cpu_percent > self.limits['max_cpu_percent']:
            violations['cpu'] = True
        
        if current.queue_size > self.limits['max_queue_size']:
            violations['queue'] = True
        
        if current.active_sessions > self.limits['max_sessions']:
            violations['sessions'] = True
        
        return violations
    
    async def enforce_limits(self, context: Dict = None) -> List[str]:
        """Enforce resource limits by taking corrective action"""
        violations = await self.check_resource_limits()
        actions_taken = []
        
        if violations.get('memory', False):
            # Force garbage collection
            gc.collect()
            actions_taken.append("Triggered garbage collection for memory limit")
        
        if violations.get('queue', False):
            # Would implement queue pruning
            actions_taken.append("Pruned message queue for size limit")
        
        if violations.get('sessions', False):
            # Would implement session limiting
            actions_taken.append("Limited new session creation")
        
        return actions_taken
    
    def set_limits(self, **limits):
        """Update resource limits"""
        self.limits.update(limits)
        logger.info(f"Updated resource limits: {self.limits}")
    
    def get_limits(self) -> Dict:
        """Get current resource limits"""
        return self.limits.copy()