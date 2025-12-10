"""Invocation repository for invocation-specific database operations."""

from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import and_, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.exceptions import InternalServerError
from app.models.invocation import Invocation
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class InvocationRepository(BaseRepository[Invocation]):
    """Repository for invocation-specific database operations."""

    @property
    def model_class(self) -> type[Invocation]:
        """Return the Invocation model class."""
        return Invocation

    async def create_invocation_log(
        self,
        user_id: Optional[int],
        playlist_id: Optional[int],
        endpoint: str,
        method: str,
        status_code: int,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        commit: bool = True,
    ) -> Invocation:
        """Create invocation log entry.

        Args:
            user_id: User ID (optional)
            playlist_id: Playlist ID (optional)
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            request_data: Request data JSON (optional)
            response_data: Response data JSON (optional)
            error_message: Error message if any (optional)
            processing_time_ms: Processing time in milliseconds (optional)
            ip_address: Client IP address (optional)
            user_agent: User agent string (optional)
            commit: Whether to commit the transaction after creating the log

        Returns:
            Created invocation instance

        Raises:
            InternalServerError: If database operation fails
        """
        try:
            invocation = Invocation(
                user_id=user_id,
                playlist_id=playlist_id,
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                request_data=request_data,
                response_data=response_data,
                error_message=error_message,
                processing_time_ms=processing_time_ms,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self.session.add(invocation)

            if commit:
                await self.session.commit()
                await self.session.refresh(invocation)
            else:
                await self.session.flush()

            self.logger.debug(
                "Invocation log created",
                invocation_id=getattr(invocation, "id", None),
                endpoint=endpoint,
                method=method,
                status_code=status_code,
                processing_time_ms=getattr(invocation, "processing_time_ms", None),
            )

            return invocation

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error creating invocation log",
                endpoint=endpoint,
                method=method,
                error=str(e),
            )
            await self.session.rollback()
            raise InternalServerError("Failed to create invocation log")

    async def get_by_user_id(
        self,
        user_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None,
    ) -> List[Invocation]:
        """Get invocations for a specific user."""
        try:
            query = select(Invocation).where(Invocation.user_id == user_id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            query = query.order_by(desc(Invocation.created_at))

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(
                        selectinload(getattr(Invocation, relationship))
                    )

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug(
                "User invocations retrieved",
                user_id=user_id,
                count=len(invocations),
                skip=skip,
                limit=limit,
            )

            return list(invocations)

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving user invocations",
                user_id=user_id,
                error=str(e),
            )
            raise InternalServerError("Failed to retrieve invocations")

    async def get_by_playlist_id(
        self,
        playlist_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None,
    ) -> List[Invocation]:
        """Get invocations for a specific playlist."""
        try:
            query = select(Invocation).where(Invocation.playlist_id == playlist_id)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            query = query.order_by(desc(Invocation.created_at))

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(
                        selectinload(getattr(Invocation, relationship))
                    )

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug(
                "Playlist invocations retrieved",
                playlist_id=playlist_id,
                count=len(invocations),
                skip=skip,
                limit=limit,
            )

            return list(invocations)

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving playlist invocations",
                playlist_id=playlist_id,
                error=str(e),
            )
            raise InternalServerError("Failed to retrieve invocations")

    async def get_by_endpoint(
        self,
        endpoint: str,
        method: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> List[Invocation]:
        """Get invocations for a specific endpoint."""
        try:
            conditions = [Invocation.endpoint == endpoint]
            if method:
                conditions.append(Invocation.method == method)

            query = select(Invocation).where(and_(*conditions))

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            query = query.order_by(desc(Invocation.created_at))

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug(
                "Endpoint invocations retrieved",
                endpoint=endpoint,
                method=method,
                count=len(invocations),
                skip=skip,
                limit=limit,
            )

            return list(invocations)

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving endpoint invocations",
                endpoint=endpoint,
                method=method,
                error=str(e),
            )
            raise InternalServerError("Failed to retrieve invocations")

    async def get_failed_invocations(
        self, skip: int = 0, limit: Optional[int] = None, min_status_code: int = 400
    ) -> List[Invocation]:
        """Get failed invocations (status code >= min_status_code)."""
        try:
            query = select(Invocation).where(Invocation.status_code >= min_status_code)

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            query = query.order_by(desc(Invocation.created_at))

            result = await self.session.execute(query)
            invocations = result.scalars().all()

            self.logger.debug(
                "Failed invocations retrieved",
                min_status_code=min_status_code,
                count=len(invocations),
                skip=skip,
                limit=limit,
            )

            return list(invocations)

        except SQLAlchemyError as e:
            self.logger.error(
                "Database error retrieving failed invocations",
                min_status_code=min_status_code,
                error=str(e),
            )
            raise InternalServerError("Failed to retrieve failed invocations")
