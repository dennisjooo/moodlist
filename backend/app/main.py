from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import LoggingMiddleware, InvocationStatusMiddleware
from app.core.limiter import limiter
from app.agents.core.cache import cache_manager
from app.auth.routes import router as auth_router
from app.spotify.routes import router as spotify_router
from app.agents.routes import router as agent_router
from app.playlists.routes import router as playlist_router

logger = structlog.get_logger(__name__)


def validate_required_secrets():
    """Validate all required secrets are set properly at startup."""
    errors = []
    weak_values = ["changeme", "secret", "password", "12345", "test", "example"]
    
    if not settings.JWT_SECRET_KEY:
        errors.append("JWT_SECRET_KEY is not set")
    elif len(settings.JWT_SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")
    elif settings.JWT_SECRET_KEY.lower() in weak_values:
        errors.append("JWT_SECRET_KEY is using a weak default value")
    
    if not settings.SESSION_SECRET_KEY:
        errors.append("SESSION_SECRET_KEY is not set")
    elif len(settings.SESSION_SECRET_KEY) < 32:
        errors.append("SESSION_SECRET_KEY must be at least 32 characters")
    elif settings.SESSION_SECRET_KEY.lower() in weak_values:
        errors.append("SESSION_SECRET_KEY is using a weak default value")
    
    if not settings.SPOTIFY_CLIENT_SECRET:
        errors.append("SPOTIFY_CLIENT_SECRET is not set")
    elif settings.SPOTIFY_CLIENT_SECRET.lower() in weak_values:
        errors.append("SPOTIFY_CLIENT_SECRET is using a weak default value")
    
    if not settings.OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is not set")
    
    if not settings.GROQ_API_KEY:
        errors.append("GROQ_API_KEY is not set")
    
    if not settings.CEREBRAS_API_KEY:
        errors.append("CEREBRAS_API_KEY is not set")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise RuntimeError(
            "Application started with invalid configuration. "
            f"Found {len(errors)} error(s). Check logs for details."
        )
    
    logger.info("All required secrets validated successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Startup
    logger.info("Starting application", app_name=settings.APP_NAME, environment=settings.APP_ENV)
    
    # Validate required secrets
    validate_required_secrets()

    # Initialize cache manager with Valkey if URL is provided
    from app.agents.core.cache import CacheManager
    global cache_manager
    if settings.REDIS_URL:
        logger.info("Initializing cache manager with Valkey", redis_url=settings.REDIS_URL)
        cache_manager = CacheManager(settings.REDIS_URL)
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

    if settings.ENABLE_RATE_LIMITING:
        from slowapi.middleware import SlowAPIMiddleware
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
            return settings.rate_limit_response(exc)

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