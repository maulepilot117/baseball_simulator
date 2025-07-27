"""
Performance Monitoring and Alerting System
Tracks system performance, identifies bottlenecks, and sends alerts
"""

import asyncio
import logging
import time
import psutil
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, TypeVar
from dataclasses import dataclass, field
from enum import Enum
import json
from collections import deque, defaultdict
import functools

import asyncpg

logger = logging.getLogger(__name__)

T = TypeVar('T')


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    metric_type: MetricType
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class Alert:
    """System alert"""
    alert_id: str
    level: AlertLevel
    title: str
    description: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    metric_name: str
    warning_threshold: float
    critical_threshold: float
    comparison: str = "greater_than"  # greater_than, less_than, equal_to
    time_window: int = 300  # seconds
    min_samples: int = 3


class PerformanceCollector:
    """Collects and aggregates performance metrics"""
    
    def __init__(self, retention_hours: int = 24):
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.retention_hours = retention_hours
        self.start_time = time.time()
        
    def record_metric(self, name: str, value: float, metric_type: MetricType, 
                     tags: Optional[Dict[str, str]] = None, unit: str = ""):
        """Record a performance metric"""
        metric = PerformanceMetric(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.utcnow(),
            tags=tags or {},
            unit=unit
        )
        
        self.metrics[name].append(metric)
        self._cleanup_old_metrics()
    
    def get_metrics(self, name: str, since: Optional[datetime] = None) -> List[PerformanceMetric]:
        """Get metrics for a specific name"""
        if since is None:
            since = datetime.utcnow() - timedelta(hours=1)
        
        return [m for m in self.metrics[name] if m.timestamp >= since]
    
    def get_metric_stats(self, name: str, since: Optional[datetime] = None) -> Dict[str, float]:
        """Get statistical summary of metrics"""
        metrics = self.get_metrics(name, since)
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        }
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.utcnow() - timedelta(hours=self.retention_hours)
        
        for name in self.metrics:
            while self.metrics[name] and self.metrics[name][0].timestamp < cutoff:
                self.metrics[name].popleft()


class SystemMonitor:
    """Monitors system resource usage"""
    
    def __init__(self, collector: PerformanceCollector):
        self.collector = collector
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, interval: int = 30):
        """Start system resource monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system resource monitoring"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("System monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in system monitoring: {e}")
                await asyncio.sleep(interval)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.collector.record_metric("system.cpu.usage", cpu_percent, MetricType.GAUGE, unit="%")
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.collector.record_metric("system.memory.usage", memory.percent, MetricType.GAUGE, unit="%")
        self.collector.record_metric("system.memory.available", memory.available / 1024**3, MetricType.GAUGE, unit="GB")
        
        # Disk usage
        disk = psutil.disk_usage('/')
        self.collector.record_metric("system.disk.usage", (disk.used / disk.total) * 100, MetricType.GAUGE, unit="%")
        
        # Network I/O
        network = psutil.net_io_counters()
        self.collector.record_metric("system.network.bytes_sent", network.bytes_sent, MetricType.COUNTER, unit="bytes")
        self.collector.record_metric("system.network.bytes_recv", network.bytes_recv, MetricType.COUNTER, unit="bytes")
        
        # Process-specific metrics
        process = psutil.Process()
        self.collector.record_metric("process.memory.rss", process.memory_info().rss / 1024**2, MetricType.GAUGE, unit="MB")
        self.collector.record_metric("process.cpu.percent", process.cpu_percent(), MetricType.GAUGE, unit="%")


class DatabaseMonitor:
    """Monitors database performance"""
    
    def __init__(self, db_pool: asyncpg.Pool, collector: PerformanceCollector):
        self.db_pool = db_pool
        self.collector = collector
    
    async def collect_db_metrics(self):
        """Collect database performance metrics"""
        try:
            # Connection pool stats
            pool_size = self.db_pool.get_size()
            idle_connections = self.db_pool.get_idle_size()
            
            self.collector.record_metric("database.pool.total", pool_size, MetricType.GAUGE)
            self.collector.record_metric("database.pool.idle", idle_connections, MetricType.GAUGE)
            self.collector.record_metric("database.pool.active", pool_size - idle_connections, MetricType.GAUGE)
            
            # Database statistics
            db_stats = await self.db_pool.fetchrow("""
                SELECT 
                    pg_database_size(current_database()) as db_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT count(*) FROM pg_stat_activity) as total_connections
            """)
            
            if db_stats:
                self.collector.record_metric("database.size", db_stats['db_size'] / 1024**3, MetricType.GAUGE, unit="GB")
                self.collector.record_metric("database.connections.active", db_stats['active_connections'], MetricType.GAUGE)
                self.collector.record_metric("database.connections.total", db_stats['total_connections'], MetricType.GAUGE)
            
            # Table sizes
            table_stats = await self.db_pool.fetch("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    n_tup_ins + n_tup_upd + n_tup_del as total_operations
                FROM pg_tables t
                JOIN pg_stat_user_tables s ON t.tablename = s.relname
                WHERE schemaname = 'public'
                ORDER BY size_bytes DESC
                LIMIT 10
            """)
            
            for table in table_stats:
                table_name = table['tablename']
                self.collector.record_metric(
                    f"database.table.{table_name}.size", 
                    table['size_bytes'] / 1024**2, 
                    MetricType.GAUGE, 
                    unit="MB"
                )
                self.collector.record_metric(
                    f"database.table.{table_name}.operations", 
                    table['total_operations'], 
                    MetricType.COUNTER
                )
                
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")


class AlertManager:
    """Manages performance alerts and notifications"""
    
    def __init__(self, collector: PerformanceCollector, db_pool: Optional[asyncpg.Pool] = None):
        self.collector = collector
        self.db_pool = db_pool
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Default thresholds
        self._setup_default_thresholds()
    
    def _setup_default_thresholds(self):
        """Setup default performance thresholds"""
        self.thresholds.update({
            'system.cpu.usage': PerformanceThreshold(
                metric_name='system.cpu.usage',
                warning_threshold=80.0,
                critical_threshold=95.0,
                time_window=300
            ),
            'system.memory.usage': PerformanceThreshold(
                metric_name='system.memory.usage',
                warning_threshold=85.0,
                critical_threshold=95.0,
                time_window=300
            ),
            'database.connections.active': PerformanceThreshold(
                metric_name='database.connections.active',
                warning_threshold=80.0,
                critical_threshold=95.0,
                time_window=300
            ),
            'api.response_time': PerformanceThreshold(
                metric_name='api.response_time',
                warning_threshold=2.0,
                critical_threshold=5.0,
                time_window=300,
                min_samples=5
            ),
            'calculation.duration': PerformanceThreshold(
                metric_name='calculation.duration',
                warning_threshold=30.0,
                critical_threshold=60.0,
                time_window=600
            )
        })
    
    def add_threshold(self, threshold: PerformanceThreshold):
        """Add custom performance threshold"""
        self.thresholds[threshold.metric_name] = threshold
    
    async def check_alerts(self):
        """Check all metrics against thresholds and generate alerts"""
        current_time = datetime.utcnow()
        
        for threshold in self.thresholds.values():
            try:
                await self._check_metric_threshold(threshold, current_time)
            except Exception as e:
                logger.error(f"Error checking threshold for {threshold.metric_name}: {e}")
    
    async def _check_metric_threshold(self, threshold: PerformanceThreshold, current_time: datetime):
        """Check a specific metric against its threshold"""
        # Get recent metrics
        since = current_time - timedelta(seconds=threshold.time_window)
        metrics = self.collector.get_metrics(threshold.metric_name, since)
        
        if len(metrics) < threshold.min_samples:
            return
        
        # Calculate current value (latest or average based on type)
        latest_metric = metrics[-1]
        if latest_metric.metric_type == MetricType.GAUGE:
            current_value = latest_metric.value
        else:
            # For counters/histograms, use average
            current_value = statistics.mean([m.value for m in metrics])
        
        # Check thresholds
        alert_level = None
        threshold_value = None
        
        if threshold.comparison == "greater_than":
            if current_value >= threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif current_value >= threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold
        elif threshold.comparison == "less_than":
            if current_value <= threshold.critical_threshold:
                alert_level = AlertLevel.CRITICAL
                threshold_value = threshold.critical_threshold
            elif current_value <= threshold.warning_threshold:
                alert_level = AlertLevel.WARNING
                threshold_value = threshold.warning_threshold
        
        # Generate alert if threshold exceeded
        if alert_level and not self._is_alert_cooldown(threshold.metric_name, alert_level):
            alert = Alert(
                alert_id=f"{threshold.metric_name}_{alert_level.value}_{int(current_time.timestamp())}",
                level=alert_level,
                title=f"{threshold.metric_name} threshold exceeded",
                description=f"{threshold.metric_name} is {current_value:.2f}, exceeding {alert_level.value} threshold of {threshold_value:.2f}",
                timestamp=current_time,
                metric_name=threshold.metric_name,
                current_value=current_value,
                threshold=threshold_value,
                tags=latest_metric.tags
            )
            
            await self._send_alert(alert)
    
    def _is_alert_cooldown(self, metric_name: str, level: AlertLevel) -> bool:
        """Check if alert is in cooldown period"""
        cooldown_key = f"{metric_name}_{level.value}"
        cooldown_period = timedelta(minutes=15 if level == AlertLevel.WARNING else 5)
        
        if cooldown_key in self.alert_cooldowns:
            if datetime.utcnow() - self.alert_cooldowns[cooldown_key] < cooldown_period:
                return True
        
        return False
    
    async def _send_alert(self, alert: Alert):
        """Send alert notification"""
        # Log alert
        log_level = logging.CRITICAL if alert.level == AlertLevel.CRITICAL else logging.WARNING
        logger.log(log_level, f"ALERT: {alert.title} - {alert.description}")
        
        # Store in history
        self.alert_history.append(alert)
        
        # Set cooldown
        cooldown_key = f"{alert.metric_name}_{alert.level.value}"
        self.alert_cooldowns[cooldown_key] = alert.timestamp
        
        # Store in database if available
        if self.db_pool:
            await self._store_alert(alert)
        
        # Additional notification methods could be added here:
        # - Email notifications
        # - Slack/Discord webhooks
        # - PagerDuty integration
        # - SMS alerts
    
    async def _store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            await self.db_pool.execute("""
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    alert_id VARCHAR(200) UNIQUE NOT NULL,
                    level VARCHAR(20) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    metric_name VARCHAR(200),
                    current_value FLOAT,
                    threshold_value FLOAT,
                    tags JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            await self.db_pool.execute("""
                INSERT INTO performance_alerts 
                (alert_id, level, title, description, timestamp, metric_name, current_value, threshold_value, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (alert_id) DO NOTHING
            """, 
                alert.alert_id, alert.level.value, alert.title, alert.description,
                alert.timestamp, alert.metric_name, alert.current_value, 
                alert.threshold, json.dumps(alert.tags)
            )
            
        except Exception as e:
            logger.error(f"Failed to store alert in database: {e}")
    
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get recent alerts"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp >= cutoff]


def monitor_performance(metric_name: str, metric_type: MetricType = MetricType.TIMER, 
                       tags: Optional[Dict[str, str]] = None):
    """Decorator for monitoring function performance"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                if hasattr(monitor_performance, 'collector'):
                    collector = monitor_performance.collector
                    
                    # Record timing
                    collector.record_metric(
                        f"{metric_name}.duration", 
                        duration, 
                        MetricType.TIMER, 
                        tags={**(tags or {}), 'function': func.__name__},
                        unit="seconds"
                    )
                    
                    # Record success/failure
                    collector.record_metric(
                        f"{metric_name}.{'success' if success else 'failure'}", 
                        1, 
                        MetricType.COUNTER,
                        tags={**(tags or {}), 'function': func.__name__}
                    )
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                duration = time.time() - start_time
                
                # Record metrics (same as async)
                if hasattr(monitor_performance, 'collector'):
                    collector = monitor_performance.collector
                    
                    collector.record_metric(
                        f"{metric_name}.duration", 
                        duration, 
                        MetricType.TIMER, 
                        tags={**(tags or {}), 'function': func.__name__},
                        unit="seconds"
                    )
                    
                    collector.record_metric(
                        f"{metric_name}.{'success' if success else 'failure'}", 
                        1, 
                        MetricType.COUNTER,
                        tags={**(tags or {}), 'function': func.__name__}
                    )
            
            return result
        
        # Return appropriate wrapper based on function type
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class PerformanceManager:
    """Main performance monitoring coordinator"""
    
    def __init__(self, db_pool: Optional[asyncpg.Pool] = None):
        self.collector = PerformanceCollector()
        self.system_monitor = SystemMonitor(self.collector)
        self.db_monitor = DatabaseMonitor(db_pool, self.collector) if db_pool else None
        self.alert_manager = AlertManager(self.collector, db_pool)
        
        # Set global collector for decorator
        monitor_performance.collector = self.collector
        
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def start_monitoring(self, system_interval: int = 30, alert_interval: int = 60):
        """Start all monitoring services"""
        await self.system_monitor.start_monitoring(system_interval)
        
        # Start alert checking loop
        self._monitoring_task = asyncio.create_task(self._alert_check_loop(alert_interval))
        
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop all monitoring services"""
        await self.system_monitor.stop_monitoring()
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _alert_check_loop(self, interval: int):
        """Background task for checking alerts"""
        while True:
            try:
                await self.alert_manager.check_alerts()
                if self.db_monitor:
                    await self.db_monitor.collect_db_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in alert check loop: {e}")
                await asyncio.sleep(interval)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return {
            'system_metrics': {
                'cpu': self.collector.get_metric_stats('system.cpu.usage'),
                'memory': self.collector.get_metric_stats('system.memory.usage'),
                'disk': self.collector.get_metric_stats('system.disk.usage')
            },
            'database_metrics': {
                'connections': self.collector.get_metric_stats('database.connections.active'),
                'pool_usage': self.collector.get_metric_stats('database.pool.active')
            } if self.db_monitor else {},
            'recent_alerts': [
                {
                    'level': alert.level.value,
                    'title': alert.title,
                    'timestamp': alert.timestamp.isoformat(),
                    'metric': alert.metric_name
                }
                for alert in self.alert_manager.get_recent_alerts(hours=1)
            ]
        }


# Global performance manager instance
performance_manager: Optional[PerformanceManager] = None


def initialize_monitoring(db_pool: Optional[asyncpg.Pool] = None) -> PerformanceManager:
    """Initialize global performance monitoring"""
    global performance_manager
    performance_manager = PerformanceManager(db_pool)
    return performance_manager


def get_performance_manager() -> Optional[PerformanceManager]:
    """Get global performance manager instance"""
    return performance_manager