"""LLM Invocation model for tracking LLM API calls."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class LLMInvocation(Base):
    """Model for tracking LLM invocations and their results."""

    __tablename__ = "llm_invocations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)  # Workflow session ID

    # LLM Configuration
    model_name = Column(String(255), nullable=False, index=True)
    provider = Column(String(100), nullable=True)  # openai, anthropic, openrouter, etc.
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)

    # Request/Response Data
    prompt = Column(Text, nullable=False)  # The full prompt sent
    messages = Column(JSON, nullable=True)  # Chat messages if applicable
    response = Column(Text, nullable=True)  # The full response received
    response_metadata = Column(JSON, nullable=True)  # Additional response metadata

    # Token Usage
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)

    # Performance Metrics
    latency_ms = Column(Integer, nullable=True)  # Time taken for the call
    cost_usd = Column(Float, nullable=True)  # Estimated cost in USD

    # Error Tracking
    success = Column(Integer, nullable=False, default=1)  # 1 for success, 0 for failure
    error_message = Column(Text, nullable=True)
    error_type = Column(String(100), nullable=True)

    # Context
    agent_name = Column(
        String(255), nullable=True, index=True
    )  # Which agent made the call
    operation = Column(String(255), nullable=True)  # What operation was being performed
    context_metadata = Column(JSON, nullable=True)  # Additional context

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="llm_invocations")
    playlist = relationship("Playlist", back_populates="llm_invocations")

    def __repr__(self):
        return f"<LLMInvocation(id={self.id}, model={self.model_name}, agent={self.agent_name}, success={self.success})>"
