"""Token service for token refresh and validation logic."""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any

import structlog

from app.clients.spotify_client import SpotifyAPIClient
from app.repositories.user_repository import UserRepository
from app.core.exceptions import ValidationException

logger = structlog.get_logger(__name__)


class TokenService:
    """Service for handling Spotify token operations."""

    def __init__(
        self,
        spotify_client: SpotifyAPIClient,
        user_repository: UserRepository
    ):
        """Initialize the token service.

        Args:
            spotify_client: Spotify API client
            user_repository: User repository for database operations
        """
        self.spotify_client = spotify_client
        self.user_repository = user_repository
        self.logger = logger.bind(service="TokenService")

    async def refresh_user_token(self, user_id: int) -> Dict[str, Any]:
        """Refresh Spotify access token for a user.

        Args:
            user_id: User ID

        Returns:
            Updated token data

        Raises:
            NotFoundException: If user not found
            SpotifyAuthError: If token refresh fails
        """
        try:
            # Get user with current tokens
            user = await self.user_repository.get_by_id_or_fail(user_id)

            if not user.refresh_token:
                raise ValidationException("No refresh token available for user")

            self.logger.info("Refreshing Spotify token", user_id=user_id)

            # Refresh token via Spotify API
            token_data = await self.spotify_client.refresh_token(user.refresh_token)

            # Calculate new expiration time
            expires_in = token_data.get("expires_in", 3600)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Update user tokens in database
            updated_user = await self.user_repository.update_tokens(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", user.refresh_token),  # May not be returned
                token_expires_at=token_expires_at
            )

            self.logger.info("Successfully refreshed Spotify token", user_id=user_id)

            return {
                "access_token": updated_user.access_token,
                "refresh_token": updated_user.refresh_token,
                "expires_at": updated_user.token_expires_at.isoformat(),
                "expires_in": expires_in
            }

        except Exception as e:
            self.logger.error(
                "Failed to refresh user token",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def validate_token(self, user_id: int) -> bool:
        """Validate if user's access token is still valid.

        Args:
            user_id: User ID

        Returns:
            True if token is valid, False otherwise
        """
        try:
            user = await self.user_repository.get_by_id_or_fail(user_id)

            if not user.access_token or not user.token_expires_at:
                return False

            # Check if token is expired (with 5 minute buffer)
            buffer_time = timedelta(minutes=5)
            return datetime.now(timezone.utc) < (user.token_expires_at - buffer_time)

        except Exception as e:
            self.logger.error(
                "Error validating token",
                user_id=user_id,
                error=str(e)
            )
            return False

    async def ensure_valid_token(self, user_id: int) -> str:
        """Ensure user has a valid access token, refreshing if necessary.

        Args:
            user_id: User ID

        Returns:
            Valid access token

        Raises:
            NotFoundException: If user not found
            SpotifyAuthError: If token refresh fails
        """
        try:
            # Check if current token is valid
            if await self.validate_token(user_id):
                user = await self.user_repository.get_by_id_or_fail(user_id)
                return user.access_token

            # Token is invalid/expired, refresh it
            self.logger.info("Token expired, refreshing", user_id=user_id)
            token_data = await self.refresh_user_token(user_id)

            return token_data["access_token"]

        except Exception as e:
            self.logger.error(
                "Failed to ensure valid token",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def revoke_user_tokens(self, user_id: int) -> bool:
        """Revoke user's tokens (set to None in database).

        Args:
            user_id: User ID

        Returns:
            True if successful

        Raises:
            NotFoundException: If user not found
        """
        try:
            # Clear tokens by setting them to None
            await self.user_repository.update(
                user_id,
                access_token=None,
                refresh_token=None,
                token_expires_at=None
            )

            self.logger.info("Successfully revoked user tokens", user_id=user_id)
            return True

        except Exception as e:
            self.logger.error(
                "Failed to revoke user tokens",
                user_id=user_id,
                error=str(e)
            )
            raise