"""Centralized token management service for Spotify API access."""

import structlog
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy import select

from ....core.config import settings
from ....core.database import async_session_factory
from ....models.user import User
from ....clients.spotify_client import SpotifyAPIClient
from ...states.agent_state import AgentState

logger = structlog.get_logger(__name__)


class TokenService:
    """Centralized service for managing Spotify access token refresh and validation."""

    @staticmethod
    async def refresh_token_from_workflow(state: AgentState) -> AgentState:
        """Refresh the Spotify access token if expired.

        This is critical to call right before making Spotify API calls to ensure the token is valid.

        Args:
            state: Current agent state

        Returns:
            Updated state with refreshed token if needed
        """
        try:
            if not state.user_id:
                logger.warning("No user_id in state, cannot refresh token")
                return state

            async with async_session_factory() as db:
                result = await db.execute(
                    select(User).where(User.id == int(state.user_id))
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"User {state.user_id} not found for token refresh")
                    return state

                # Check if token is expired or will expire soon (within 5 minutes)
                now = datetime.now(timezone.utc)
                token_expires_at = user.token_expires_at

                # Handle both timezone-aware and naive datetimes
                if token_expires_at.tzinfo is None:
                    token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

                # If token is still valid (more than 5 minutes remaining), no need to refresh
                if token_expires_at > now + timedelta(minutes=5):
                    logger.info(f"Token still valid until {token_expires_at}, no refresh needed")
                    return state

                logger.warning(f"Spotify token expired or expiring soon (expires at {token_expires_at}), refreshing now...")

                # Refresh the token
                refreshed_state = await TokenService._refresh_token_for_user(user, db)
                if refreshed_state:
                    # Update the state with new token
                    state.metadata["spotify_access_token"] = user.access_token

                    logger.info(f"Successfully refreshed Spotify token for user {user.id}, new token expires at {user.token_expires_at}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error refreshing Spotify token: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Failed to refresh Spotify token: {str(e)}", exc_info=True)

        return state

    @staticmethod
    async def _refresh_token_for_user(user: User, db) -> bool:
        """Refresh the access token for a specific user.

        Args:
            user: User model instance
            db: Database session

        Returns:
            True if refresh was successful
        """
        spotify_client = SpotifyAPIClient()
        token_data = await spotify_client.refresh_token(user.refresh_token)

        # Update user's tokens in database
        user.access_token = token_data["access_token"]
        if "refresh_token" in token_data:
            user.refresh_token = token_data["refresh_token"]

        # Update expiration time
        expires_in = token_data.get("expires_in", 3600)
        user.token_expires_at = datetime.now(timezone.utc).replace(microsecond=0) + \
                               timedelta(seconds=expires_in)

        await db.commit()
        return True

    @staticmethod
    async def get_valid_token_for_user(user_id: int) -> Optional[str]:
        """Get a valid access token for a user, refreshing if necessary.

        Args:
            user_id: User ID

        Returns:
            Valid access token or None if refresh failed
        """
        try:
            async with async_session_factory() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"User {user_id} not found")
                    return None

                # Check if token needs refresh
                now = datetime.now(timezone.utc)
                token_expires_at = user.token_expires_at

                if token_expires_at.tzinfo is None:
                    token_expires_at = token_expires_at.replace(tzinfo=timezone.utc)

                if token_expires_at <= now + timedelta(minutes=5):
                    # Token expired or expiring soon, refresh it
                    await TokenService._refresh_token_for_user(user, db)
                    logger.info(f"Refreshed token for user {user_id}")

                return user.access_token

        except Exception as e:
            logger.error(f"Failed to get valid token for user {user_id}: {str(e)}")
            return None

    @staticmethod
    def is_token_valid(token: str, expires_at: datetime) -> bool:
        """Check if a token is currently valid.

        Args:
            token: Access token
            expires_at: Token expiration datetime

        Returns:
            True if token is valid
        """
        if not token:
            return False

        now = datetime.now(timezone.utc)
        expires_at_utc = expires_at.replace(tzinfo=timezone.utc) if expires_at.tzinfo is None else expires_at

        # Consider token valid if it has more than 5 minutes remaining
        return expires_at_utc > now + timedelta(minutes=5)
