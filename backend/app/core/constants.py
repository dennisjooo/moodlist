"""Application-wide constants and enums."""

from enum import Enum


class PlaylistStatus(str, Enum):
    """Playlist status values."""

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RecommendationStatusEnum(str, Enum):
    """Recommendation workflow status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TimeRange(str, Enum):
    """Spotify time range values."""

    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class SessionConstants:
    """Session-related constants."""

    EXPIRATION_HOURS = 24
    EXPIRATION_SECONDS = 86400  # 24 * 60 * 60
    COOKIE_NAME = "session_token"


class SpotifyEndpoints:
    """Spotify API endpoint paths."""

    # Base URLs
    API_BASE = "https://api.spotify.com/v1"
    ACCOUNTS_BASE = "https://accounts.spotify.com/api"

    # User endpoints
    USER_PROFILE = "/me"
    USER_TOP_TRACKS = "/me/top/tracks"
    USER_TOP_ARTISTS = "/me/top/artists"
    USER_PLAYLISTS = "/me/playlists"

    # Playlist endpoints
    PLAYLISTS = "/playlists"

    # Search endpoints
    SEARCH = "/search"

    # Track endpoints
    TRACKS = "/tracks"

    # Auth endpoints
    TOKEN_URL = "https://accounts.spotify.com/api/token"


class HTTPTimeouts:
    """HTTP request timeout constants."""

    DEFAULT = 30
    SPOTIFY_API = 30
    LONG_RUNNING = 120
