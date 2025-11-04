"""Background tasks for proactive cache warming and optimization."""

import asyncio
import structlog
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .cache import cache_manager


logger = structlog.get_logger(__name__)


class BackgroundTaskManager:
    """Manager for background optimization tasks."""

    def __init__(self):
        """Initialize background task manager."""
        self.running_tasks = set()
        self.popular_moods = [
            "happy_energetic",
            "sad_melancholic",
            "calm_relaxing",
            "upbeat_danceable",
            "focus_productive",
            "romantic_intimate",
            "angry_intense",
            "nostalgic_reflective",
        ]

    def _normalize_mood_key(self, mood_prompt: str) -> str:
        """Normalize mood prompt to a cache key.

        Args:
            mood_prompt: Raw mood prompt

        Returns:
            Normalized mood key
        """
        mood_lower = mood_prompt.lower().strip()

        mood_keywords = {
            "happy": "happy_energetic",
            "energetic": "happy_energetic",
            "joyful": "happy_energetic",
            "sad": "sad_melancholic",
            "melancholic": "sad_melancholic",
            "depressed": "sad_melancholic",
            "calm": "calm_relaxing",
            "relaxing": "calm_relaxing",
            "peaceful": "calm_relaxing",
            "upbeat": "upbeat_danceable",
            "danceable": "upbeat_danceable",
            "party": "upbeat_danceable",
            "focus": "focus_productive",
            "productive": "focus_productive",
            "study": "focus_productive",
            "romantic": "romantic_intimate",
            "intimate": "romantic_intimate",
            "love": "romantic_intimate",
            "angry": "angry_intense",
            "intense": "angry_intense",
            "aggressive": "angry_intense",
            "nostalgic": "nostalgic_reflective",
            "reflective": "nostalgic_reflective",
            "memories": "nostalgic_reflective",
        }

        for keyword, mood_key in mood_keywords.items():
            if keyword in mood_lower:
                return mood_key

        return "generic_mood"

    async def precompute_popular_moods(
        self,
        workflow_manager,
        spotify_service,
        reccobeat_service,
        llm,
        access_token: str,
        user_id: str
    ) -> None:
        """Precompute recommendations for popular moods.

        Phase 4 Optimization: Background task to warm cache with popular mood
        recommendations during off-peak times.

        Args:
            workflow_manager: Workflow manager instance
            spotify_service: Spotify service instance
            reccobeat_service: RecoBeat service instance
            llm: LLM instance for mood analysis
            access_token: Spotify access token
            user_id: User ID for context
        """
        async def precompute_mood(mood_prompt: str):
            """Precompute recommendations for a single mood."""
            try:
                mood_key = self._normalize_mood_key(mood_prompt)

                cached = await cache_manager.get_popular_mood_cache(mood_key)
                if cached:
                    logger.debug(f"Popular mood '{mood_key}' already cached, skipping")
                    return

                logger.info(f"Precomputing recommendations for popular mood: {mood_prompt}")

                session_id = await workflow_manager.start_workflow(
                    mood_prompt=mood_prompt,
                    user_id=user_id,
                    spotify_user_id=user_id
                )

                state = workflow_manager.get_workflow_state(session_id)
                if state:
                    state.metadata["spotify_access_token"] = access_token

                timeout = 180
                elapsed = 0
                interval = 2

                while elapsed < timeout:
                    state = workflow_manager.get_workflow_state(session_id)
                    if not state:
                        break

                    if state.status.value in ["completed", "failed", "error"]:
                        if state.status.value == "completed" and state.recommendations:
                            recommendations_data = {
                                "mood_analysis": state.mood_analysis,
                                "recommendations": [
                                    {
                                        "track_id": rec.track_id,
                                        "track_name": rec.track_name,
                                        "artists": rec.artists,
                                        "spotify_uri": rec.spotify_uri,
                                        "confidence_score": rec.confidence_score,
                                        "reasoning": rec.reasoning,
                                        "source": rec.source
                                    }
                                    for rec in state.recommendations
                                ],
                                "computed_at": datetime.now(timezone.utc).isoformat()
                            }

                            await cache_manager.set_popular_mood_cache(mood_key, recommendations_data)
                            logger.info(f"Cached recommendations for popular mood '{mood_key}'")
                        break

                    await asyncio.sleep(interval)
                    elapsed += interval

            except Exception as e:
                logger.warning(f"Error precomputing mood '{mood_prompt}': {e}")

        logger.info("Starting background mood precomputation")

        for mood_prompt in self.popular_moods:
            try:
                await precompute_mood(mood_prompt)
                await asyncio.sleep(5)

            except Exception as e:
                logger.error(f"Failed to precompute mood '{mood_prompt}': {e}")

        logger.info("Completed background mood precomputation")

    def start_background_precomputation(
        self,
        workflow_manager,
        spotify_service,
        reccobeat_service,
        llm,
        access_token: str,
        user_id: str
    ) -> None:
        """Start background precomputation task (fire-and-forget).

        Args:
            workflow_manager: Workflow manager instance
            spotify_service: Spotify service instance
            reccobeat_service: RecoBeat service instance
            llm: LLM instance
            access_token: Spotify access token
            user_id: User ID for context
        """
        task = asyncio.create_task(
            self.precompute_popular_moods(
                workflow_manager,
                spotify_service,
                reccobeat_service,
                llm,
                access_token,
                user_id
            )
        )

        self.running_tasks.add(task)
        task.add_done_callback(self.running_tasks.discard)

        logger.info("Started background mood precomputation task")


background_task_manager = BackgroundTaskManager()
