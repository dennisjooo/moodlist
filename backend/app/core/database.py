from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine with asyncpg driver and optimized connection pool settings
engine = create_async_engine(
    settings.get_database_url().replace("postgresql://", "postgresql+asyncpg://"),
    # echo=settings.DEBUG,  # Only log SQL in debug mode
    future=True,
    
    # Optimized connection pool settings for production
    pool_size=20,              # Base pool size (increased from 10)
    max_overflow=10,           # Extra connections under load (decreased from 20 for better control)
    pool_pre_ping=True,        # Test connections before using them
    pool_recycle=3600,         # Recycle connections after 1 hour
    
    # Performance settings
    echo_pool=False,           # Don't log pool checkouts
    
    # Connection arguments for PostgreSQL/asyncpg
    connect_args={
        "prepared_statement_cache_size": 100,
        "statement_cache_size": 100,
        "server_settings": {
            "application_name": "moodlist_api",
            "jit": "off",      # Disable JIT for faster simple queries
        },
    },
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.

    Note: Does not auto-commit. Write operations should commit explicitly.
    This allows better control over transaction boundaries and avoids
    unnecessary commits for read-only operations.
    """
    async with async_session_factory() as session:
        try:
            yield session
            # Let caller decide when to commit
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get read-only database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
