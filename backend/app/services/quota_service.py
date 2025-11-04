"""Service for managing per-user playlist creation quota usage."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Optional

import structlog

from app.agents.core.cache import cache_manager
from app.repositories.playlist_repository import PlaylistRepository

logger = structlog.get_logger(__name__)


class QuotaService:
    """Provide cached access to a user's daily playlist creation usage."""

    _lock_registry: Dict[int, asyncio.Lock] = {}
    _registry_lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, playlist_repo: PlaylistRepository):
        self.playlist_repo = playlist_repo
        self._cache = cache_manager.cache

    async def get_daily_usage(self, user_id: int) -> int:
        """Return the number of playlists the user has created today.

        Uses a cache (Valkey when configured, in-memory otherwise) keyed by user
        and UTC calendar day. The cache TTL is set to the number of seconds until
        the next midnight in UTC so the count naturally resets each day.
        """
        cache_date = self._current_date()
        cache_key = self._cache_key(user_id, cache_date)

        cached_usage: Optional[int] = await self._cache.get(cache_key)
        if cached_usage is not None:
            logger.debug("Quota usage cache hit", user_id=user_id, usage=cached_usage)
            return cached_usage

        usage = await self.playlist_repo.count_user_playlists_created_today(user_id)
        await self._cache.set(cache_key, usage, ttl=self._ttl_until_midnight())
        logger.debug("Quota usage cache miss", user_id=user_id, usage=usage)
        return usage

    async def increment_daily_usage(self, user_id: int, delta: int = 1) -> int:
        """Increase the cached usage count when a playlist is created.

        If the cache entry is missing, we recompute from the database to avoid
        drifting out of sync.
        """
        cache_date = self._current_date()
        cache_key = self._cache_key(user_id, cache_date)

        user_lock = await self._get_user_lock(user_id)

        async with user_lock:
            cached_usage: Optional[int] = await self._cache.get(cache_key)
            if cached_usage is None:
                logger.debug("Quota usage cache warm-up on increment", user_id=user_id)
                usage = await self.playlist_repo.count_user_playlists_created_today(user_id)
            else:
                usage = cached_usage + delta

            await self._cache.set(cache_key, usage, ttl=self._ttl_until_midnight())
            return usage

    async def invalidate_daily_usage(self, user_id: int, cache_date: Optional[date] = None) -> None:
        """Invalidate the cached usage entry."""
        cache_date = cache_date or self._current_date()
        cache_key = self._cache_key(user_id, cache_date)
        await self._cache.delete(cache_key)

    @staticmethod
    def _current_date() -> date:
        """Current UTC date used for quota buckets."""
        return datetime.now(timezone.utc).date()

    @staticmethod
    def _cache_key(user_id: int, cache_date: date) -> str:
        return f"quota_usage:{user_id}:{cache_date.isoformat()}"

    @staticmethod
    def _ttl_until_midnight() -> int:
        """Seconds until the next UTC midnight, minimum one minute."""
        now = datetime.now(timezone.utc)
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        ttl = int((tomorrow - now).total_seconds())
        return max(ttl, 60)

    async def _get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Return a lock dedicated to the user for cache mutations."""
        try:
            return self._lock_registry[user_id]
        except KeyError:
            async with self._registry_lock:
                return self._lock_registry.setdefault(user_id, asyncio.Lock())
