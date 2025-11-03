"""Rate limiting utilities for the agentic system."""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
import structlog

from fastapi import Request
from app.core.exceptions import RateLimitException


logger = structlog.get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API endpoints."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst requests allowed
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size

        # Calculate tokens per second
        self.tokens_per_second = requests_per_minute / 60.0

        # In-memory storage for rate limiting
        # In production, this would use Redis
        self.buckets: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_update)
        self.request_counts: Dict[str, deque] = defaultdict(deque)

        # Cleanup interval
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _get_bucket(self, key: str) -> Tuple[float, float]:
        """Get or create a token bucket for a key.

        Args:
            key: Rate limiting key (IP, user_id, etc.)

        Returns:
            Tuple of (current_tokens, last_update_time)
        """
        now = time.time()

        if key not in self.buckets:
            # Initialize new bucket
            self.buckets[key] = (self.burst_size, now)
            return self.buckets[key]

        tokens, last_update = self.buckets[key]

        # Add tokens based on elapsed time
        elapsed = now - last_update
        new_tokens = elapsed * self.tokens_per_second

        # Update bucket
        updated_tokens = min(self.burst_size, tokens + new_tokens)
        self.buckets[key] = (updated_tokens, now)

        return self.buckets[key]

    def _consume_token(self, key: str) -> bool:
        """Try to consume a token from the bucket.

        Args:
            key: Rate limiting key

        Returns:
            Whether a token was consumed (request allowed)
        """
        tokens, _ = self._get_bucket(key)

        if tokens >= 1.0:
            self.buckets[key] = (tokens - 1.0, time.time())
            return True

        return False

    def _cleanup_old_entries(self):
        """Clean up old rate limiting entries."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Clean up old buckets (older than 1 hour)
        cutoff = now - 3600
        keys_to_remove = [
            key for key, (_, last_update) in self.buckets.items()
            if last_update < cutoff
        ]

        for key in keys_to_remove:
            del self.buckets[key]
            if key in self.request_counts:
                del self.request_counts[key]

        self.last_cleanup = now

        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} old rate limiting entries")

    async def is_allowed(
        self,
        request: Request,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> bool:
        """Check if request is allowed under rate limits.

        Args:
            request: FastAPI request object
            user_id: Optional user ID for user-based limiting
            endpoint: Optional endpoint for endpoint-based limiting

        Returns:
            Whether request is allowed
        """
        # Clean up old entries periodically
        self._cleanup_old_entries()

        # Generate rate limiting keys
        client_ip = self._get_client_ip(request)
        keys = [f"ip:{client_ip}"]

        if user_id:
            keys.append(f"user:{user_id}")

        if endpoint:
            keys.append(f"endpoint:{endpoint}")

        # Check all applicable rate limits
        for key in keys:
            if not self._consume_token(key):
                logger.warning(f"Rate limit exceeded for key: {key}")
                return False

        # Track request for sliding window
        current_minute = int(time.time() / 60)
        for key in keys:
            self.request_counts[key].append(current_minute)
            # Keep only last 2 minutes of data
            while self.request_counts[key] and self.request_counts[key][0] < current_minute - 1:
                self.request_counts[key].popleft()

        return True

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Check for forwarded IP headers
        forwarded_ips = request.headers.get("X-Forwarded-For")
        if forwarded_ips:
            return forwarded_ips.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to client host
        if request.client:
            return request.client.host

        return "unknown"

    def get_rate_limit_info(
        self,
        request: Request,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> Dict[str, int]:
        """Get current rate limit information.

        Args:
            request: FastAPI request object
            user_id: Optional user ID
            endpoint: Optional endpoint

        Returns:
            Dictionary with rate limit information
        """
        client_ip = self._get_client_ip(request)
        keys = [f"ip:{client_ip}"]

        if user_id:
            keys.append(f"user:{user_id}")

        if endpoint:
            keys.append(f"endpoint:{endpoint}")

        info = {}
        current_minute = int(time.time() / 60)

        for key in keys:
            # Get current token count
            tokens, _ = self._get_bucket(key)

            # Get request count for current minute
            request_count = len([
                minute for minute in self.request_counts[key]
                if minute == current_minute
            ])

            info[key] = {
                "current_tokens": int(tokens),
                "requests_this_minute": request_count,
                "max_burst": self.burst_size
            }

        return info


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for more precise control."""

    def __init__(self, requests_per_minute: int = 60):
        """Initialize sliding window rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, deque] = defaultdict(deque)

    async def is_allowed(self, key: str) -> bool:
        """Check if request is allowed.

        Args:
            key: Rate limiting key

        Returns:
            Whether request is allowed
        """
        now = time.time()

        # Add current request
        self.requests[key].append(now)

        # Remove old requests (older than 1 minute)
        cutoff = now - 60
        while self.requests[key] and self.requests[key][0] < cutoff:
            self.requests[key].popleft()

        # Check if under limit
        if len(self.requests[key]) <= self.requests_per_minute:
            return True

        # Remove the current request since it's over the limit
        self.requests[key].pop()
        return False


# Global rate limiter instances
api_rate_limiter = RateLimiter(
    requests_per_minute=120,  # 120 requests per minute for general API
    burst_size=20
)

workflow_rate_limiter = SlidingWindowRateLimiter(
    requests_per_minute=30  # 30 workflow starts per minute
)

recommendation_rate_limiter = RateLimiter(
    requests_per_minute=60,  # 60 recommendation requests per minute
    burst_size=10
)


async def check_api_rate_limit(request: Request, user_id: Optional[str] = None) -> None:
    """Check API rate limit and raise exception if exceeded.

    Args:
        request: FastAPI request object
        user_id: Optional user ID

    Raises:
        RateLimitException: If rate limit exceeded
    """
    allowed = await api_rate_limiter.is_allowed(request, user_id)
    if not allowed:
        raise RateLimitException(
            detail="Too many requests. Please try again later."
        )


async def check_workflow_rate_limit(user_id: str) -> None:
    """Check workflow rate limit and raise exception if exceeded.

    Args:
        user_id: User ID for rate limiting

    Raises:
        RateLimitException: If rate limit exceeded
    """
    allowed = await workflow_rate_limiter.is_allowed(f"user:{user_id}")
    if not allowed:
        raise RateLimitException(
            detail="Too many workflow starts. Please wait before starting another."
        )


async def check_recommendation_rate_limit(request: Request, user_id: Optional[str] = None) -> None:
    """Check recommendation rate limit and raise exception if exceeded.

    Args:
        request: FastAPI request object
        user_id: Optional user ID

    Raises:
        RateLimitException: If rate limit exceeded
    """
    allowed = await recommendation_rate_limiter.is_allowed(request, user_id)
    if not allowed:
        raise RateLimitException(
            detail="Too many recommendation requests. Please try again later."
        )