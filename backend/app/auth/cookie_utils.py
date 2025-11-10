"""Cookie management utilities."""
from fastapi import Response

from app.core.config import settings
from app.core.constants import SessionConstants


def _is_localhost_origin(origin: str) -> bool:
    """Check if origin is localhost/127.0.0.1."""
    if not origin:
        return False
    return any(host in origin.lower() for host in ['localhost', '127.0.0.1'])


def set_session_cookie(response: Response, session_token: str, origin: str = None) -> None:
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
            # Use samesite=none (allow cross-site) + secure=False (allow HTTP)
            # Note: This may not work in all browsers due to security restrictions
            secure = False
            samesite = "none"
        else:
            # True production: HTTPS cross-origin
            secure = True
            samesite = "none"
    else:
        # Development: both frontend and backend are local
        secure = False
        samesite = "lax"

    response.set_cookie(
        key=SessionConstants.COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=SessionConstants.EXPIRATION_SECONDS,
        path="/",
        domain=None  # Let browser handle domain automatically
    )


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
            samesite = "none"
        else:
            secure = True
            samesite = "none"
    else:
        secure = False
        samesite = "lax"

    response.delete_cookie(
        key=SessionConstants.COOKIE_NAME,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
        domain=None  # Must match the domain used when setting the cookie
    )
