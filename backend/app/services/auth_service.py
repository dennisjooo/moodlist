"""Auth service for authentication business logic."""

from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

import structlog
import uuid

from app.clients.spotify_client import SpotifyAPIClient
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.core.exceptions import UnauthorizedException, ValidationException, NotFoundException
from app.core.constants import SessionConstants

logger = structlog.get_logger(__name__)


class AuthService:
    """Service for authentication business logic."""

    def __init__(
        self,
        spotify_client: SpotifyAPIClient,
        user_repository: UserRepository,
        session_repository: SessionRepository
    ):
        """Initialize the auth service.

        Args:
            spotify_client: Spotify API client
            user_repository: User repository
            session_repository: Session repository
        """
        self.spotify_client = spotify_client
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.logger = logger.bind(service="AuthService")

    async def authenticate_user(self, authorization_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Authenticate user with Spotify authorization code.

        Args:
            authorization_code: Spotify authorization code
            redirect_uri: OAuth redirect URI

        Returns:
            Authentication data with user and session info

        Raises:
            ValidationException: If authentication fails
        """
        try:
            # Exchange authorization code for tokens
            token_data = await self._exchange_code_for_tokens(authorization_code, redirect_uri)

            # Get user profile from Spotify
            user_profile = await self.spotify_client.get_user_profile(token_data["access_token"])

            # Create or update user in database
            user = await self._create_or_update_user(user_profile, token_data)

            # Create session
            session = await self._create_user_session(user.id)

            self.logger.info(
                "User authenticated successfully",
                user_id=user.id,
                spotify_id=user.spotify_id
            )

            return {
                "user": {
                    "id": user.id,
                    "spotify_id": user.spotify_id,
                    "display_name": user.display_name,
                    "email": user.email,
                    "profile_image_url": user.profile_image_url
                },
                "session": {
                    "token": session.session_token,
                    "expires_at": session.expires_at.isoformat()
                },
                "tokens": {
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in")
                }
            }

        except Exception as e:
            self.logger.error(
                "User authentication failed",
                error=str(e)
            )
            raise ValidationException("Authentication failed")

    async def validate_session(self, session_token: str) -> Dict[str, Any]:
        """Validate session token and return user data.

        Args:
            session_token: Session token

        Returns:
            User and session data

        Raises:
            UnauthorizedException: If session is invalid or expired
        """
        try:
            # Get session
            session = await self.session_repository.get_by_token(session_token)
            if not session:
                raise UnauthorizedException("Invalid session")

            # Check if session is expired
            now = datetime.now(timezone.utc)
            if session.expires_at <= now:
                raise UnauthorizedException("Session expired")

            # Get user
            user = await self.user_repository.get_by_id_or_fail(session.user_id)

            # Update last activity
            await self.session_repository.update_last_activity(session.id)

            return {
                "user": {
                    "id": user.id,
                    "spotify_id": user.spotify_id,
                    "display_name": user.display_name,
                    "email": user.email,
                    "profile_image_url": user.profile_image_url
                },
                "session": {
                    "token": session.session_token,
                    "expires_at": session.expires_at.isoformat(),
                    "last_activity": session.last_activity.isoformat()
                }
            }

        except NotFoundException:
            raise UnauthorizedException("Invalid session")
        except Exception as e:
            self.logger.error(
                "Session validation failed",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            raise UnauthorizedException("Session validation failed")

    async def refresh_session(self, session_token: str) -> Dict[str, Any]:
        """Refresh session expiration time.

        Args:
            session_token: Session token

        Returns:
            Updated session data

        Raises:
            UnauthorizedException: If session is invalid
        """
        try:
            # Get session
            session = await self.session_repository.get_by_token(session_token)
            if not session:
                raise UnauthorizedException("Invalid session")

            # Calculate new expiration time
            new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=SessionConstants.EXPIRATION_SECONDS)

            # Update session
            updated_session = await self.session_repository.extend_session(session.id, new_expires_at)

            self.logger.info(
                "Session refreshed",
                session_token=session_token[:8] + "...",
                new_expires_at=new_expires_at.isoformat()
            )

            return {
                "session": {
                    "token": updated_session.session_token,
                    "expires_at": updated_session.expires_at.isoformat(),
                    "last_activity": updated_session.last_activity.isoformat()
                }
            }

        except Exception as e:
            self.logger.error(
                "Session refresh failed",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            raise UnauthorizedException("Session refresh failed")

    async def logout_user(self, session_token: str) -> bool:
        """Logout user by deleting their session.

        Args:
            session_token: Session token

        Returns:
            True if logout successful
        """
        try:
            # Get session
            session = await self.session_repository.get_by_token(session_token)
            if not session:
                # Session doesn't exist, consider logout successful
                return True

            # Delete session
            await self.session_repository.delete(session.id)

            self.logger.info(
                "User logged out",
                session_token=session_token[:8] + "...",
                user_id=session.user_id
            )

            return True

        except Exception as e:
            self.logger.error(
                "Logout failed",
                session_token=session_token[:8] + "...",
                error=str(e)
            )
            # Don't raise exception for logout failures
            return False

    async def logout_user_from_all_sessions(self, user_id: int) -> int:
        """Logout user from all sessions.

        Args:
            user_id: User ID

        Returns:
            Number of sessions deleted
        """
        try:
            deleted_count = await self.session_repository.delete_user_sessions(user_id)

            self.logger.info(
                "Logged out user from all sessions",
                user_id=user_id,
                deleted_sessions=deleted_count
            )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Failed to logout user from all sessions",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def get_user_sessions(self, user_id: int, include_expired: bool = False) -> list[Dict[str, Any]]:
        """Get all sessions for a user.

        Args:
            user_id: User ID
            include_expired: Include expired sessions

        Returns:
            List of session data
        """
        try:
            if include_expired:
                sessions = await self.session_repository.get_by_user_id(user_id)
            else:
                sessions = await self.session_repository.get_active_sessions(user_id=user_id)

            return [
                {
                    "token": s.session_token,
                    "created_at": s.created_at.isoformat(),
                    "last_activity": s.last_activity.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                    "is_expired": s.expires_at <= datetime.now(timezone.utc)
                }
                for s in sessions
            ]

        except Exception as e:
            self.logger.error(
                "Failed to get user sessions",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def _exchange_code_for_tokens(self, authorization_code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens.

        Args:
            authorization_code: Spotify authorization code
            redirect_uri: OAuth redirect URI

        Returns:
            Token data

        Raises:
            ValidationException: If token exchange fails
        """
        try:
            import httpx
            from app.core.config import settings

            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": redirect_uri,
                "client_id": settings.SPOTIFY_CLIENT_ID,
                "client_secret": settings.SPOTIFY_CLIENT_SECRET
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://accounts.spotify.com/api/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            self.logger.error(
                "Token exchange failed",
                status_code=e.response.status_code,
                error=str(e)
            )
            raise ValidationException("Failed to exchange authorization code for tokens")
        except Exception as e:
            self.logger.error("Unexpected error during token exchange", error=str(e))
            raise ValidationException("Token exchange failed")

    async def _create_or_update_user(self, user_profile: Dict[str, Any], token_data: Dict[str, Any]) -> Any:
        """Create or update user in database.

        Args:
            user_profile: Spotify user profile data
            token_data: Token data from Spotify

        Returns:
            User instance
        """
        try:
            spotify_id = user_profile["id"]

            # Check if user exists
            existing_user = await self.user_repository.get_by_spotify_id(spotify_id)

            # Calculate token expiration
            expires_in = token_data.get("expires_in", 3600)
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            if existing_user:
                # Update existing user
                return await self.user_repository.update_tokens(
                    user_id=existing_user.id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", existing_user.refresh_token),
                    token_expires_at=token_expires_at
                )
            else:
                # Create new user
                return await self.user_repository.create(
                    spotify_id=spotify_id,
                    display_name=user_profile.get("display_name"),
                    email=user_profile.get("email"),
                    profile_image_url=self._extract_profile_image(user_profile),
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_expires_at=token_expires_at,
                    is_active=True
                )

        except Exception as e:
            self.logger.error(
                "Failed to create or update user",
                spotify_id=user_profile.get("id"),
                error=str(e)
            )
            raise

    async def _create_user_session(self, user_id: int) -> Any:
        """Create a new session for user.

        Args:
            user_id: User ID

        Returns:
            Session instance
        """
        try:
            session_token = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=SessionConstants.EXPIRATION_SECONDS)

            return await self.session_repository.create(
                user_id=user_id,
                session_token=session_token,
                expires_at=expires_at,
                metadata={}
            )

        except Exception as e:
            self.logger.error(
                "Failed to create user session",
                user_id=user_id,
                error=str(e)
            )
            raise

    def _extract_profile_image(self, user_profile: Dict[str, Any]) -> Optional[str]:
        """Extract profile image URL from Spotify user profile.

        Args:
            user_profile: Spotify user profile data

        Returns:
            Profile image URL or None
        """
        try:
            images = user_profile.get("images", [])
            if images and len(images) > 0:
                # Return the first (usually largest) image
                return images[0].get("url")
        except Exception:
            pass
        return None