"""FastAPI application factory."""
import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.middleware import LoggingMiddleware, InvocationStatusMiddleware
from app.core.limiter import limiter
from app.auth.routes import router as auth_router
from app.spotify.routes import router as spotify_router
from app.agents.routes import router as agent_router
from app.playlists.routes import router as playlist_router

logger = structlog.get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Mood-based playlist generation API",
        lifespan=lifespan,
    )

    # Add global exception handler for CORS on errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", error=str(exc), error_type=type(exc).__name__, path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers={
                "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
                "Access-Control-Allow-Credentials": "true",
            }
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

    # Add TrustedHostMiddleware if ALLOWED_HOSTS is configured
    # Automatically includes Render hostname via RENDER_EXTERNAL_URL
    if settings.ALLOWED_HOSTS:
        logger.info("Enabling TrustedHostMiddleware", allowed_hosts=settings.ALLOWED_HOSTS)
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

