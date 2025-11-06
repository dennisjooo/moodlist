"""State management for the agentic recommendation system."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field


class RecommendationStatus(str, Enum):
    """Status of the recommendation process."""
    PENDING = "pending"
    ANALYZING_MOOD = "analyzing_mood"
    GATHERING_SEEDS = "gathering_seeds"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    EVALUATING_QUALITY = "evaluating_quality"
    OPTIMIZING_RECOMMENDATIONS = "optimizing_recommendations"
    AWAITING_USER_INPUT = "awaiting_user_input"
    PROCESSING_EDITS = "processing_edits"
    CREATING_PLAYLIST = "creating_playlist"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrackRecommendation(BaseModel):
    """Individual track recommendation with metadata."""
    track_id: str = Field(..., description="Track ID from RecoBeat/Spotify")
    track_name: str = Field(..., description="Track name")
    artists: List[str] = Field(..., description="Artist names")
    spotify_uri: Optional[str] = Field(None, description="Spotify URI")
    confidence_score: float = Field(..., description="Recommendation confidence 0-1")
    audio_features: Optional[Dict[str, Any]] = Field(None, description="Audio features")
    reasoning: str = Field(..., description="Why this track was recommended")
    source: str = Field(..., description="Source of recommendation (reccobeat/spotify)")
    
    # Anchor track protection metadata
    user_mentioned: bool = Field(default=False, description="Whether track was explicitly mentioned by user")
    user_mentioned_artist: bool = Field(default=False, description="Whether track is from a user-mentioned artist")
    anchor_type: Optional[str] = Field(None, description="Type of anchor: 'user' or 'genre'")
    protected: bool = Field(default=False, description="Whether track is protected from quality filtering")
    
    # Energy flow analysis (for playlist ordering)
    energy_analysis: Optional[Dict[str, Any]] = Field(None, description="Energy flow characteristics for ordering")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlaylistEdit(BaseModel):
    """User edit to the playlist."""
    edit_type: str = Field(..., description="Type of edit (reorder/remove/add)")
    track_id: Optional[str] = Field(None, description="Track being edited")
    new_position: Optional[int] = Field(None, description="New position for reorder")
    edit_timestamp: datetime = Field(default_factory=datetime.utcnow)
    reasoning: Optional[str] = Field(None, description="User reasoning for edit")


class AgentState(BaseModel):
    """Main state object for the agentic workflow."""

    # Core identification
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")

    # Workflow state
    current_step: str = Field(default="pending", description="Current workflow step")
    status: RecommendationStatus = Field(default=RecommendationStatus.PENDING)

    # Input data
    mood_prompt: str = Field(..., description="Original mood description")
    mood_analysis: Optional[Dict[str, Any]] = Field(None, description="LLM mood analysis")

    # Spotify user data
    spotify_user_id: Optional[str] = Field(None, description="Spotify user ID")
    user_top_tracks: List[str] = Field(default_factory=list, description="User's top track IDs")
    user_top_artists: List[str] = Field(default_factory=list, description="User's top artist IDs")

    # Recommendations
    recommendations: List[TrackRecommendation] = Field(default_factory=list, description="Generated recommendations")
    seed_tracks: List[str] = Field(default_factory=list, description="Seed tracks used for recommendations")
    negative_seeds: List[str] = Field(default_factory=list, description="Tracks to avoid")

    # Playlist management
    playlist_id: Optional[str] = Field(None, description="Created playlist ID")
    playlist_name: Optional[str] = Field(None, description="Generated playlist name")
    spotify_playlist_id: Optional[str] = Field(None, description="Spotify playlist ID")

    # Human-in-the-loop
    user_edits: List[PlaylistEdit] = Field(default_factory=list, description="User edits to playlist")
    awaiting_user_input: bool = Field(default=False, description="Whether waiting for user input")

    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if failed")
    retry_count: int = Field(default=0, description="Number of retries attempted")

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def add_recommendation(self, recommendation: TrackRecommendation):
        """Add a recommendation to the state.

        Args:
            recommendation: Track recommendation to add
        """
        self.recommendations.append(recommendation)
        self.update_timestamp()

    def add_user_edit(self, edit: PlaylistEdit):
        """Add a user edit to the state.

        Args:
            edit: User edit to add
        """
        self.user_edits.append(edit)
        self.awaiting_user_input = False
        self.update_timestamp()

    def set_error(self, error: str):
        """Set error state.

        Args:
            error: Error message
        """
        self.error_message = error
        self.status = RecommendationStatus.FAILED
        self.update_timestamp()

    def reset_for_retry(self):
        """Reset state for retry attempt."""
        self.retry_count += 1
        self.error_message = None
        self.status = RecommendationStatus.PENDING
        self.current_step = "pending"
        self.update_timestamp()

    def is_complete(self) -> bool:
        """Check if the recommendation process is complete.

        Returns:
            Whether the process is complete
        """
        return self.status in [RecommendationStatus.COMPLETED, RecommendationStatus.FAILED]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the current state.

        Returns:
            State summary dictionary
        """
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "mood_prompt": self.mood_prompt[:50] + "..." if len(self.mood_prompt) > 50 else self.mood_prompt,
            "recommendation_count": len(self.recommendations),
            "has_playlist": self.playlist_id is not None,
            "awaiting_input": self.awaiting_user_input,
            "error": self.error_message is not None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class RecommendationState(BaseModel):
    """Simplified state for recommendation-specific operations."""

    mood_prompt: str
    target_features: Dict[str, float] = Field(default_factory=dict)
    seed_tracks: List[str] = Field(default_factory=list)
    excluded_tracks: List[str] = Field(default_factory=list)
    recommendations: List[TrackRecommendation] = Field(default_factory=list)
    max_recommendations: int = Field(default=30)

    def add_recommendation(self, recommendation: TrackRecommendation):
        """Add a recommendation if under the limit.

        Args:
            recommendation: Track recommendation to add
        """
        if len(self.recommendations) < self.max_recommendations:
            self.recommendations.append(recommendation)

    def get_top_recommendations(self, limit: int = 10) -> List[TrackRecommendation]:
        """Get top recommendations by confidence score.

        Args:
            limit: Maximum number of recommendations to return

        Returns:
            Top recommendations sorted by confidence
        """
        sorted_recs = sorted(
            self.recommendations,
            key=lambda x: x.confidence_score,
            reverse=True
        )
        return sorted_recs[:limit]
