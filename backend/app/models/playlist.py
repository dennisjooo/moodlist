from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Playlist(Base):
    """Playlist model for storing generated playlists."""
    __tablename__ = "playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(255), unique=True, nullable=True, index=True)  # Workflow session UUID
    spotify_playlist_id = Column(String(255), nullable=True, index=True)
    mood_prompt = Column(Text, nullable=False)
    playlist_data = Column(JSON, nullable=True)  # Store playlist metadata
    recommendations_data = Column(JSON, nullable=True)  # Store recommendation list
    mood_analysis_data = Column(JSON, nullable=True)  # Store mood analysis results
    track_count = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    status = Column(String(50), default="created", nullable=False)  # created, generating, completed, failed
    error_message = Column(Text, nullable=True)
    
    # LLM-generated triadic color scheme
    color_primary = Column(String(7), nullable=True)  # Hex color code (e.g., #FF5733)
    color_secondary = Column(String(7), nullable=True)  # Hex color code
    color_tertiary = Column(String(7), nullable=True)  # Hex color code
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Soft delete timestamp
    
    # Relationships
    user = relationship("User", back_populates="playlists")
    invocations = relationship("Invocation", back_populates="playlist", cascade="all, delete-orphan")
    llm_invocations = relationship("LLMInvocation", back_populates="playlist", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Playlist(id={self.id}, user_id={self.user_id}, mood_prompt={self.mood_prompt[:50]}...)>"