"""Pre-validated ID registry for RecoBeat compatibility.

Maintains a local registry of Spotify IDs that are known to be missing
or invalid in RecoBeat to skip futile API calls.
"""

import structlog
from typing import Optional
from datetime import datetime, timezone

from .cache import cache_manager

logger = structlog.get_logger(__name__)


class RecoBeatIDRegistry:
    """Registry for tracking RecoBeat ID availability and validation status.
    
    Prevents repeated conversion attempts for IDs known to be missing
    in RecoBeat, reducing API latency and cost.
    """
    
    # Cache key prefixes
    MISSING_ID_PREFIX = "reccobeat:missing:"
    VALIDATED_ID_PREFIX = "reccobeat:validated:"
    REVERSE_VALIDATED_ID_PREFIX = "reccobeat:reverse_validated:"  # RecoBeat -> Spotify
    
    # TTLs for different states - optimized for rate limit mitigation
    MISSING_ID_TTL = 86400 * 90  # 90 days - missing IDs rarely appear suddenly
    VALIDATED_ID_TTL = 86400 * 180  # 180 days - validated IDs remain very stable
    
    @classmethod
    async def mark_missing(cls, spotify_id: str, reason: Optional[str] = None) -> None:
        """Mark a Spotify ID as missing/unavailable in RecoBeat.
        
        Args:
            spotify_id: Spotify track ID that failed conversion
            reason: Optional reason for marking as missing
        """
        key = f"{cls.MISSING_ID_PREFIX}{spotify_id}"
        
        data = {
            "spotify_id": spotify_id,
            "marked_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason or "ID not found in RecoBeat"
        }
        
        try:
            await cache_manager.cache.set(key, data, ttl=cls.MISSING_ID_TTL)
            logger.debug(f"Marked Spotify ID as missing in RecoBeat: {spotify_id}")
        except Exception as e:
            logger.warning(f"Error marking ID as missing: {e}")
    
    @classmethod
    async def mark_validated(cls, spotify_id: str, reccobeat_id: str) -> None:
        """Mark a Spotify ID as successfully validated with its RecoBeat ID.
        
        Stores bidirectional mapping for both Spotify->RecoBeat and RecoBeat->Spotify lookups.
        
        Args:
            spotify_id: Spotify track ID
            reccobeat_id: Corresponding RecoBeat ID
        """
        forward_key = f"{cls.VALIDATED_ID_PREFIX}{spotify_id}"
        reverse_key = f"{cls.REVERSE_VALIDATED_ID_PREFIX}{reccobeat_id}"
        
        forward_data = {
            "spotify_id": spotify_id,
            "reccobeat_id": reccobeat_id,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
        reverse_data = {
            "reccobeat_id": reccobeat_id,
            "spotify_id": spotify_id,
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Store both directions with same TTL
            await cache_manager.cache.set(forward_key, forward_data, ttl=cls.VALIDATED_ID_TTL)
            await cache_manager.cache.set(reverse_key, reverse_data, ttl=cls.VALIDATED_ID_TTL)
            logger.debug(f"Validated bidirectional ID mapping: {spotify_id} <-> {reccobeat_id}")
        except Exception as e:
            logger.warning(f"Error marking ID as validated: {e}")
    
    @classmethod
    async def is_known_missing(cls, spotify_id: str) -> bool:
        """Check if a Spotify ID is known to be missing in RecoBeat.
        
        Args:
            spotify_id: Spotify track ID to check
            
        Returns:
            True if ID is known to be missing
        """
        key = f"{cls.MISSING_ID_PREFIX}{spotify_id}"
        
        try:
            data = await cache_manager.cache.get(key)
            return data is not None
        except Exception as e:
            logger.warning(f"Error checking missing ID status: {e}")
            return False
    
    @classmethod
    async def get_validated_id(cls, spotify_id: str) -> Optional[str]:
        """Get the validated RecoBeat ID for a Spotify ID if cached.
        
        Args:
            spotify_id: Spotify track ID
            
        Returns:
            RecoBeat ID if validated, None otherwise
        """
        key = f"{cls.VALIDATED_ID_PREFIX}{spotify_id}"
        
        try:
            data = await cache_manager.cache.get(key)
            if data:
                return data.get("reccobeat_id")
        except Exception as e:
            logger.warning(f"Error retrieving validated ID: {e}")
        
        return None
    
    @classmethod
    async def bulk_check_missing(cls, spotify_ids: list[str]) -> tuple[list[str], list[str]]:
        """Bulk check which IDs are known to be missing and which need validation.
        
        Filter out known-bad IDs before making API calls.
        
        Args:
            spotify_ids: List of Spotify track IDs
            
        Returns:
            Tuple of (ids_to_check, known_missing_ids)
        """
        ids_to_check = []
        known_missing = []
        
        for spotify_id in spotify_ids:
            if await cls.is_known_missing(spotify_id):
                known_missing.append(spotify_id)
            else:
                ids_to_check.append(spotify_id)
        
        if known_missing:
            logger.info(
                f"Skipped {len(known_missing)} known-missing IDs",
                total_ids=len(spotify_ids),
                skip_rate=f"{len(known_missing)/len(spotify_ids)*100:.1f}%"
            )
        
        return ids_to_check, known_missing
    
    @classmethod
    async def bulk_get_validated(cls, spotify_ids: list[str]) -> dict[str, str]:
        """Bulk retrieve validated RecoBeat IDs from cache.
        
        Return cached conversions without API calls.
        
        Args:
            spotify_ids: List of Spotify track IDs
            
        Returns:
            Dictionary mapping Spotify IDs to RecoBeat IDs for validated entries
        """
        validated_mapping = {}
        
        for spotify_id in spotify_ids:
            reccobeat_id = await cls.get_validated_id(spotify_id)
            if reccobeat_id:
                validated_mapping[spotify_id] = reccobeat_id
        
        if validated_mapping:
            logger.info(
                f"Retrieved {len(validated_mapping)} validated IDs from cache",
                total_requested=len(spotify_ids),
                cache_hit_rate=f"{len(validated_mapping)/len(spotify_ids)*100:.1f}%"
            )
        
        return validated_mapping
    
    @classmethod
    async def get_spotify_id_for_reccobeat(cls, reccobeat_id: str) -> Optional[str]:
        """Get the Spotify ID for a RecoBeat ID if cached (reverse lookup).
        
        Args:
            reccobeat_id: RecoBeat track ID
            
        Returns:
            Spotify ID if validated, None otherwise
        """
        key = f"{cls.REVERSE_VALIDATED_ID_PREFIX}{reccobeat_id}"
        
        try:
            data = await cache_manager.cache.get(key)
            if data:
                return data.get("spotify_id")
        except Exception as e:
            logger.warning(f"Error retrieving reverse validated ID: {e}")
        
        return None
    
    @classmethod
    async def bulk_get_spotify_ids(cls, reccobeat_ids: list[str]) -> dict[str, str]:
        """Bulk retrieve Spotify IDs from RecoBeat IDs (reverse lookup).
        
        Args:
            reccobeat_ids: List of RecoBeat track IDs
            
        Returns:
            Dictionary mapping RecoBeat IDs to Spotify IDs for validated entries
        """
        reverse_mapping = {}
        
        for reccobeat_id in reccobeat_ids:
            spotify_id = await cls.get_spotify_id_for_reccobeat(reccobeat_id)
            if spotify_id:
                reverse_mapping[reccobeat_id] = spotify_id
        
        if reverse_mapping:
            logger.info(
                f"Retrieved {len(reverse_mapping)} reverse validated IDs from cache",
                total_requested=len(reccobeat_ids),
                cache_hit_rate=f"{len(reverse_mapping)/len(reccobeat_ids)*100:.1f}%"
            )
        
        return reverse_mapping
    
    @classmethod
    async def get_registry_stats(cls) -> dict[str, int]:
        """Get statistics about the ID registry.
        
        Returns:
            Dictionary with registry statistics
        """
        # Note: This is a simplified implementation
        # In a production system with Redis, you'd use SCAN or key counting
        return {
            "note": "Registry stats require Redis SCAN for accurate counts",
            "description": "Use cache stats endpoint for hit/miss rates"
        }


# Singleton registry instance
id_registry = RecoBeatIDRegistry()

