"""Caching utilities for the agentic system."""

import asyncio
import hashlib
import pickle
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse
import structlog

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


logger = structlog.get_logger(__name__)


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
            if entry["expires_at"] and datetime.now(timezone.utc) > entry["expires_at"]:
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
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
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
    """Redis-based cache implementation with connection pooling.

    Optimized with a persistent connection pool for better performance.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "agentic:"):
        """Initialize Redis cache with connection pooling.

        Args:
            redis_url: Redis connection URL
            prefix: Key prefix for namespacing
        """
        super().__init__()
        self.redis_url, self._using_tls = self._prepare_redis_url(redis_url)
        self.prefix = prefix
        self.redis_client = None
        self._pool_initialized = False

    def _prepare_redis_url(self, redis_url: str) -> Tuple[str, bool]:
        """Ensure providers that require TLS (e.g., Upstash) don't drop connections."""
        parsed = urlparse(redis_url)
        using_tls = parsed.scheme == "rediss"

        if parsed.scheme == "redis" and parsed.hostname and parsed.hostname.endswith("upstash.io"):
            parsed = parsed._replace(scheme="rediss")
            redis_url = urlunparse(parsed)
            using_tls = True
            logger.info("Upgrading Redis URL to TLS for Upstash host", host=parsed.hostname)

        return redis_url, using_tls

    async def _get_client(self) -> redis.Redis:
        """Get or create Redis client with optimized connection pool.

        Uses persistent connection pool with tuned parameters for better performance
        under high concurrency.
        """
        if self.redis_client is None:
            # Create connection pool with optimized settings
            connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=50,  # Increased from default 10
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,  # Health check every 30 seconds
                decode_responses=False,  # We use pickle, so keep as bytes
            )
            self.redis_client = redis.Redis(connection_pool=connection_pool)
            self._pool_initialized = True
            logger.info(
                "Initialized Redis connection pool with 50 max connections",
                using_tls=self._using_tls
            )
        return self.redis_client

    async def close(self):
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            await self.redis_client.close()
            await self.redis_client.connection_pool.disconnect()
            self.redis_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()

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
            # Increased cache size to 5000 for better hit rates with rate limiting
            self.cache = MemoryCache(max_size=5000)
            logger.info("Using in-memory cache (no Valkey/Redis URL provided)")

        # Cache TTL defaults (in seconds) - optimized for rate limit mitigation
        self.default_ttl = {
            "user_profile": 3600,  # 1 hour
            "top_tracks": 1800,    # 30 minutes
            "top_artists": 1800,   # 30 minutes
            "artist_top_tracks": 7200,  # 2 hours - increased to minimize rate limit hits
            "recommendations": 1800,  # 30 minutes - increased from 15 to reduce API load
            "mood_analysis": 3600,  # 1 hour
            "workflow_state": 300,  # 5 minutes
            "track_details": 7200,  # 2 hours - track details are stable, increased
            "workflow_artifacts": 1800,  # 30 minutes - workflow artifacts
            "validated_seeds": 7200,  # 2 hours - validated seed lists are stable
            "artist_enrichment": 3600,  # 1 hour - increased from 30min for stability
            "popular_mood_cache": 14400,  # 4 hours - popular mood recommendations
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

    async def get_user_top_artists(
        self,
        user_id: str,
        time_range: str = "medium_term",
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached user top artists.

        Caches user top artists to avoid repeated fetches.

        Args:
            user_id: User ID
            time_range: Time range for artists
            limit: Number of artists

        Returns:
            Top artists or None if not cached
        """
        key = self._make_cache_key("top_artists", user_id, time_range, limit)
        return await self.cache.get(key)

    async def set_user_top_artists(
        self,
        user_id: str,
        artists: List[Dict[str, Any]],
        time_range: str = "medium_term",
        limit: int = 20
    ) -> None:
        """Cache user top artists.

        Caches user top artists to avoid repeated fetches.

        Args:
            user_id: User ID
            artists: Top artists data
            time_range: Time range for artists
            limit: Number of artists
        """
        key = self._make_cache_key("top_artists", user_id, time_range, limit)
        ttl = self.default_ttl["top_artists"]
        await self.cache.set(key, artists, ttl)

    def _normalize_market_for_cache(self, market: Optional[str]) -> str:
        """Normalize market parameter for cache key generation.
        
        Converts None to "global" for consistent cache keys.
        
        Args:
            market: Optional ISO 3166-1 alpha-2 country code (None for global)
            
        Returns:
            Market code or "global" if None
        """
        return market if market is not None else "global"

    async def get_artist_top_tracks_cache(
        self,
        artist_id: str,
        market: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached Spotify top tracks for an artist."""
        cache_market = self._normalize_market_for_cache(market)
        key = self._make_cache_key("artist_top_tracks", artist_id, cache_market)
        return await self.cache.get(key)

    async def set_artist_top_tracks_cache(
        self,
        artist_id: str,
        tracks: List[Dict[str, Any]],
        market: Optional[str] = None
    ) -> None:
        """Cache Spotify top tracks for an artist."""
        cache_market = self._normalize_market_for_cache(market)
        key = self._make_cache_key("artist_top_tracks", artist_id, cache_market)
        ttl = self.default_ttl["artist_top_tracks"]
        await self.cache.set(key, tracks, ttl)

    async def get_anchor_tracks(
        self,
        user_id: str,
        mood_prompt: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached anchor tracks for a user and mood.

        Caches anchor track selections to avoid repeated expensive searches
        and filtering.

        Args:
            user_id: User ID
            mood_prompt: Mood prompt used for anchor selection

        Returns:
            Anchor tracks or None if not cached
        """
        key = self._make_cache_key("anchor_tracks", user_id, mood_prompt)
        return await self.cache.get(key)

    async def set_anchor_tracks(
        self,
        user_id: str,
        mood_prompt: str,
        anchor_tracks: List[Dict[str, Any]]
    ) -> None:
        """Cache anchor tracks for a user and mood.

        Caches anchor track selections to avoid repeated expensive searches
        and filtering.

        Args:
            user_id: User ID
            mood_prompt: Mood prompt used for anchor selection
            anchor_tracks: Selected anchor tracks
        """
        key = self._make_cache_key("anchor_tracks", user_id, mood_prompt)
        # Cache anchor tracks for 15 minutes (they should be recomputed periodically)
        await self.cache.set(key, anchor_tracks, ttl=900)

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

    async def get_track_details(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get cached track details.

        Args:
            track_id: Spotify track ID

        Returns:
            Track details or None if not cached
        """
        key = self._make_cache_key("track_details", track_id)
        return await self.cache.get(key)

    async def set_track_details(self, track_id: str, track_data: Dict[str, Any]) -> None:
        """Cache track details.

        Args:
            track_id: Spotify track ID
            track_data: Track details data
        """
        key = self._make_cache_key("track_details", track_id)
        ttl = self.default_ttl["track_details"]
        await self.cache.set(key, track_data, ttl)

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

    async def close(self):
        """Close cache connections gracefully.
        
        Proper cleanup for distributed cache connections.
        """
        if isinstance(self.cache, RedisCache):
            await self.cache.close()
            logger.info("Closed Redis/Valkey cache connection")
    
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

    async def get_workflow_artifacts(
        self,
        user_id: str,
        mood_prompt: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached workflow artifacts for reuse across iterations.
        
        Persist workflow artifacts so similar prompts can reuse validated
        seeds, artist lists, and audio features.
        
        Args:
            user_id: User ID
            mood_prompt: Mood prompt (used as cache key)
            
        Returns:
            Cached workflow artifacts or None
        """
        key = self._make_cache_key("workflow_artifacts", user_id, mood_prompt)
        return await self.cache.get(key)
    
    async def set_workflow_artifacts(
        self,
        user_id: str,
        mood_prompt: str,
        artifacts: Dict[str, Any]
    ) -> None:
        """Cache workflow artifacts for reuse.
        
        Store validated seeds, artist lists, audio features
        to avoid recomputation on similar prompts.
        
        Args:
            user_id: User ID
            mood_prompt: Mood prompt (used as cache key)
            artifacts: Workflow artifacts to cache (seeds, artists, features, etc.)
        """
        key = self._make_cache_key("workflow_artifacts", user_id, mood_prompt)
        ttl = self.default_ttl["workflow_artifacts"]
        
        # Add timestamp for diffing later
        artifacts["cached_at"] = datetime.now(timezone.utc).isoformat()
        
        await self.cache.set(key, artifacts, ttl)
        logger.info(
            f"Cached workflow artifacts for user {user_id}",
            artifact_keys=list(artifacts.keys())
        )
    
    async def get_artist_enrichment(
        self,
        artist_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Get cached enriched artist data.
        
        Cache artist enrichment (top tracks, audio features)
        to avoid repeated fetches.
        
        Args:
            artist_ids: List of artist IDs (sorted for consistent caching)
            
        Returns:
            Cached artist enrichment data or None
        """
        sorted_ids = sorted(artist_ids)
        key = self._make_cache_key("artist_enrichment", *sorted_ids)
        return await self.cache.get(key)
    
    async def set_artist_enrichment(
        self,
        artist_ids: List[str],
        enrichment_data: Dict[str, Any]
    ) -> None:
        """Cache enriched artist data.
        
        Store artist top tracks and audio features
        for reuse across workflows.
        
        Args:
            artist_ids: List of artist IDs (sorted for consistent caching)
            enrichment_data: Enriched artist data with tracks and audio features
        """
        sorted_ids = sorted(artist_ids)
        key = self._make_cache_key("artist_enrichment", *sorted_ids)
        ttl = self.default_ttl["artist_enrichment"]
        await self.cache.set(key, enrichment_data, ttl)
        logger.info(f"Cached enrichment data for {len(artist_ids)} artists")

    async def warm_user_cache(
        self,
        user_id: str,
        spotify_service,
        reccobeat_service,
        access_token: str
    ) -> None:
        """Proactively warm cache with user data in background.

        Fire-and-forget cache warming to pre-populate frequently accessed data.

        Args:
            user_id: User ID
            spotify_service: Spotify service for fetching data
            reccobeat_service: RecoBeat service for fetching data
            access_token: Spotify access token
        """
        async def warm_cache_background():
            """Background task to warm cache."""
            try:
                logger.info(f"Warming cache for user {user_id}")

                # Warm top tracks cache
                top_tracks = await spotify_service.get_user_top_tracks(
                    access_token=access_token,
                    limit=20,
                    time_range="medium_term",
                    user_id=user_id
                )

                # Warm top artists cache
                top_artists = await spotify_service.get_user_top_artists(
                    access_token=access_token,
                    limit=15,
                    time_range="medium_term",
                    user_id=user_id
                )

                # Warm audio features cache for top tracks
                if top_tracks and reccobeat_service:
                    track_ids = [track.get('id') for track in top_tracks if track.get('id')]
                    if track_ids:
                        await reccobeat_service.get_tracks_audio_features(track_ids)

                logger.info(f"Successfully warmed cache for user {user_id}: "
                           f"{len(top_tracks)} tracks, {len(top_artists)} artists")

            except Exception as e:
                logger.warning(f"Error warming cache for user {user_id}: {e}")

        # Fire and forget - don't await
        asyncio.create_task(warm_cache_background())
        logger.info(f"Started background cache warming for user {user_id}")


class CacheManagerProxy:
    """Proxy that always forwards to the current CacheManager instance."""

    def __init__(self, manager: CacheManager):
        self._manager = manager

    def set_manager(self, manager: CacheManager) -> None:
        self._manager = manager

    def get_manager(self) -> CacheManager:
        return self._manager

    def __getattr__(self, item: str):
        return getattr(self._manager, item)


# Global cache manager proxy - swapped to Valkey-backed instances at runtime
cache_manager = CacheManagerProxy(CacheManager())


def set_cache_manager(manager: CacheManager) -> None:
    """Replace the active CacheManager used across the application."""
    cache_manager.set_manager(manager)


def get_cache_manager() -> CacheManager:
    """Return the currently active CacheManager instance."""
    return cache_manager.get_manager()


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
