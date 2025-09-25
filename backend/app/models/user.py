from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """User model for storing user information."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    spotify_id = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    display_name = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=False)  # Encrypted
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    profile_image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    playlists = relationship("Playlist", back_populates="user", cascade="all, delete-orphan")
    invocations = relationship("Invocation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, spotify_id={self.spotify_id}, display_name={self.display_name})>"