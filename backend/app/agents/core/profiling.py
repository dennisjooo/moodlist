"""Performance profiling utilities for monitoring and regression detection.

Provides continuous profiling capabilities to track performance over time
and detect regressions.
"""

import asyncio
import functools
import time
import structlog
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict

from .cache import cache_manager

logger = structlog.get_logger(__name__)


class PerformanceProfiler:
    """Tracks performance metrics across the application."""

    # In-memory storage for recent profiling data
    _metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    _max_samples_per_metric = 100  # Keep last 100 samples per metric

    @classmethod
    async def record_metric(
        cls,
        metric_name: str,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a performance metric.

        Args:
            metric_name: Name of the metric (e.g., "seed_gathering", "artist_search")
            duration_seconds: Duration in seconds
            metadata: Optional additional metadata
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration_seconds,
            "metadata": metadata or {},
        }

        # Store in memory
        cls._metrics[metric_name].append(record)

        # Trim to max samples
        if len(cls._metrics[metric_name]) > cls._max_samples_per_metric:
            cls._metrics[metric_name] = cls._metrics[metric_name][
                -cls._max_samples_per_metric :
            ]

        # Also cache for persistence (1 hour TTL)
        cache_key = f"profiling:{metric_name}:latest"
        try:
            await cache_manager.cache.set(cache_key, record, ttl=3600)
        except Exception as e:
            logger.warning(f"Failed to cache profiling metric: {e}")

        # Log if duration exceeds threshold
        threshold = (
            metadata.get("expected_duration_seconds", 10.0) if metadata else 10.0
        )
        if duration_seconds > threshold:
            logger.warning(
                f"Performance threshold exceeded: {metric_name}",
                duration_seconds=f"{duration_seconds:.2f}",
                threshold_seconds=threshold,
                metadata=metadata,
            )

    @classmethod
    def get_metrics(cls, metric_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent metrics for a given name.

        Args:
            metric_name: Name of the metric
            limit: Maximum number of samples to return

        Returns:
            List of recent metric records
        """
        return cls._metrics.get(metric_name, [])[-limit:]

    @classmethod
    def get_metric_stats(cls, metric_name: str) -> Dict[str, Any]:
        """Get statistics for a metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Dictionary with min, max, avg, and count
        """
        samples = cls._metrics.get(metric_name, [])
        if not samples:
            return {
                "metric_name": metric_name,
                "count": 0,
                "min": None,
                "max": None,
                "avg": None,
            }

        durations = [s["duration_seconds"] for s in samples]
        return {
            "metric_name": metric_name,
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "recent_samples": samples[-5:],  # Last 5 samples
        }

    @classmethod
    def list_all_metrics(cls) -> List[str]:
        """List all tracked metric names.

        Returns:
            List of metric names
        """
        return list(cls._metrics.keys())


@contextmanager
def profile(metric_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Context manager for profiling synchronous code.

    Args:
        metric_name: Name of the metric
        metadata: Optional metadata

    Example:
        with profile("my_operation", {"user_id": 123}):
            # ... code to profile
            pass
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        # Use asyncio to record metric (will be scheduled)
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(
                PerformanceProfiler.record_metric(metric_name, duration, metadata)
            )
        except RuntimeError:
            # No event loop, just log
            logger.info(
                f"Profile: {metric_name}",
                duration_seconds=f"{duration:.2f}",
                metadata=metadata,
            )


@asynccontextmanager
async def profile_async(metric_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Async context manager for profiling asynchronous code.

    Args:
        metric_name: Name of the metric
        metadata: Optional metadata

    Example:
        async with profile_async("my_async_operation", {"user_id": 123}):
            # ... async code to profile
            await something()
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        await PerformanceProfiler.record_metric(metric_name, duration, metadata)


def profile_function(metric_name: Optional[str] = None):
    """Decorator for profiling functions.

    Args:
        metric_name: Optional metric name (defaults to function name)

    Example:
        @profile_function("expensive_operation")
        async def my_function():
            # ... code
            pass
    """

    def decorator(func: Callable):
        nonlocal metric_name
        if metric_name is None:
            metric_name = f"{func.__module__}.{func.__name__}"

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                async with profile_async(metric_name, {"function": func.__name__}):
                    return await func(*args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                with profile(metric_name, {"function": func.__name__}):
                    return func(*args, **kwargs)

            return sync_wrapper

    return decorator
