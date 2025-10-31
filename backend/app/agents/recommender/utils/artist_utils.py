"""Shared utilities for artist processing and deduplication."""

from typing import Any, Dict, List


class ArtistDeduplicator:
    """Shared utility for artist deduplication and merging."""

    @staticmethod
    def merge_and_deduplicate(
        *artist_sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge multiple artist lists and deduplicate by ID.

        Args:
            *artist_sources: Variable number of artist list sources to merge

        Returns:
            Merged and deduplicated list of artists (preserves order, keeps first occurrence)
        """
        seen_ids = set()
        merged = []

        for artists in artist_sources:
            for artist in artists:
                artist_id = artist.get("id")
                if artist_id and artist_id not in seen_ids:
                    seen_ids.add(artist_id)
                    merged.append(artist)

        return merged

    @staticmethod
    def deduplicate(artists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate a single artist list by ID.

        Args:
            artists: List of artist dictionaries

        Returns:
            Deduplicated list of artists (preserves order, keeps first occurrence)
        """
        return ArtistDeduplicator.merge_and_deduplicate(artists)
