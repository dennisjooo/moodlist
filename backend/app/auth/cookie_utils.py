"""Cookie management utilities."""
from fastapi import Response

from app.core.config import settings
from app.core.constants import SessionConstants


def set_session_cookie(response: Response, session_token: str) -> None:
    """Set session cookie with standard parameters.

    Args:
        response: FastAPI response object
        session_token: Session token value
    """
    is_production = settings.APP_ENV == "production"

    # Use SameSite=None in production to allow cross-origin cookies
    # This is necessary when frontend and backend are on different domains
    samesite_value = "none" if is_production else "lax"

    response.set_cookie(
        key=SessionConstants.COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=is_production,  # Must be True when SameSite=None
        samesite=samesite_value,
        max_age=SessionConstants.EXPIRATION_SECONDS,
        path="/"
    )


def delete_session_cookie(response: Response) -> None:
    """Delete session cookie.

    Args:
        response: FastAPI response object
    """
    is_production = settings.APP_ENV == "production"
    samesite_value = "none" if is_production else "lax"

    response.delete_cookie(
        key=SessionConstants.COOKIE_NAME,
        httponly=True,
        secure=is_production,
        samesite=samesite_value,
        path="/"
    )
