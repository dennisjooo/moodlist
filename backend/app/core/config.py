import ast
import json
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = Field(default="MoodList API", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Database (Render sets DATABASE_URL automatically)
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    POSTGRES_CONNECTION_STRING: Optional[str] = Field(
        default=None, env="POSTGRES_CONNECTION_STRING"
    )

    # JWT
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(
        default=7, env="JWT_REFRESH_EXPIRATION_DAYS"
    )

    # Session
    SESSION_SECRET_KEY: str = Field(env="SESSION_SECRET_KEY")
    SESSION_EXPIRATION_MINUTES: int = Field(
        default=30, env="SESSION_EXPIRATION_MINUTES"
    )

    # Spotify
    SPOTIFY_CLIENT_ID: str = Field(env="SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: str = Field(env="SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI: str = Field(env="SPOTIFY_REDIRECT_URI")
    SPOTIFY_DEV_MODE: bool = Field(default=True, env="SPOTIFY_DEV_MODE")

    # CORS
    FRONTEND_URL: str = Field(default="http://127.0.0.1:3000", env="FRONTEND_URL")
    ALLOWED_ORIGINS: Union[str, List[str]] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        env="ALLOWED_ORIGINS",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from comma-separated string or JSON list."""
        if isinstance(v, str):
            # Try parsing as JSON first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle Python-style list strings (e.g. "['https://...']")
                try:
                    evaluated = ast.literal_eval(v)
                    if isinstance(evaluated, (list, tuple, set)):
                        return list(evaluated)
                except (ValueError, SyntaxError):
                    pass
                # Fall back to comma-separated
                return [
                    origin.strip().strip("\"'")
                    for origin in v.split(",")
                    if origin.strip()
                ]
        return v

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def add_frontend_url_to_origins(cls, v, info):
        """Automatically add FRONTEND_URL to allowed origins if not localhost."""
        frontend_url = info.data.get("FRONTEND_URL")
        if frontend_url and not any(
            host in frontend_url for host in ["127.0.0.1", "localhost"]
        ):
            if frontend_url not in v:
                v.append(frontend_url)
        return v

    # Redis
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # LLM Providers
    OPENROUTER_API_KEY: Optional[str] = Field(default=None, env="OPENROUTER_API_KEY")
    GROQ_API_KEY: Optional[str] = Field(default=None, env="GROQ_API_KEY")
    CEREBRAS_API_KEY: Optional[str] = Field(default=None, env="CEREBRAS_API_KEY")

    # Rate Limiting
    DAILY_PLAYLIST_CREATION_LIMIT: int = Field(
        default=5, env="DAILY_PLAYLIST_CREATION_LIMIT"
    )
    ENABLE_RATE_LIMITING: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    RATE_LIMITS: Dict[str, str] = Field(
        default_factory=lambda: {
            "general": "100/minute",
            "workflow_start": "10/minute",
            "workflow_remix": "5/minute",  # More restrictive for remix to prevent abuse
            "workflow_poll": "60/minute",
            "playlist_edit": "30/minute",
            "auth": "20/minute",
        }
    )

    def rate_limit_response(self, exc):
        """Generate rate limit error response."""
        from fastapi.responses import JSONResponse

        retry_after = (
            int(exc.retry_after)
            if hasattr(exc, "retry_after") and exc.retry_after
            else None
        )
        headers = {"Retry-After": str(retry_after)} if retry_after else {}
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests, please slow down.",
                "error": "rate_limit_exceeded",
                "limit": getattr(exc, "detail", "Rate limit exceeded"),
                "retry_after": retry_after,
            },
            headers=headers,
        )

    ALLOWED_HOSTS: Optional[Union[str, List[str]]] = Field(
        default=None, env="ALLOWED_HOSTS"
    )

    # Auto-detect Render service URL for TrustedHostMiddleware
    RENDER_EXTERNAL_URL: Optional[str] = Field(default=None, env="RENDER_EXTERNAL_URL")

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from comma-separated string or JSON/Python list."""
        if v is None:
            return None

        parsed_hosts = v
        if isinstance(v, str):
            # Try JSON first
            try:
                parsed_hosts = json.loads(v)
            except json.JSONDecodeError:
                # Accept Python-style list strings
                try:
                    evaluated = ast.literal_eval(v)
                    if isinstance(evaluated, (list, tuple, set)):
                        parsed_hosts = list(evaluated)
                    else:
                        parsed_hosts = evaluated
                except (ValueError, SyntaxError):
                    parsed_hosts = v

        if isinstance(parsed_hosts, str):
            parsed_hosts = [
                host.strip() for host in parsed_hosts.split(",") if host.strip()
            ]

        if parsed_hosts is None:
            return None

        normalized_hosts: List[str] = []
        for host in parsed_hosts:
            if not host:
                continue
            normalized = cls._normalize_host(host)
            if normalized and normalized not in normalized_hosts:
                normalized_hosts.append(normalized)

        return normalized_hosts or None

    @staticmethod
    def _normalize_host(host: str) -> Optional[str]:
        """Normalize host entries to bare hostnames or allowed wildcards."""
        host = host.strip().strip("\"'")
        if not host:
            return None
        if host == "*":
            return "*"
        if host.startswith("*."):
            return host
        if "://" in host:
            parsed = urlparse(host)
            host = parsed.hostname or parsed.netloc
        return host.strip("/")

    @field_validator("ALLOWED_HOSTS", mode="after")
    @classmethod
    def add_render_host(cls, v, info):
        """Automatically add Render hostname if RENDER_EXTERNAL_URL is set."""
        import os

        # Check if we're on Render (Render sets RENDER_EXTERNAL_URL)
        render_url = info.data.get("RENDER_EXTERNAL_URL") or os.getenv(
            "RENDER_EXTERNAL_URL"
        )

        if render_url:
            # Extract hostname from Render URL
            parsed = urlparse(render_url)
            hostname = parsed.hostname or parsed.netloc

            if hostname:
                # Initialize list if None
                if v is None:
                    v = []
                elif isinstance(v, str):
                    v = [v]

                # Add Render hostname if not already present
                if hostname not in v:
                    v.append(hostname)

        return v

    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment."""
        # Prefer POSTGRES_CONNECTION_STRING, fallback to DATABASE_URL (set by Render)
        return self.POSTGRES_CONNECTION_STRING or self.DATABASE_URL

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
