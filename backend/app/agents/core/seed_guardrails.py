"""Seed selection guardrails for RecoBeat API compatibility.

Maintains a persistent allow/deny list to prevent repeating failing seed
combinations and provides intelligent fallback strategies.
"""

import hashlib
import structlog
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from .cache import cache_manager

logger = structlog.get_logger(__name__)


class SeedGuardrails:
    """Manages seed selection validation and guardrails for RecoBeat API."""

    # Cache key prefix for denied combinations
    DENY_LIST_PREFIX = "seed_guardrails:denied:"
    DENY_LIST_TTL = 3600 * 24  # 24 hours - give failed combinations a fresh chance daily

    # Error patterns that indicate permanent failures vs retriable ones
    PERMANENT_ERROR_PATTERNS = [
        "invalid parameters",
        "validation error",
        "bad request",
        "too many negative seeds",
        "overlapping ids",
        "empty or whitespace"
    ]

    @staticmethod
    def _make_combination_key(
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        feature_params: Optional[Dict] = None
    ) -> str:
        """Create a unique key for a seed combination.

        Args:
            seeds: List of seed track IDs
            negative_seeds: Optional negative seed track IDs
            feature_params: Optional audio feature parameters

        Returns:
            Hash key representing this combination
        """
        # Sort seeds for consistent hashing
        sorted_seeds = sorted(seeds) if seeds else []
        sorted_negatives = sorted(negative_seeds) if negative_seeds else []

        # Create a deterministic representation
        key_parts = [
            "seeds:" + ",".join(sorted_seeds),
            "negatives:" + ",".join(sorted_negatives),
        ]

        # Include feature params if provided (simplified - only include if present)
        if feature_params:
            feature_str = ",".join(f"{k}:{v}" for k, v in sorted(feature_params.items()) if v is not None)
            if feature_str:
                key_parts.append("features:" + feature_str)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    @classmethod
    async def is_combination_denied(
        cls,
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        feature_params: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if a seed combination is on the deny list.

        Args:
            seeds: List of seed track IDs
            negative_seeds: Optional negative seed track IDs
            feature_params: Optional audio feature parameters

        Returns:
            Tuple of (is_denied, reason)
        """
        combination_key = cls._make_combination_key(seeds, negative_seeds, feature_params)
        cache_key = f"{cls.DENY_LIST_PREFIX}{combination_key}"

        try:
            denied_info = await cache_manager.cache.get(cache_key)
            if denied_info:
                reason = denied_info.get("reason", "Previously failed")
                logger.info(
                    f"Seed combination denied by guardrails: {reason}",
                    seed_count=len(seeds),
                    negative_seed_count=len(negative_seeds) if negative_seeds else 0
                )
                return True, reason
        except Exception as e:
            logger.warning(f"Error checking deny list: {e}")

        return False, None

    @classmethod
    async def add_to_deny_list(
        cls,
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        feature_params: Optional[Dict] = None,
        reason: str = "API failure"
    ) -> None:
        """Add a failing seed combination to the deny list.

        Args:
            seeds: List of seed track IDs
            negative_seeds: Optional negative seed track IDs
            feature_params: Optional audio feature parameters
            reason: Reason for denial
        """
        combination_key = cls._make_combination_key(seeds, negative_seeds, feature_params)
        cache_key = f"{cls.DENY_LIST_PREFIX}{combination_key}"

        denied_info = {
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed_count": len(seeds),
            "negative_seed_count": len(negative_seeds) if negative_seeds else 0
        }

        try:
            await cache_manager.cache.set(cache_key, denied_info, ttl=cls.DENY_LIST_TTL)
            logger.info(
                f"Added seed combination to deny list: {reason}",
                seed_count=len(seeds),
                negative_seed_count=len(negative_seeds) if negative_seeds else 0
            )
        except Exception as e:
            logger.warning(f"Error adding to deny list: {e}")

    @classmethod
    def should_skip_retry(cls, error_message: str) -> bool:
        """Determine if an error indicates a permanent failure that shouldn't be retried.

        Args:
            error_message: Error message from API or validation

        Returns:
            True if this error should skip retries
        """
        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in cls.PERMANENT_ERROR_PATTERNS)

    @classmethod
    def suggest_fallback_strategy(
        cls,
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        error_reason: Optional[str] = None
    ) -> Optional[Dict]:
        """Suggest a fallback strategy for failed seed combinations.

        Provides contextual fallbacks instead of abandoning the request entirely.

        Args:
            seeds: Original seed track IDs
            negative_seeds: Original negative seed track IDs
            error_reason: Reason for failure

        Returns:
            Dictionary with fallback strategy or None if no fallback available
        """
        if not seeds:
            return None

        fallback = {
            "strategy": "unknown",
            "seeds": seeds.copy(),
            "negative_seeds": None,
            "reason": ""
        }

        error_lower = (error_reason or "").lower()

        # Strategy 1: Drop negative seeds if they're causing issues
        if negative_seeds and ("negative" in error_lower or "ratio" in error_lower):
            fallback["strategy"] = "drop_negative_seeds"
            fallback["negative_seeds"] = None
            fallback["reason"] = "Dropped negative seeds due to ratio or compatibility issues"
            logger.info(f"Suggesting fallback: drop negative seeds ({len(negative_seeds)} removed)")
            return fallback

        # Strategy 2: Reduce negative seeds to safe ratio (< 50% of positive seeds)
        if negative_seeds and len(negative_seeds) >= len(seeds) * 0.5:
            max_negative = max(1, len(seeds) // 2 - 1)  # Keep it well under 50%
            fallback["strategy"] = "reduce_negative_seeds"
            fallback["negative_seeds"] = negative_seeds[:max_negative]
            fallback["reason"] = f"Reduced negative seeds from {len(negative_seeds)} to {max_negative}"
            logger.info(f"Suggesting fallback: reduce negative seeds to {max_negative}")
            return fallback

        # Strategy 3: Use only the first few seeds if we have too many
        if len(seeds) > 3:
            fallback["strategy"] = "reduce_seeds"
            fallback["seeds"] = seeds[:3]
            fallback["negative_seeds"] = None  # Also drop negatives when reducing seeds
            fallback["reason"] = f"Reduced seeds from {len(seeds)} to 3"
            logger.info("Suggesting fallback: reduce seeds to 3")
            return fallback

        # Strategy 4: Try without any negative seeds as last resort
        if negative_seeds:
            fallback["strategy"] = "remove_all_negatives"
            fallback["negative_seeds"] = None
            fallback["reason"] = "Removed all negative seeds as fallback"
            logger.info("Suggesting fallback: remove all negative seeds")
            return fallback

        # No fallback available
        return None

    @classmethod
    async def validate_and_auto_balance(
        cls,
        seeds: List[str],
        negative_seeds: Optional[List[str]] = None,
        size: int = 20
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Validate seed parameters and suggest auto-balancing if needed.

        Instead of rejecting bad parameters, attempts to auto-balance them.

        Args:
            seeds: List of seed track IDs
            negative_seeds: Optional negative seed track IDs
            size: Number of recommendations requested

        Returns:
            Tuple of (is_valid, error_message, suggested_params)
            If is_valid is False but suggested_params is provided, caller should
            retry with suggested_params.
        """
        # Basic validation
        if not seeds or any(not s or not s.strip() for s in seeds):
            return False, "Seeds contain empty or whitespace-only IDs", None

        if size < 1 or size > 100:
            return False, f"Invalid recommendation size: {size} (must be 1-100)", None

        # Check if this combination is denied
        is_denied, deny_reason = await cls.is_combination_denied(seeds, negative_seeds)
        if is_denied:
            # Suggest fallback instead of failing outright
            fallback = cls.suggest_fallback_strategy(seeds, negative_seeds, deny_reason)
            return False, f"Combination previously failed: {deny_reason}", fallback

        # Validate negative seeds if provided
        if negative_seeds:
            if any(not s or not s.strip() for s in negative_seeds):
                return False, "Negative seeds contain empty or whitespace-only IDs", None

            # Auto-balance: negative seeds should be < 50% of positive seeds
            if len(negative_seeds) >= len(seeds):
                max_negative = max(1, len(seeds) // 2)
                suggested = {
                    "seeds": seeds,
                    "negative_seeds": negative_seeds[:max_negative],
                    "size": size
                }
                logger.info(
                    f"Auto-balancing: reduced negative seeds from {len(negative_seeds)} to {max_negative}",
                    original_ratio=f"{len(negative_seeds)}/{len(seeds)}",
                    new_ratio=f"{max_negative}/{len(seeds)}"
                )
                return False, f"Auto-balanced: too many negative seeds ({len(negative_seeds)} >= {len(seeds)})", suggested

            # Check for overlap
            seed_set = set(seeds)
            negative_set = set(negative_seeds)
            overlap = seed_set & negative_set
            if overlap:
                # Auto-fix: remove overlapping IDs from negative seeds
                fixed_negatives = [ns for ns in negative_seeds if ns not in seed_set]
                if not fixed_negatives:
                    # All negatives overlapped, drop them entirely
                    suggested = {
                        "seeds": seeds,
                        "negative_seeds": None,
                        "size": size
                    }
                    logger.info("Auto-balancing: removed all negative seeds (all overlapped with seeds)")
                    return False, "Auto-balanced: removed overlapping negative seeds", suggested
                else:
                    suggested = {
                        "seeds": seeds,
                        "negative_seeds": fixed_negatives,
                        "size": size
                    }
                    logger.info(
                        f"Auto-balancing: removed {len(overlap)} overlapping negative seeds",
                        removed=list(overlap)[:3]
                    )
                    return False, f"Auto-balanced: removed {len(overlap)} overlapping IDs", suggested

        # All validations passed
        return True, None, None
