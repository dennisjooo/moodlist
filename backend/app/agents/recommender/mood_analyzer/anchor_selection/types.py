"""Type definitions for anchor track selection."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class AnchorCandidate:
    """Represents a candidate track for anchor selection."""

    track: Dict[str, Any]
    score: float
    confidence: float
    features: Dict[str, Any]
    source: str
    anchor_type: str
    user_mentioned: bool
    protected: bool
    genre: Optional[str] = None
    artist: Optional[str] = None
    llm_score: Optional[float] = None
    llm_confidence: Optional[float] = None
    llm_reasoning: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "track": self.track,
            "score": self.score,
            "confidence": self.confidence,
            "features": self.features,
            "source": self.source,
            "anchor_type": self.anchor_type,
            "user_mentioned": self.user_mentioned,
            "protected": self.protected,
            "genre": self.genre,
            "artist": self.artist,
            "llm_score": self.llm_score,
            "llm_confidence": self.llm_confidence,
            "llm_reasoning": self.llm_reasoning,
        }


@dataclass
class AnchorSelectionStrategy:
    """Strategy configuration for anchor track selection."""

    anchor_count: int
    selection_criteria: Dict[str, Any]
    track_priorities: Optional[List[Dict[str, Any]]] = None
    strategy_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "anchor_count": self.anchor_count,
            "selection_criteria": self.selection_criteria,
            "track_priorities": self.track_priorities,
            "strategy_notes": self.strategy_notes,
        }


@dataclass
class TrackFeatures:
    """Audio features for a track."""

    energy: Optional[float] = None
    valence: Optional[float] = None
    danceability: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    tempo: Optional[float] = None
    mode: Optional[float] = None
    loudness: Optional[float] = None
    speechiness: Optional[float] = None
    liveness: Optional[float] = None
    key: Optional[float] = None
    popularity: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
