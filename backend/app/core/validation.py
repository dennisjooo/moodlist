"""Configuration validation utilities."""
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


def validate_required_secrets():
    """Validate that all required secrets are set properly.

    Raises:
        RuntimeError: If any required secrets are missing or weak
    """
    errors = []

    # Check JWT secret key
    if not settings.JWT_SECRET_KEY:
        errors.append("JWT_SECRET_KEY is not set")
    elif len(settings.JWT_SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")
    else:
        # Check for common default/weak values
        weak_values = ["changeme", "secret", "password", "12345", "test", "default"]
        if settings.JWT_SECRET_KEY.lower() in weak_values:
            errors.append("JWT_SECRET_KEY is using a weak default value")

    # Check session secret key
    if not settings.SESSION_SECRET_KEY:
        errors.append("SESSION_SECRET_KEY is not set")
    elif len(settings.SESSION_SECRET_KEY) < 32:
        errors.append("SESSION_SECRET_KEY must be at least 32 characters")
    else:
        weak_values = ["changeme", "secret", "password", "12345", "test", "default"]
        if settings.SESSION_SECRET_KEY.lower() in weak_values:
            errors.append("SESSION_SECRET_KEY is using a weak default value")

    # Check Spotify credentials
    if not settings.SPOTIFY_CLIENT_ID:
        errors.append("SPOTIFY_CLIENT_ID is not set")
    if not settings.SPOTIFY_CLIENT_SECRET:
        errors.append("SPOTIFY_CLIENT_SECRET is not set")

    # Check LLM API keys (at least one should be set)
    llm_keys_set = [
        settings.OPENROUTER_API_KEY,
        settings.GROQ_API_KEY,
        settings.CEREBRAS_API_KEY
    ]
    if not any(llm_keys_set):
        errors.append("At least one LLM provider API key must be set (OPENROUTER, GROQ, or CEREBRAS)")

    # If there are errors, log them and raise exception
    if errors:
        for error in errors:
            logger.error("Configuration error", error=error)
        raise RuntimeError(
            f"Application started with invalid configuration. "
            f"Found {len(errors)} error(s): {'; '.join(errors)}"
        )

    logger.info("All required secrets validated successfully")

