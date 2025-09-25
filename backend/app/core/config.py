from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = Field(default="MoodList API", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Database
    DATABASE_URL: str = Field(env="DATABASE_URL")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    RDS_HOST: Optional[str] = Field(default=None, env="RDS_HOST")
    RDS_PORT: int = Field(default=5432, env="RDS_PORT")
    RDS_DATABASE: str = Field(default="moodlist_db", env="RDS_DATABASE")
    RDS_USERNAME: str = Field(default=None, env="RDS_USERNAME")
    RDS_PASSWORD: str = Field(default=None, env="RDS_PASSWORD")
    
    # JWT
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(default=7, env="JWT_REFRESH_EXPIRATION_DAYS")
    
    # Session
    SESSION_SECRET_KEY: str = Field(env="SESSION_SECRET_KEY")
    SESSION_EXPIRATION_MINUTES: int = Field(default=30, env="SESSION_EXPIRATION_MINUTES")
    
    # Spotify
    SPOTIFY_CLIENT_ID: str = Field(env="SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: str = Field(env="SPOTIFY_CLIENT_SECRET")
    SPOTIFY_REDIRECT_URI: str = Field(env="SPOTIFY_REDIRECT_URI")
    
    # AWS
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    
    # CORS
    FRONTEND_URL: str = Field(default="http://127.0.0.1:3000", env="FRONTEND_URL")
    ALLOWED_ORIGINS: List[str] = Field(default_factory=lambda: [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ])
    
    # Redis
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """Get allowed hosts based on environment."""
        if self.APP_ENV == "production":
            return ["your-production-domain.com"]
        return ["localhost", "127.0.0.1", "0.0.0.0"]
    
    def get_database_url(self) -> str:
        """Get the appropriate database URL based on environment."""
        return (
            f"postgresql://{self.RDS_USERNAME}:{self.RDS_PASSWORD}"
            f"@{self.RDS_HOST}:{self.RDS_PORT}/{self.RDS_DATABASE}"
        )
        
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()