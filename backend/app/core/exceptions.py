"""Custom exceptions and exception factories."""

from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Resource not found exception."""

    def __init__(self, resource: str, identifier: str = ""):
        detail = f"{resource} not found"
        if identifier:
            detail = f"{resource} '{identifier}' not found"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedException(HTTPException):
    """Unauthorized access exception."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenException(HTTPException):
    """Forbidden access exception."""

    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationException(HTTPException):
    """Validation error exception."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class SpotifyAPIException(HTTPException):
    """Spotify API error exception."""

    def __init__(
        self, detail: str = "Spotify API request failed", status_code: int = 502
    ):
        super().__init__(status_code=status_code, detail=detail)


class SpotifyAuthError(SpotifyAPIException):
    """Spotify authentication error."""

    def __init__(self, detail: str = "Invalid or expired Spotify token"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class SpotifyRateLimitError(SpotifyAPIException):
    """Spotify rate limit exceeded."""

    def __init__(self, detail: str = "Spotify API rate limit exceeded"):
        super().__init__(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


class SpotifyServerError(SpotifyAPIException):
    """Spotify server error."""

    def __init__(self, detail: str = "Spotify server error"):
        super().__init__(detail=detail, status_code=status.HTTP_502_BAD_GATEWAY)


class SpotifyConnectionError(SpotifyAPIException):
    """Spotify connection error."""

    def __init__(self, detail: str = "Failed to connect to Spotify"):
        super().__init__(detail=detail, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


class RateLimitException(HTTPException):
    """Rate limit exceeded exception."""

    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": detail,
                "retry_after": retry_after,
            },
        )


class InternalServerError(HTTPException):
    """Internal server error."""

    def __init__(self, detail: str = "Internal server error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class WorkflowException(HTTPException):
    """Workflow-related exception."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)
