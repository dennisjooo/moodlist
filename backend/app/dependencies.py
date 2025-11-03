"""Dependency injection functions for FastAPI routes."""

from typing import Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.playlist_repository import PlaylistRepository
from app.repositories.user_repository import UserRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.invocation_repository import InvocationRepository
from app.repositories.llm_invocation_repository import LLMInvocationRepository
from app.clients.spotify_client import SpotifyAPIClient
from app.services.playlist_service import PlaylistService
from app.services.token_service import TokenService
from app.services.workflow_state_service import WorkflowStateService
from app.services.auth_service import AuthService


# Singletons
_spotify_client: Optional[SpotifyAPIClient] = None

def get_spotify_client() -> SpotifyAPIClient:
    """Get Spotify API client singleton."""
    global _spotify_client
    if _spotify_client is None:
        _spotify_client = SpotifyAPIClient()
    return _spotify_client


# Repository dependencies
def get_playlist_repository(
    db: AsyncSession = Depends(get_db)
) -> PlaylistRepository:
    """Get playlist repository."""
    return PlaylistRepository(db)


def get_user_repository(
    db: AsyncSession = Depends(get_db)
) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


def get_session_repository(
    db: AsyncSession = Depends(get_db)
) -> SessionRepository:
    """Get session repository."""
    return SessionRepository(db)


def get_invocation_repository(
    db: AsyncSession = Depends(get_db)
) -> InvocationRepository:
    """Get invocation repository."""
    return InvocationRepository(db)


def get_llm_invocation_repository(
    db: AsyncSession = Depends(get_db)
) -> LLMInvocationRepository:
    """Get LLM invocation repository."""
    return LLMInvocationRepository(db)


# Service dependencies
def get_token_service(
    user_repo: UserRepository = Depends(get_user_repository),
    spotify_client: SpotifyAPIClient = Depends(get_spotify_client)
) -> TokenService:
    """Get token service."""
    return TokenService(spotify_client, user_repo)


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    token_service: TokenService = Depends(get_token_service)
) -> AuthService:
    """Get auth service."""
    return AuthService(user_repo, token_service)


def get_workflow_state_service(
    session_repo: SessionRepository = Depends(get_session_repository),
    playlist_repo: PlaylistRepository = Depends(get_playlist_repository),
    user_repo: UserRepository = Depends(get_user_repository)
) -> WorkflowStateService:
    """Get workflow state service."""
    return WorkflowStateService(session_repo, playlist_repo, user_repo)


def get_playlist_service(
    playlist_repo: PlaylistRepository = Depends(get_playlist_repository),
    user_repo: UserRepository = Depends(get_user_repository),
    spotify_client: SpotifyAPIClient = Depends(get_spotify_client),
) -> PlaylistService:
    """Get playlist service."""
    return PlaylistService(spotify_client, playlist_repo, user_repo)
