from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import LoggingMiddleware, InvocationStatusMiddleware
from app.agents.core.cache import cache_manager
from app.auth.routes import router as auth_router
from app.spotify.routes import router as spotify_router
from app.agents.routes import router as agent_router
from app.playlists.routes import router as playlist_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting application", app_name=settings.APP_NAME, environment=settings.APP_ENV)

    # Initialize cache manager with Valkey if URL is provided
    global cache_manager
    if settings.REDIS_URL:
        logger.info("Initializing cache manager with Valkey", redis_url=settings.REDIS_URL)
        cache_manager = cache_manager.__class__(settings.REDIS_URL)
    else:
        logger.info("No Valkey URL provided, using in-memory cache")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    logger.info("Shutting down application", app_name=settings.APP_NAME)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Mood-based playlist generation API",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(InvocationStatusMiddleware)
    
    # Include routers
    app.include_router(
        auth_router,
        prefix="/api/auth",
        tags=["authentication"]
    )
    app.include_router(
        spotify_router,
        prefix="/api/spotify",
        tags=["spotify"]
    )
    app.include_router(
        agent_router,
        prefix="/api/agents",
        tags=["agents"]
    )
    app.include_router(
        playlist_router,
        prefix="/api",
        tags=["playlists"]
    )
    
    return app


app = create_application()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}