"""Factory for creating logged LLM instances."""

from typing import Optional

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.llm_wrapper import LoggingChatModel


def create_logged_llm(
    model: Optional[str] = None,
    temperature: float = 0.25,
    enable_logging: bool = True,
    log_full_response: bool = True,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LoggingChatModel:
    """Create a logged LLM instance.

    Args:
        model: Model name (defaults to settings)
        temperature: Temperature setting
        enable_logging: Whether to enable logging
        log_full_response: Whether to log full response or just metadata
        base_url: Base URL for the LLM API
        api_key: API key for the LLM service
        **kwargs: Additional arguments to pass to ChatOpenAI

    Returns:
        LoggingChatModel instance wrapping ChatOpenAI
    """
    # Create base LLM
    base_llm = ChatOpenAI(
        model=model or "google/gemini-2.5-flash-lite-preview-09-2025",
        temperature=temperature,
        base_url=base_url or "https://openrouter.ai/api/v1",
        api_key=api_key or settings.OPENROUTER_API_KEY,
        **kwargs,
    )

    # Wrap with logging
    logged_llm = LoggingChatModel(
        wrapped_llm=base_llm,
        provider="openrouter",
        enable_logging=enable_logging,
        log_full_response=log_full_response,
    )

    return logged_llm


def create_llm_for_agent(
    agent_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    playlist_id: Optional[int] = None,
    **kwargs,
) -> LoggingChatModel:
    """Create a logged LLM instance configured for a specific agent.

    Args:
        agent_name: Name of the agent
        session_id: Workflow session ID
        user_id: User ID
        playlist_id: Playlist ID
        **kwargs: Additional arguments to pass to create_logged_llm

    Returns:
        LoggingChatModel instance with context set
    """
    llm = create_logged_llm(**kwargs)

    # Set context
    llm.set_context(
        agent_name=agent_name,
        session_id=session_id,
        user_id=user_id,
        playlist_id=playlist_id,
    )

    return llm
