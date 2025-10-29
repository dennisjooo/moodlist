"""Repository for LLM invocation logging and querying."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, and_, desc, func as sql_func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.llm_invocation import LLMInvocation
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import InternalServerError

logger = structlog.get_logger(__name__)


class LLMInvocationRepository(BaseRepository[LLMInvocation]):
    """Repository for LLM invocation-specific database operations."""

    @property
    def model_class(self) -> type[LLMInvocation]:
        """Return the LLMInvocation model class."""
        return LLMInvocation

    async def create_llm_invocation_log(
        self,
        model_name: str,
        prompt: str,
        user_id: Optional[int] = None,
        playlist_id: Optional[int] = None,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        response: Optional[str] = None,
        response_metadata: Optional[Dict[str, Any]] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        agent_name: Optional[str] = None,
        operation: Optional[str] = None,
        context_metadata: Optional[Dict[str, Any]] = None,
        commit: bool = True
    ) -> LLMInvocation:
        """Create an LLM invocation log entry.

        Args:
            model_name: Name of the LLM model used
            prompt: The prompt sent to the LLM
            user_id: User ID (optional)
            playlist_id: Playlist ID (optional)
            session_id: Workflow session ID (optional)
            provider: LLM provider name (optional)
            temperature: Temperature setting (optional)
            max_tokens: Max tokens setting (optional)
            messages: Chat messages if applicable (optional)
            response: The response from the LLM (optional)
            response_metadata: Additional response metadata (optional)
            prompt_tokens: Number of tokens in prompt (optional)
            completion_tokens: Number of tokens in completion (optional)
            total_tokens: Total tokens used (optional)
            latency_ms: Latency in milliseconds (optional)
            cost_usd: Estimated cost in USD (optional)
            success: Whether the call was successful
            error_message: Error message if failed (optional)
            error_type: Type of error if failed (optional)
            agent_name: Name of the agent making the call (optional)
            operation: Operation being performed (optional)
            context_metadata: Additional context metadata (optional)
            commit: Whether to commit the transaction

        Returns:
            Created LLMInvocation instance

        Raises:
            InternalServerError: If database operation fails
        """
        try:
            llm_invocation = LLMInvocation(
                user_id=user_id,
                playlist_id=playlist_id,
                session_id=session_id,
                model_name=model_name,
                provider=provider,
                temperature=temperature,
                max_tokens=max_tokens,
                prompt=prompt,
                messages=messages,
                response=response,
                response_metadata=response_metadata,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                success=1 if success else 0,
                error_message=error_message,
                error_type=error_type,
                agent_name=agent_name,
                operation=operation,
                context_metadata=context_metadata
            )

            self.session.add(llm_invocation)

            if commit:
                await self.session.commit()
                await self.session.refresh(llm_invocation)
            else:
                await self.session.flush()

            self.logger.debug(
                "LLM invocation log created",
                invocation_id=getattr(llm_invocation, "id", None),
                model=model_name,
                agent=agent_name,
                success=success
            )

            return llm_invocation

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error creating LLM invocation log",
                model=model_name,
                agent=agent_name,
                error=str(e)
            )
            await self.session.rollback()
            raise InternalServerError("Failed to create LLM invocation log")

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[LLMInvocation]:
        """Get LLM invocations by user ID.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of LLMInvocation instances
        """
        try:
            query = select(LLMInvocation).where(
                LLMInvocation.user_id == user_id
            ).order_by(desc(LLMInvocation.created_at))

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(LLMInvocation, relationship)))

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug("Retrieved LLM invocations by user", user_id=user_id, count=len(invocations))
            return list(invocations)

        except Exception as e:
            self.logger.error("Error retrieving LLM invocations by user", user_id=user_id, error=str(e))
            raise

    async def get_by_session_id(
        self,
        session_id: str,
        load_relationships: Optional[List[str]] = None
    ) -> List[LLMInvocation]:
        """Get LLM invocations by session ID.

        Args:
            session_id: Workflow session ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of LLMInvocation instances
        """
        try:
            query = select(LLMInvocation).where(
                LLMInvocation.session_id == session_id
            ).order_by(LLMInvocation.created_at)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(LLMInvocation, relationship)))

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug("Retrieved LLM invocations by session", session_id=session_id, count=len(invocations))
            return list(invocations)

        except Exception as e:
            self.logger.error("Error retrieving LLM invocations by session", session_id=session_id, error=str(e))
            raise

    async def get_session_cost_summary(self, session_id: str) -> Dict[str, Any]:
        """Get aggregate cost and usage metrics for a workflow session."""

        try:
            query = select(
                sql_func.count(LLMInvocation.id).label("invocation_count"),
                sql_func.sum(LLMInvocation.prompt_tokens).label("total_prompt_tokens"),
                sql_func.sum(LLMInvocation.completion_tokens).label("total_completion_tokens"),
                sql_func.sum(LLMInvocation.total_tokens).label("total_tokens"),
                sql_func.sum(LLMInvocation.cost_usd).label("total_cost_usd"),
            ).where(LLMInvocation.session_id == session_id)

            result = await self.session.execute(query)
            row = result.one_or_none()

            if not row:
                return {
                    "invocation_count": 0,
                    "total_prompt_tokens": 0,
                    "total_completion_tokens": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                }

            summary = {
                "invocation_count": row.invocation_count or 0,
                "total_prompt_tokens": row.total_prompt_tokens or 0,
                "total_completion_tokens": row.total_completion_tokens or 0,
                "total_tokens": row.total_tokens or 0,
                "total_cost_usd": float(row.total_cost_usd or 0),
            }

            self.logger.debug(
                "Retrieved session cost summary",
                session_id=session_id,
                summary=summary,
            )

            return summary

        except Exception as e:
            self.logger.error(
                "Error retrieving session cost summary",
                session_id=session_id,
                error=str(e),
            )
            raise

    async def get_by_agent_name(
        self,
        agent_name: str,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[LLMInvocation]:
        """Get LLM invocations by agent name.

        Args:
            agent_name: Name of the agent
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of LLMInvocation instances
        """
        try:
            query = select(LLMInvocation).where(
                LLMInvocation.agent_name == agent_name
            ).order_by(desc(LLMInvocation.created_at))

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug("Retrieved LLM invocations by agent", agent_name=agent_name, count=len(invocations))
            return list(invocations)

        except Exception as e:
            self.logger.error("Error retrieving LLM invocations by agent", agent_name=agent_name, error=str(e))
            raise

    async def get_usage_stats(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get usage statistics for LLM invocations.

        Args:
            user_id: Filter by user ID (optional)
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional)

        Returns:
            Dictionary with usage statistics
        """
        try:
            query = select(
                sql_func.count(LLMInvocation.id).label('total_invocations'),
                sql_func.sum(LLMInvocation.total_tokens).label('total_tokens'),
                sql_func.sum(LLMInvocation.cost_usd).label('total_cost'),
                sql_func.avg(LLMInvocation.latency_ms).label('avg_latency'),
                sql_func.sum(LLMInvocation.success).label('successful_calls'),
            )

            conditions = []
            if user_id:
                conditions.append(LLMInvocation.user_id == user_id)
            if start_date:
                conditions.append(LLMInvocation.created_at >= start_date)
            if end_date:
                conditions.append(LLMInvocation.created_at <= end_date)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            row = result.one()

            stats = {
                'total_invocations': row.total_invocations or 0,
                'total_tokens': row.total_tokens or 0,
                'total_cost_usd': float(row.total_cost or 0),
                'avg_latency_ms': float(row.avg_latency or 0),
                'successful_calls': row.successful_calls or 0,
                'failed_calls': (row.total_invocations or 0) - (row.successful_calls or 0)
            }

            self.logger.debug("Retrieved LLM usage stats", user_id=user_id, stats=stats)
            return stats

        except Exception as e:
            self.logger.error("Error retrieving LLM usage stats", user_id=user_id, error=str(e))
            raise

    async def get_model_usage_breakdown(
        self,
        user_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get breakdown of usage by model.

        Args:
            user_id: Filter by user ID (optional)
            days: Number of days to look back

        Returns:
            List of dictionaries with model usage stats
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            query = select(
                LLMInvocation.model_name,
                sql_func.count(LLMInvocation.id).label('count'),
                sql_func.sum(LLMInvocation.total_tokens).label('tokens'),
                sql_func.sum(LLMInvocation.cost_usd).label('cost'),
                sql_func.avg(LLMInvocation.latency_ms).label('avg_latency')
            ).where(
                LLMInvocation.created_at >= start_date
            ).group_by(
                LLMInvocation.model_name
            ).order_by(
                desc('count')
            )

            if user_id:
                query = query.where(LLMInvocation.user_id == user_id)

            result = await self.session.execute(query)
            rows = result.all()

            breakdown = [
                {
                    'model_name': row.model_name,
                    'invocation_count': row.count,
                    'total_tokens': row.tokens or 0,
                    'total_cost_usd': float(row.cost or 0),
                    'avg_latency_ms': float(row.avg_latency or 0)
                }
                for row in rows
            ]

            self.logger.debug("Retrieved model usage breakdown", user_id=user_id, days=days, models=len(breakdown))
            return breakdown

        except Exception as e:
            self.logger.error("Error retrieving model usage breakdown", user_id=user_id, error=str(e))
            raise

