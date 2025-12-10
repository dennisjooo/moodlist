"""Cookie management utilities."""

import structlog
from fastapi import Response

from app.core.config import settings
from app.core.constants import SessionConstants

logger = structlog.get_logger(__name__)


def _is_localhost_origin(origin: str) -> bool:
    """Check if origin is localhost/127.0.0.1."""
    if not origin:
        return False
    return any(host in origin.lower() for host in ["localhost", "127.0.0.1"])


def set_session_cookie(
    response: Response, session_token: str, origin: str = None
) -> None:
    """Set session cookie with standard parameters.

    Args:
        response: FastAPI response object
        session_token: Session token value
        origin: Request origin header (optional, used to detect localhost)
    """
    is_production = settings.APP_ENV == "production"
    is_localhost = _is_localhost_origin(origin or "")

    # Cookie security strategy for cross-site scenarios:
    # When backend is on different domain than frontend (cross-site), we need:
    # - secure=True (HTTPS required for cross-site cookies)
    # - samesite="none" (required for cross-site)
    #
    # PROBLEM: localhost is HTTP, but cross-site cookies require HTTPS + SameSite=None
    # SOLUTION: For localhost, we have to compromise security for development:
    #   - Use secure=False (allow HTTP)
    #   - Use samesite="none" (allow cross-site)
    #   - This works in Chrome but may not work in all browsers

    if is_production:
        if is_localhost:
            # SPECIAL CASE: localhost frontend + production backend
            # This is cross-origin but frontend is HTTP
            # Use samesite=None (allow cross-site) + secure=False (allow HTTP)
            # Note: This may not work in all browsers due to security restrictions
            secure = False
            samesite = "None"
        else:
            # True production: HTTPS cross-origin
            secure = True
            samesite = "None"
    else:
        # Development: both frontend and backend are local
        secure = False
        samesite = "lax"

    # Build cookie string manually to add Partitioned attribute for cross-site cookies
    # Chrome 118+ requires Partitioned for third-party cookies
    cookie_parts = [
        f"{SessionConstants.COOKIE_NAME}={session_token}",
        "HttpOnly",
        f"Max-Age={SessionConstants.EXPIRATION_SECONDS}",
        "Path=/",
    ]

    if secure:
        cookie_parts.append("Secure")

    if samesite:
        cookie_parts.append(f"SameSite={samesite}")

    # Add Partitioned attribute for cross-site cookies in production
    if is_production and not is_localhost and samesite == "None":
        cookie_parts.append("Partitioned")
        logger.info(
            "Setting partitioned cross-site cookie",
            origin=origin,
            secure=secure,
            samesite=samesite,
        )

    cookie_string = "; ".join(cookie_parts)

    # Set the cookie via Set-Cookie header
    response.headers.append("Set-Cookie", cookie_string)


def delete_session_cookie(response: Response, origin: str = None) -> None:
    """Delete session cookie.

    Args:
        response: FastAPI response object
        origin: Request origin header (optional, used to detect localhost)
    """
    is_production = settings.APP_ENV == "production"
    is_localhost = _is_localhost_origin(origin or "")

    # Must match the settings used when cookie was set
    if is_production:
        if is_localhost:
            secure = False
            samesite = "None"
        else:
            secure = True
            samesite = "None"
    else:
        secure = False
        samesite = "lax"

    # Build cookie deletion string manually to match how we set it (including Partitioned)
    cookie_parts = [
        f"{SessionConstants.COOKIE_NAME}=",
        "HttpOnly",
        "Max-Age=0",  # Expire immediately
        "Path=/",
    ]

    if secure:
        cookie_parts.append("Secure")

    if samesite:
        cookie_parts.append(f"SameSite={samesite}")

    # Must include Partitioned if it was used when setting the cookie
    if is_production and not is_localhost and samesite == "None":
        cookie_parts.append("Partitioned")

    cookie_string = "; ".join(cookie_parts)

    # Delete the cookie via Set-Cookie header
    response.headers.append("Set-Cookie", cookie_string)
