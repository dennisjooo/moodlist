"""Application lifespan management."""
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.database import engine, Base
from app.core.validation import validate_required_secrets

logger = structlog.get_logger(__name__)


def _initialize_cache_manager():
    """Initialize cache manager singleton based on configuration.
    
    Returns:
        CacheManager: Initialized cache manager instance
    """
    from app.agents.core.cache import CacheManager
    
    if settings.REDIS_URL:
        logger.info("Initializing cache manager with Valkey", redis_url=settings.REDIS_URL)
        return CacheManager(settings.REDIS_URL)
    else:
        logger.info("No Valkey URL provided, using in-memory cache")
        return CacheManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    # Configure logging first
    from app.core.logging_config import configure_logging
    configure_logging(log_level=settings.LOG_LEVEL, app_env=settings.APP_ENV)

    # Startup
    logger.info("Starting application", app_name=settings.APP_NAME, environment=settings.APP_ENV)

    # Validate required secrets before proceeding
    validate_required_secrets()

    # Initialize cache manager - replace global singleton
    from app.agents.core.cache import set_cache_manager

    new_cache_manager = _initialize_cache_manager()
    set_cache_manager(new_cache_manager)

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    logger.info("Shutting down application", app_name=settings.APP_NAME)

    # Gracefully shutdown active workflows first
    try:
        from app.agents.routes.dependencies import get_workflow_manager
        workflow_manager = get_workflow_manager()
        logger.info("Initiating graceful shutdown for active workflows")
        await workflow_manager.graceful_shutdown(timeout=300)  # 5 minutes max
    except Exception as e:
        logger.error("Error during workflow graceful shutdown", error=str(e), exc_info=True)

    # Close cache manager connection
    from app.agents.core.cache import get_cache_manager

    cache_manager = get_cache_manager()
    if hasattr(cache_manager, 'close'):
        logger.info("Closing cache manager connection")
        await cache_manager.close()
