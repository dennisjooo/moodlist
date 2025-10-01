from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Create async engine with asyncpg driver
engine = create_async_engine(
    settings.get_database_url().replace("postgresql://", "postgresql+asyncpg://"),
    # echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
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
