"""Handler for anchor track inclusion in recommendations."""

import structlog
from typing import Any, Dict, List

from ....states.agent_state import AgentState, TrackRecommendation

logger = structlog.get_logger(__name__)


class AnchorTrackHandler:
    """Handles inclusion of anchor tracks in recommendations."""

    def include_anchor_tracks(
        self, state: AgentState, all_recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Include anchor tracks in recommendations with high confidence.

        Args:
            state: Current agent state
            all_recommendations: Existing recommendations list

        Returns:
            Updated recommendations list with anchor tracks included
        """
        anchor_tracks = state.metadata.get("anchor_tracks", [])

        if not anchor_tracks:
            return all_recommendations

        # Convert anchor tracks to recommendation format with high confidence
        for anchor_track in anchor_tracks:
            recommendation = self._create_anchor_recommendation(anchor_track)

            # Insert at beginning for high priority
            all_recommendations.insert(0, recommendation.dict())

        user_count = sum(1 for t in anchor_tracks if t.get("user_mentioned", False))
        genre_count = len(anchor_tracks) - user_count

        logger.info(
            f"Included {len(anchor_tracks)} anchor tracks in recommendations "
            f"({user_count} user-mentioned, {genre_count} genre-based)"
        )

        return all_recommendations

    def _create_anchor_recommendation(
        self, anchor_track: Dict[str, Any]
    ) -> TrackRecommendation:
        """Create a TrackRecommendation from an anchor track.

        Args:
            anchor_track: Anchor track data

        Returns:
            TrackRecommendation object
        """
        # Get metadata for protection
        user_mentioned = anchor_track.get("user_mentioned", False)
        anchor_type = anchor_track.get("anchor_type", "genre")
        protected = anchor_track.get("protected", False)
        confidence = anchor_track.get("confidence", 0.95)

        # Debug log to trace metadata
        logger.debug(
            f"Adding anchor track '{anchor_track.get('name')}': "
            f"user_mentioned={user_mentioned}, anchor_type={anchor_type}, "
            f"protected={protected}, confidence={confidence}"
        )

        # Build reasoning based on anchor type
        if user_mentioned or anchor_type == "user":
            reasoning = "User-mentioned track - guaranteed inclusion"
        else:
            reasoning = "Anchor track from genre search - high feature match"

        rec = TrackRecommendation(
            track_id=anchor_track["id"],
            track_name=anchor_track["name"],
            artists=[a["name"] for a in anchor_track.get("artists", [])],
            spotify_uri=anchor_track.get("uri") or anchor_track.get("spotify_uri"),
            confidence_score=confidence,
            audio_features=anchor_track.get("audio_features", {}),
            reasoning=reasoning,
            source="anchor_track",
            user_mentioned=user_mentioned,
            anchor_type=anchor_type,
            protected=protected,
        )

        # Verify metadata was preserved
        rec_dict = rec.dict()
        logger.debug(
            f"TrackRecommendation created: user_mentioned={rec_dict.get('user_mentioned')}, "
            f"protected={rec_dict.get('protected')}"
        )

        return rec
