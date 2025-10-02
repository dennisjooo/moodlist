"""Caching utilities for the agentic system."""

import asyncio
import hashlib
import json
import pickle
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


logger = logging.getLogger(__name__)


class Cache:
    """Generic cache interface."""

    def __init__(self):
        """Initialize cache."""
        self.hit_count = 0
        self.miss_count = 0

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            Whether key exists
        """
        raise NotImplementedError

    async def clear(self) -> None:
        """Clear all cache entries."""
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0

        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total_requests,
            "hit_rate": hit_rate
        }


class MemoryCache(Cache):
    """In-memory cache implementation."""

    def __init__(self, max_size: int = 1000):
        """Initialize memory cache.

        Args:
            max_size: Maximum number of entries
        """
        super().__init__()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.access_order: List[str] = []

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        if key in self.cache:
            entry = self.cache[key]

            # Check if expired
            if entry["expires_at"] and datetime.utcnow() > entry["expires_at"]:
                del self.cache[key]
                if key in self.access_order:
                    self.access_order.remove(key)
                self.miss_count += 1
                return None

            # Update access order for LRU
            if key in self.access_order:
                self.access_order.remove(key)
            self.access_order.append(key)

            self.hit_count += 1
            return entry["value"]

        self.miss_count += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in memory cache."""
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.utcnow()
        }

        # Update access order
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

        # Implement LRU eviction
        if len(self.cache) > self.max_size:
            await self._evict_lru()

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_order:
            self.access_order.remove(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        entry = await self.get(key)
        return entry is not None

    async def clear(self) -> None:
        """Clear memory cache."""
        self.cache.clear()
        self.access_order.clear()

    async def _evict_lru(self):
        """Evict least recently used entries."""
        if not self.access_order:
            return

        # Remove oldest entries (first 10% of max size)
        to_remove = len(self.access_order) // 10
        if to_remove == 0:
            to_remove = 1

        for i in range(to_remove):
            if self.access_order:
                oldest_key = self.access_order.pop(0)
                if oldest_key in self.cache:
                    del self.cache[oldest_key]


class RedisCache(Cache):
    """Redis-based cache implementation."""

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "agentic:"):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
        """
        super().__init__()
        self.redis_url = redis_url
        self.prefix = prefix
        self.redis_client = None

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url)
        return self.redis_client

    def _make_key(self, key: str) -> str:
        """Create namespaced key.

        Args:
            key: Original key

        Returns:
            Namespaced key
        """
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            client = await self._get_client()
            namespaced_key = self._make_key(key)

            value = await client.get(namespaced_key)
            if value:
                self.hit_count += 1
                return pickle.loads(value)
            else:
                self.miss_count += 1
                return None

        except Exception as e:
            logger.error(f"Error getting from Redis cache: {e}")
            self.miss_count += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis cache."""
        try:
            client = await self._get_client()
            namespaced_key = self._make_key(key)

            pickled_value = pickle.dumps(value)
            if ttl:
                await client.setex(namespaced_key, ttl, pickled_value)
            else:
                await client.set(namespaced_key, pickled_value)

        except Exception as e:
            logger.error(f"Error setting Redis cache: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from Redis cache."""
        try:
            client = await self._get_client()
            namespaced_key = self._make_key(key)
            await client.delete(namespaced_key)

        except Exception as e:
            logger.error(f"Error deleting from Redis cache: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            client = await self._get_client()
            namespaced_key = self._make_key(key)
            return await client.exists(namespaced_key) > 0

        except Exception as e:
            logger.error(f"Error checking Redis cache: {e}")
            return False

    async def clear(self) -> None:
        """Clear Redis cache (with prefix)."""
        try:
            client = await self._get_client()

            # Get all keys with prefix
            pattern = f"{self.prefix}*"
            keys = await client.keys(pattern)

            if keys:
                await client.delete(*keys)

        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")


class CacheManager:
    """Manager for different cache types and strategies."""

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize cache manager.

        Args:
            redis_url: Optional Redis/Valkey URL for distributed caching
        """
        # Choose cache implementation
        if redis_url and REDIS_AVAILABLE:
            self.cache = RedisCache(redis_url)
            logger.info(f"Using Valkey/Redis cache at {redis_url}")
        else:
            self.cache = MemoryCache(max_size=1000)
            logger.info("Using in-memory cache (no Valkey/Redis URL provided)")

        # Cache TTL defaults (in seconds)
        self.default_ttl = {
            "user_profile": 3600,  # 1 hour
            "top_tracks": 1800,    # 30 minutes
            "top_artists": 1800,   # 30 minutes
            "recommendations": 900,  # 15 minutes
            "mood_analysis": 3600,  # 1 hour
            "workflow_state": 300   # 5 minutes
        }

    def _make_cache_key(self, category: str, *args) -> str:
        """Create a standardized cache key.

        Args:
            category: Cache category
            *args: Key components

        Returns:
            Standardized cache key
        """
        # Create deterministic key from components
        key_components = [category] + [str(arg) for arg in args]
        key_string = ":".join(key_components)

        # Hash for consistent length
        return hashlib.md5(key_string.encode()).hexdigest()

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user profile.

        Args:
            user_id: User ID

        Returns:
            User profile or None if not cached
        """
        key = self._make_cache_key("user_profile", user_id)
        return await self.cache.get(key)

    async def set_user_profile(self, user_id: str, profile: Dict[str, Any]) -> None:
        """Cache user profile.

        Args:
            user_id: User ID
            profile: User profile data
        """
        key = self._make_cache_key("user_profile", user_id)
        ttl = self.default_ttl["user_profile"]
        await self.cache.set(key, profile, ttl)

    async def get_user_top_tracks(
        self,
        user_id: str,
        time_range: str = "medium_term",
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached user top tracks.

        Args:
            user_id: User ID
            time_range: Time range for tracks
            limit: Number of tracks

        Returns:
            Top tracks or None if not cached
        """
        key = self._make_cache_key("top_tracks", user_id, time_range, limit)
        return await self.cache.get(key)

    async def set_user_top_tracks(
        self,
        user_id: str,
        tracks: List[Dict[str, Any]],
        time_range: str = "medium_term",
        limit: int = 20
    ) -> None:
        """Cache user top tracks.

        Args:
            user_id: User ID
            tracks: Top tracks data
            time_range: Time range for tracks
            limit: Number of tracks
        """
        key = self._make_cache_key("top_tracks", user_id, time_range, limit)
        ttl = self.default_ttl["top_tracks"]
        await self.cache.set(key, tracks, ttl)

    async def get_mood_analysis(self, mood_prompt: str) -> Optional[Dict[str, Any]]:
        """Get cached mood analysis.

        Args:
            mood_prompt: Original mood prompt

        Returns:
            Mood analysis or None if not cached
        """
        key = self._make_cache_key("mood_analysis", mood_prompt)
        return await self.cache.get(key)

    async def set_mood_analysis(self, mood_prompt: str, analysis: Dict[str, Any]) -> None:
        """Cache mood analysis.

        Args:
            mood_prompt: Original mood prompt
            analysis: Mood analysis data
        """
        key = self._make_cache_key("mood_analysis", mood_prompt)
        ttl = self.default_ttl["mood_analysis"]
        await self.cache.set(key, analysis, ttl)

    async def get_workflow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cached workflow state.

        Args:
            session_id: Workflow session ID

        Returns:
            Workflow state or None if not cached
        """
        key = self._make_cache_key("workflow_state", session_id)
        return await self.cache.get(key)

    async def set_workflow_state(self, session_id: str, state: Dict[str, Any]) -> None:
        """Cache workflow state.

        Args:
            session_id: Workflow session ID
            state: Workflow state data
        """
        key = self._make_cache_key("workflow_state", session_id)
        ttl = self.default_ttl["workflow_state"]
        await self.cache.set(key, state, ttl)

    async def invalidate_user_data(self, user_id: str) -> None:
        """Invalidate all cached data for a user.

        Args:
            user_id: User ID
        """
        # This is a simplified implementation
        # In a real system, you might want to track all keys for a user
        logger.info(f"Invalidating cache for user {user_id}")

        # For now, we'll rely on TTL expiration
        # In a production system, you might implement key tagging

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Cache statistics
        """
        return {
            "cache_type": "redis" if isinstance(self.cache, RedisCache) else "memory",
            "cache_stats": self.cache.get_stats(),
            "default_ttl": self.default_ttl
        }


# Global cache manager - will be initialized with Valkey when available
cache_manager = CacheManager()


class CacheDecorator:
    """Decorator for caching function results."""

    def __init__(
        self,
        category: str,
        ttl: Optional[int] = None,
        key_func: Optional[callable] = None
    ):
        """Initialize cache decorator.

        Args:
            category: Cache category for key generation
            ttl: Custom TTL for this cache entry
            key_func: Custom function for generating cache keys
        """
        self.category = category
        self.ttl = ttl
        self.key_func = key_func

    def __call__(self, func):
        """Apply cache decorator to function."""
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if self.key_func:
                cache_key = self.key_func(*args, **kwargs)
            else:
                # Default key generation
                key_components = [self.category, func.__name__]
                key_components.extend([str(arg) for arg in args])
                key_components.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_key = hashlib.md5(":".join(key_components).encode()).hexdigest()

            # Try to get from cache
            cached_result = await cache_manager.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result

            # Execute function
            logger.debug(f"Cache miss for {func.__name__}")
            result = await func(*args, **kwargs)

            # Cache result
            ttl = self.ttl or cache_manager.default_ttl.get(self.category, 300)
            await cache_manager.cache.set(cache_key, result, ttl)

            return result

        return wrapper