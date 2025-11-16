"""
UnityKernel Health Monitor

Continuous health checking and auto-recovery system.
Monitors kernel components and modules, restarts failed components.
"""

import asyncio
import psutil
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from .types import (
    Event, EventType, HealthCheck, SystemMetrics,
    SystemState, ModuleState, Priority
)


class HealthMonitor:
    """
    System health monitoring and auto-recovery

    Features:
    - Continuous health checks
    - System metrics collection (CPU, memory)
    - Module health monitoring
    - Auto-restart failed modules
    - Degradation detection
    - Alerting via events
    """

    def __init__(self, config: any, event_bus: any, module_loader: any):
        """
        Initialize health monitor

        Args:
            config: Config manager reference
            event_bus: Event bus reference
            module_loader: Module loader reference
        """
        self.config = config
        self.event_bus = event_bus
        self.module_loader = module_loader

        # System metrics
        self.metrics = SystemMetrics()
        self.start_time = datetime.utcnow()

        # Health checks
        self.last_check: Optional[datetime] = None
        self.check_interval = config.get('health.check_interval', 30)

        # Auto-recovery
        self.auto_restart = config.get('health.restart_failed_modules', True)
        self.degraded_threshold = config.get('health.degraded_threshold', 0.7)

        # Running state
        self.running = False
        self.monitor_task: Optional[asyncio.Task] = None

        # Process handle for system metrics
        self.process = psutil.Process()

    async def start(self) -> None:
        """Start health monitoring"""
        self.running = True
        self.start_time = datetime.utcnow()

        # Start background monitoring
        self.monitor_task = asyncio.create_task(self._monitor_loop())

        print(f"✓ Health monitor started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop health monitoring"""
        self.running = False

        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self) -> None:
        """Background monitoring loop"""
        while self.running:
            try:
                await asyncio.sleep(self.check_interval)

                # Perform health check
                await self.check_health()

                # Update metrics
                await self.update_metrics()

                # Check for issues
                await self._check_for_issues()

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠ Health monitor error: {e}")

    async def check_health(self) -> HealthCheck:
        """
        Perform complete system health check

        Returns:
            System health check result
        """
        self.last_check = datetime.utcnow()

        # Check all modules
        module_checks = await self._check_all_modules()

        # Determine overall health
        healthy_count = sum(1 for c in module_checks if c.is_healthy())
        total_count = len(module_checks)

        if total_count == 0:
            status = "healthy"  # No modules yet
        elif healthy_count == total_count:
            status = "healthy"
        elif healthy_count / total_count >= self.degraded_threshold:
            status = "degraded"
        else:
            status = "unhealthy"

        # Create system health check
        health = HealthCheck(
            component="system",
            status=status,
            timestamp=self.last_check,
            message=f"{healthy_count}/{total_count} modules healthy",
            metrics={
                'modules_healthy': healthy_count,
                'modules_total': total_count,
                'uptime_seconds': self.metrics.uptime_seconds,
                'cpu_usage': self.metrics.cpu_usage,
                'memory_usage_mb': self.metrics.memory_usage_mb
            }
        )

        # Publish health check event
        await self.event_bus.publish(Event(
            event_type=EventType.SYSTEM_HEALTH_CHECK.value,
            source="health_monitor",
            data={
                'status': status,
                'healthy_modules': healthy_count,
                'total_modules': total_count,
                'metrics': health.metrics
            },
            priority=Priority.LOW
        ), persist=False)

        return health

    async def _check_all_modules(self) -> List[HealthCheck]:
        """Check health of all loaded modules"""
        checks = []

        for module_name, module in self.module_loader.modules.items():
            try:
                check = await module.health_check()
                checks.append(check)

                # Update module info
                info = self.module_loader.module_info.get(module_name)
                if info:
                    info.health_status = check.status

            except Exception as e:
                # Module health check failed
                check = HealthCheck(
                    component=module_name,
                    status="unhealthy",
                    message=f"Health check failed: {e}"
                )
                checks.append(check)

        return checks

    async def update_metrics(self) -> None:
        """Update system metrics"""
        # Uptime
        self.metrics.uptime_seconds = (
            datetime.utcnow() - self.start_time
        ).total_seconds()

        # CPU usage (percentage)
        self.metrics.cpu_usage = self.process.cpu_percent(interval=0.1)

        # Memory usage (MB)
        mem_info = self.process.memory_info()
        self.metrics.memory_usage_mb = mem_info.rss / 1024 / 1024

        # Event bus stats
        bus_stats = self.event_bus.get_statistics()
        self.metrics.events_processed = bus_stats['events_delivered']
        self.metrics.events_failed = bus_stats['events_failed']

        # Module stats
        loader_stats = self.module_loader.get_statistics()
        self.metrics.modules_loaded = loader_stats['loaded']
        self.metrics.modules_running = loader_stats['states'].get('running', 0)
        self.metrics.modules_failed = loader_stats['states'].get('failed', 0)

        # Queue depth (if processor available)
        # Would need reference to priority processor

        self.metrics.last_health_check = self.last_check

    async def _check_for_issues(self) -> None:
        """Check for issues and take action"""
        # Check failed modules
        for module_name, info in self.module_loader.module_info.items():
            if info.state == ModuleState.FAILED and self.auto_restart and info.auto_restart:
                # Try to restart failed module
                await self._restart_module(module_name)

        # Check resource usage
        if self.metrics.cpu_usage > 90:
            await self._alert("High CPU usage", {
                'cpu_usage': self.metrics.cpu_usage
            })

        if self.metrics.memory_usage_mb > 4000:  # 4GB threshold
            await self._alert("High memory usage", {
                'memory_mb': self.metrics.memory_usage_mb
            })

    async def _restart_module(self, module_name: str) -> None:
        """
        Attempt to restart a failed module

        Args:
            module_name: Name of module to restart
        """
        print(f"🔄 Auto-restarting failed module: {module_name}")

        try:
            # Reload module
            await self.module_loader.reload_module(module_name)

            # Publish recovery event
            await self.event_bus.publish(Event(
                event_type="system.module_recovered",
                source="health_monitor",
                data={
                    'module_name': module_name,
                    'timestamp': datetime.utcnow().isoformat()
                },
                priority=Priority.HIGH
            ), persist=True)

        except Exception as e:
            print(f"❌ Failed to restart module {module_name}: {e}")

            # Publish failure event
            await self.event_bus.publish(Event(
                event_type="system.module_restart_failed",
                source="health_monitor",
                data={
                    'module_name': module_name,
                    'error': str(e)
                },
                priority=Priority.CRITICAL
            ), persist=True)

    async def _alert(self, message: str, data: Dict) -> None:
        """
        Send alert for critical issue

        Args:
            message: Alert message
            data: Alert data
        """
        await self.event_bus.publish(Event(
            event_type="system.alert",
            source="health_monitor",
            data={
                'message': message,
                **data
            },
            priority=Priority.CRITICAL
        ), persist=True)

        print(f"⚠ ALERT: {message} - {data}")

    def get_metrics(self) -> SystemMetrics:
        """Get current system metrics"""
        return self.metrics

    def get_health_summary(self) -> Dict[str, any]:
        """Get health summary as dictionary"""
        return {
            'status': 'healthy' if self.metrics.modules_failed == 0 else 'degraded',
            'uptime_seconds': self.metrics.uptime_seconds,
            'metrics': self.metrics.to_dict(),
            'last_check': self.last_check.isoformat() if self.last_check else None
        }
