from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Invocation(Base):
    """Invocation model for tracking API calls and their results."""
    __tablename__ = "invocations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    status_code = Column(Integer, nullable=False)
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="invocations")
    playlist = relationship("Playlist", back_populates="invocations")
    
    def __repr__(self):
        return f"<Invocation(id={self.id}, endpoint={self.endpoint}, status_code={self.status_code})>"