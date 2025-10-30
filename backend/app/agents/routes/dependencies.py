"""Dependency providers for agent routes."""

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict

from ...core.llm_factory import create_logged_llm
from ..tools.reccobeat_service import RecoBeatService
from ..tools.spotify_service import SpotifyService
from ..workflows.workflow_manager import WorkflowConfig, WorkflowManager
from ..recommender import (
    IntentAnalyzerAgent,
    MoodAnalyzerAgent,
    OrchestratorAgent,
    RecommendationGeneratorAgent,
    SeedGathererAgent,
)
from ..recommender.playlist_orderer import PlaylistOrderingAgent
from ..recommender.utils.config import config


@dataclass(frozen=True)
class AgentResources:
    """Container for lazily-instantiated agent dependencies."""

    llm: Any
    reccobeat_service: RecoBeatService
    spotify_service: SpotifyService
    agents: Dict[str, Any]
    workflow_manager: WorkflowManager


@lru_cache()
def _create_agent_resources() -> AgentResources:
    """Instantiate shared services, agents, and workflow manager on demand."""

    reccobeat_service = RecoBeatService()
    spotify_service = SpotifyService()

    llm = create_logged_llm(
        model="google/gemini-2.5-flash-lite-preview-09-2025",
        temperature=0.25,
        enable_logging=True,
        log_full_response=True,
    )

    intent_analyzer = IntentAnalyzerAgent(llm=llm, verbose=True)
    mood_analyzer = MoodAnalyzerAgent(
        llm=llm,
        spotify_service=spotify_service,
        reccobeat_service=reccobeat_service,
        verbose=True,
    )
    seed_gatherer = SeedGathererAgent(
        spotify_service=spotify_service,
        reccobeat_service=reccobeat_service,
        llm=llm,
        verbose=True,
    )
    recommendation_generator = RecommendationGeneratorAgent(
        reccobeat_service,
        spotify_service,
        max_recommendations=config.max_recommendations,
        verbose=True,
    )
    orchestrator = OrchestratorAgent(
        mood_analyzer=mood_analyzer,
        recommendation_generator=recommendation_generator,
        seed_gatherer=seed_gatherer,
        llm=llm,
        max_iterations=config.max_iterations,
        cohesion_threshold=config.cohesion_threshold,
        verbose=True,
    )
    playlist_orderer = PlaylistOrderingAgent(llm=llm, verbose=True)

    workflow_config = WorkflowConfig(
        max_retries=config.max_retries,
        timeout_per_agent=config.timeout_per_agent,
        max_recommendations=config.max_recommendations,
        enable_human_loop=True,
        require_approval=True,
    )

    agents = {
        "intent_analyzer": intent_analyzer,
        "mood_analyzer": mood_analyzer,
        "seed_gatherer": seed_gatherer,
        "recommendation_generator": recommendation_generator,
        "orchestrator": orchestrator,
        "playlist_orderer": playlist_orderer,
    }

    workflow_manager = WorkflowManager(workflow_config, agents, reccobeat_service.tools)

    return AgentResources(
        llm=llm,
        reccobeat_service=reccobeat_service,
        spotify_service=spotify_service,
        agents=agents,
        workflow_manager=workflow_manager,
    )


def get_llm() -> Any:
    """Provide the shared logged LLM instance."""

    return _create_agent_resources().llm


def get_reccobeat_service() -> RecoBeatService:
    """Provide the lazily-created RecoBeat service."""

    return _create_agent_resources().reccobeat_service


def get_spotify_service() -> SpotifyService:
    """Provide the lazily-created Spotify service."""

    return _create_agent_resources().spotify_service


def get_agents() -> Dict[str, Any]:
    """Provide the configured agent instances."""

    return _create_agent_resources().agents


def get_workflow_manager() -> WorkflowManager:
    """Provide the configured workflow manager."""

    return _create_agent_resources().workflow_manager
