"""WebSocket authentication utilities."""

import structlog
from fastapi import WebSocket

from ....core.database import async_session_factory
from ....repositories.playlist_repository import PlaylistRepository
from ....repositories.session_repository import SessionRepository
from ....repositories.user_repository import UserRepository
from ....models.user import User

logger = structlog.get_logger(__name__)


async def authenticate_websocket(
    websocket: WebSocket,
    session_id: str,
) -> tuple[User, dict | None, str | None]:
    """
    Authenticate WebSocket connection and verify user access to workflow.

    Returns:
        Tuple of (authenticated_user, initial_playlist_data, initial_playlist_status)
        Raises exception if authentication fails
    """
    # Authenticate via cookie or query parameter (WebSocket fallback)
    session_token = websocket.cookies.get("session_token")

    # Fallback: check query parameters if cookie not available
    if not session_token and websocket.query_params:
        session_token = websocket.query_params.get("token")
        logger.info("Using query param token for WebSocket auth", session_id=session_id)

    logger.info(
        "WebSocket auth attempt",
        session_id=session_id,
        has_token=bool(session_token),
        cookies_keys=list(websocket.cookies.keys()) if websocket.cookies else [],
        has_query_params=bool(websocket.query_params),
    )

    if not session_token:
        logger.warn(
            "No session token in WebSocket cookies or query params",
            session_id=session_id,
        )
        await websocket.send_json(
            {"type": "error", "message": "Authentication required - no session token"}
        )
        await websocket.close(code=1008)
        raise ValueError("Authentication required")

    # Verify session and get user (in a scoped DB session that will be closed)
    async with async_session_factory() as db:
        session_repo = SessionRepository(db)
        user_repo = UserRepository(db)
        playlist_repo = PlaylistRepository(db)

        session = await session_repo.get_valid_session_by_token(session_token)
        if not session:
            logger.warn("Invalid session token for WebSocket", session_id=session_id)
            await websocket.send_json({"type": "error", "message": "Invalid session"})
            await websocket.close(code=1008)
            raise ValueError("Invalid session")

        current_user = await user_repo.get_active_user_by_id(session.user_id)
        if not current_user:
            logger.warn(
                "User not found for WebSocket session",
                session_id=session_id,
                user_id=session.user_id,
            )
            await websocket.send_json({"type": "error", "message": "User not found"})
            await websocket.close(code=1008)
            raise ValueError("User not found")

        # Verify user owns this workflow
        session_playlist = await playlist_repo.get_by_session_id(session_id)
        if session_playlist and session_playlist.user_id != current_user.id:
            logger.warn(
                "Unauthorized WebSocket access attempt",
                session_id=session_id,
                user_id=current_user.id,
                playlist_user_id=session_playlist.user_id,
            )
            await websocket.send_json(
                {"type": "error", "message": "Unauthorized access to workflow"}
            )
            await websocket.close(code=1008)
            raise ValueError("Unauthorized access")

        # Prepare initial playlist data for state check
        initial_playlist_data = None
        initial_playlist_status = None
        if session_playlist:
            from ..serializers import serialize_playlist_status

            initial_playlist_data = serialize_playlist_status(
                session_id, session_playlist
            )
            initial_playlist_status = session_playlist.status

    # DB session is now closed - proceed with long-lived WebSocket connection
    logger.info(
        "WebSocket authenticated successfully",
        session_id=session_id,
        user_id=current_user.id,
    )

    return current_user, initial_playlist_data, initial_playlist_status
