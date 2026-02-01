"""Health Monitor - Component health tracking for PiDog brain

Provides health monitoring with:
- Health check function registration per component
- Status tracking: HEALTHY / DEGRADED / UNHEALTHY
- Background monitoring thread (configurable interval)
- Status exposure via get_status()

Usage:
    from pidog_brain.health_monitor import HealthMonitor, HealthStatus

    monitor = HealthMonitor()

    # Register health checks
    def check_camera():
        return HealthStatus.HEALTHY if camera.is_available() else HealthStatus.UNHEALTHY
    monitor.register('camera', check_camera)

    # Start monitoring
    monitor.start()

    # Check status
    status = monitor.get_status()
    # {'camera': 'HEALTHY', 'brain': 'DEGRADED', ...}

    # Stop monitoring
    monitor.stop()
"""

import threading
import time
import logging
from enum import Enum
from typing import Callable, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class ComponentHealth:
    """Health state for a single component"""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_error: Optional[str] = None
    check_count: int = 0
    failure_count: int = 0


class HealthMonitor:
    """Background health monitoring for system components

    Registers health check functions and periodically checks them.
    """

    DEFAULT_CHECK_INTERVAL = 10.0  # seconds

    def __init__(self, check_interval: float = DEFAULT_CHECK_INTERVAL):
        """Initialize health monitor

        Args:
            check_interval: Seconds between health checks (default 10s)
        """
        self._check_interval = check_interval
        self._checks: Dict[str, Callable[[], HealthStatus]] = {}
        self._health: Dict[str, ComponentHealth] = {}
        self._lock = threading.RLock()

        # Background thread
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def register(self, name: str, check_fn: Callable[[], HealthStatus]):
        """Register a health check function for a component

        Args:
            name: Component name
            check_fn: Function that returns HealthStatus

        Example:
            def check_camera():
                return HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY
            monitor.register('camera', check_camera)
        """
        with self._lock:
            self._checks[name] = check_fn
            self._health[name] = ComponentHealth(name=name)
            logger.debug(f"Registered health check for: {name}")

    def unregister(self, name: str):
        """Unregister a health check

        Args:
            name: Component name to remove
        """
        with self._lock:
            self._checks.pop(name, None)
            self._health.pop(name, None)

    def check(self, name: str) -> HealthStatus:
        """Run health check for a specific component

        Args:
            name: Component name

        Returns:
            Current health status
        """
        with self._lock:
            if name not in self._checks:
                return HealthStatus.UNKNOWN

            check_fn = self._checks[name]
            health = self._health[name]

        try:
            status = check_fn()
            with self._lock:
                # Check if component still exists (could be unregistered during check)
                if name not in self._health:
                    return status
                health = self._health[name]
                health.status = status
                health.last_check = datetime.now()
                health.check_count += 1
                if status == HealthStatus.UNHEALTHY:
                    health.failure_count += 1
                health.last_error = None
            return status

        except Exception as e:
            logger.error(f"Health check failed for {name}: {e}")
            with self._lock:
                # Check if component still exists (could be unregistered during check)
                if name not in self._health:
                    return HealthStatus.UNHEALTHY
                health = self._health[name]
                health.status = HealthStatus.UNHEALTHY
                health.last_check = datetime.now()
                health.check_count += 1
                health.failure_count += 1
                health.last_error = str(e)
            return HealthStatus.UNHEALTHY

    def check_all(self) -> Dict[str, HealthStatus]:
        """Run all health checks

        Returns:
            Dict of component name -> status
        """
        results = {}
        with self._lock:
            names = list(self._checks.keys())

        for name in names:
            results[name] = self.check(name)

        return results

    def get_status(self) -> Dict[str, str]:
        """Get current health status of all components

        Returns:
            Dict of component name -> status string
        """
        with self._lock:
            return {
                name: health.status.value
                for name, health in self._health.items()
            }

    def get_detailed_status(self) -> Dict[str, Dict]:
        """Get detailed health information for all components

        Returns:
            Dict with detailed health info per component
        """
        with self._lock:
            result = {}
            for name, health in self._health.items():
                result[name] = {
                    'status': health.status.value,
                    'last_check': health.last_check.isoformat() if health.last_check else None,
                    'last_error': health.last_error,
                    'check_count': health.check_count,
                    'failure_count': health.failure_count
                }
            return result

    def is_healthy(self) -> bool:
        """Check if all components are healthy

        Returns:
            True if all components are HEALTHY
        """
        with self._lock:
            return all(
                h.status == HealthStatus.HEALTHY
                for h in self._health.values()
            )

    def start(self):
        """Start background health monitoring"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Health monitor started (interval: {self._check_interval}s)")

    def stop(self, timeout: float = 5.0):
        """Stop background health monitoring

        Args:
            timeout: Maximum seconds to wait for thread to stop
        """
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("Health monitor stopped")

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                self.check_all()
            except Exception as e:
                logger.error(f"Health monitor error: {e}")

            # Sleep in small intervals to allow quick shutdown
            for _ in range(int(self._check_interval * 10)):
                if not self._running:
                    break
                time.sleep(0.1)
