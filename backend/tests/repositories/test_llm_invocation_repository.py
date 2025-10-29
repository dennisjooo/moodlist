import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.llm_invocation import LLMInvocation
from app.repositories.llm_invocation_repository import LLMInvocationRepository


@pytest.fixture
async def async_session() -> AsyncSession:
    """Provide an in-memory SQLite session for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session_factory = sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        async with async_session_factory() as session:
            yield session
            await session.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_session_cost_summary_returns_aggregates(async_session: AsyncSession):
    repo = LLMInvocationRepository(async_session)
    session_id = "session-123"

    invocations = [
        LLMInvocation(
            session_id=session_id,
            model_name="model-a",
            prompt="prompt",
            cost_usd=0.1,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        LLMInvocation(
            session_id=session_id,
            model_name="model-b",
            prompt="prompt",
            cost_usd=0.2,
            prompt_tokens=12,
            completion_tokens=6,
            total_tokens=18,
        ),
        LLMInvocation(
            session_id=session_id,
            model_name="model-c",
            prompt="prompt",
            cost_usd=0.3,
            prompt_tokens=14,
            completion_tokens=7,
            total_tokens=21,
        ),
    ]

    async_session.add_all(invocations)
    await async_session.commit()

    summary = await repo.get_session_cost_summary(session_id)

    assert summary["invocation_count"] == 3
    assert summary["total_prompt_tokens"] == 36
    assert summary["total_completion_tokens"] == 18
    assert summary["total_tokens"] == 54
    assert summary["total_cost_usd"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_get_session_cost_summary_returns_zero_for_missing_session(async_session: AsyncSession):
    repo = LLMInvocationRepository(async_session)

    summary = await repo.get_session_cost_summary("missing-session")

    assert summary == {
        "invocation_count": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
    }
