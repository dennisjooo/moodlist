"""Workflow execution logic."""

import asyncio
import structlog
from typing import Dict
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from ..core.base_agent import BaseAgent
from ..states.agent_state import AgentState, RecommendationStatus
from ...clients.spotify_client import SpotifyAPIClient

logger = structlog.get_logger(__name__)


class WorkflowExecutor:
    """Executes workflow steps with agents."""

    def __init__(self, agents: Dict[str, BaseAgent]):
        """Initialize the workflow executor.

        Args:
            agents: Dictionary of available agents
        """
        self.agents = agents

    async def execute_intent_analysis(self, state: AgentState) -> AgentState:
        """Execute intent analysis step.

        Phase 2: New step to analyze user intent before mood analysis.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "analyzing_intent"
        state.status = RecommendationStatus.ANALYZING_MOOD

        intent_agent = self.agents.get("intent_analyzer")
        if not intent_agent:
            logger.warning("Intent analyzer agent not available, skipping intent analysis")
            # Set empty intent analysis so downstream agents don't break
            state.metadata["intent_analysis"] = {
                "intent_type": "mood_variety",
                "user_mentioned_tracks": [],
                "user_mentioned_artists": [],
                "primary_genre": None,
                "genre_strictness": 0.6,
                "language_preferences": ["english"],
                "exclude_regions": [],
                "allow_obscure_artists": False,
                "quality_threshold": 0.6,
                "reasoning": "Intent analyzer not available"
            }
            return state

        return await intent_agent.run_with_error_handling(state)

    async def execute_mood_analysis(self, state: AgentState) -> AgentState:
        """Execute mood analysis step.

        Args:
            state: Current workflow state

        Returns:
            Updated state
        """
        state.current_step = "analyzing_mood"
        state.status = RecommendationStatus.ANALYZING_MOOD

        mood_agent = self.agents.get("mood_analyzer")
        if not mood_agent:
            raise ValueError("Mood analyzer agent not available")

        return await mood_agent.run_with_error_handling(state)

    async def execute_orchestration(self, state: AgentState, progress_callback=None) -> AgentState:
        """Execute orchestration for quality evaluation and improvement.

        Args:
            state: Current workflow state
            progress_callback: Optional callback for progress updates

        Returns:
            Updated state
        """
        # Refresh token before orchestration
        state = await self._refresh_spotify_token_if_needed(state)

        state.current_step = "evaluating_quality"
        state.status = RecommendationStatus.EVALUATING_QUALITY

        orchestrator = self.agents.get("orchestrator")
        if not orchestrator:
            logger.warning("Orchestrator agent not available, skipping quality optimization")
            return state

        # Set progress callback for real-time SSE updates
        if progress_callback:
            orchestrator._progress_callback = progress_callback

        return await orchestrator.run_with_error_handling(state)

    async def execute_playlist_ordering(self, state: AgentState) -> AgentState:
        """Execute playlist ordering to create optimal energy flow.

        Args:
            state: Current workflow state

        Returns:
            Updated state with ordered recommendations
        """
        state.current_step = "ordering_playlist"
        state.status = RecommendationStatus.OPTIMIZING_RECOMMENDATIONS

        ordering_agent = self.agents.get("playlist_orderer")
        if not ordering_agent:
            logger.warning("Playlist ordering agent not available, skipping ordering")
            state.metadata["ordering_applied"] = False
            return state

        return await ordering_agent.execute(state)

    async def _refresh_spotify_token_if_needed(self, state: AgentState) -> AgentState:
        """Refresh the Spotify access token if needed during workflow execution.

        Args:
            state: Current workflow state

        Returns:
            Updated state with refreshed token if needed
        """
        try:
            # Check if we have a user_id and can refresh the token
            if not state.user_id:
                logger.warning("No user_id in state, cannot refresh token")
                return state

            # Get user from database to check token expiry and refresh
            from ...core.database import async_session_factory
            from ...models.user import User

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
                    return state

                logger.info(f"Refreshing expired Spotify token for user {user.id}")

                # Refresh the token
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

                # Update the state with new token
                state.metadata["spotify_access_token"] = user.access_token

                logger.info(
                    f"Successfully refreshed Spotify token for user {user.id}, "
                    f"expires at {user.token_expires_at}"
                )

        except Exception as e:
            logger.error(f"Failed to refresh Spotify token: {str(e)}", exc_info=True)

        return state

