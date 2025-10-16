"""Base repository class with common database operations."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any, Dict

import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, desc, asc
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import NotFoundException, ValidationException, InternalServerError

T = TypeVar('T')

logger = structlog.get_logger(__name__)


class BaseRepository(ABC, Generic[T]):
    """Base repository class providing common CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.logger = logger.bind(repository=self.__class__.__name__)

    @property
    @abstractmethod
    def model_class(self) -> type[T]:
        """Return the SQLAlchemy model class for this repository."""
        pass

    async def get_by_id(self, id: int, load_relationships: Optional[List[str]] = None) -> Optional[T]:
        """Get entity by ID.

        Args:
            id: Entity ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Entity instance or None if not found
        """
        try:
            query = select(self.model_class).where(self.model_class.id == id)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(self.model_class, relationship)))

            result = await self.session.execute(query)
            entity = result.scalar_one_or_none()

            if entity:
                self.logger.debug("Entity retrieved successfully", entity_id=id)
            else:
                self.logger.debug("Entity not found", entity_id=id)

            return entity

        except SQLAlchemyError as e:
            self.logger.error("Database error retrieving entity", entity_id=id, error=str(e))
            raise InternalServerError(f"Failed to retrieve {self.model_class.__name__}")

    async def get_by_id_or_fail(self, id: int, load_relationships: Optional[List[str]] = None) -> T:
        """Get entity by ID or raise NotFoundException.

        Args:
            id: Entity ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Entity instance

        Raises:
            NotFoundException: If entity not found
        """
        entity = await self.get_by_id(id, load_relationships)
        if not entity:
            raise NotFoundException(self.model_class.__name__, str(id))
        return entity

    async def get_all(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        filters: Optional[Dict[str, Any]] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[T]:
        """Get all entities with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            order_by: Field to order by
            order_desc: Order descending if True
            filters: Dictionary of field filters
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of entities
        """
        try:
            query = select(self.model_class)

            # Apply filters
            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        conditions.append(getattr(self.model_class, field) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                order_func = desc if order_desc else asc
                query = query.order_by(order_func(getattr(self.model_class, order_by)))

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(self.model_class, relationship)))

            result = await self.session.execute(query)
            entities = result.scalars().all()

            self.logger.debug(
                "Entities retrieved successfully",
                count=len(entities),
                filters=filters,
                skip=skip,
                limit=limit
            )

            return list(entities)

        except SQLAlchemyError as e:
            self.logger.error("Database error retrieving entities", error=str(e))
            raise InternalServerError(f"Failed to retrieve {self.model_class.__name__} entities")

    async def create(self, **kwargs) -> T:
        """Create a new entity.

        Args:
            **kwargs: Entity field values

        Returns:
            Created entity instance

        Raises:
            ValidationException: If required fields are missing or invalid
        """
        try:
            entity = self.model_class(**kwargs)
            self.session.add(entity)
            await self.session.flush()  # Get the ID without committing

            self.logger.info("Entity created successfully", entity_id=getattr(entity, 'id', None))
            return entity

        except IntegrityError as e:
            self.logger.error("Integrity error creating entity", error=str(e))
            await self.session.rollback()
            raise ValidationException("Entity creation failed due to constraint violation")

        except SQLAlchemyError as e:
            self.logger.error("Database error creating entity", error=str(e))
            await self.session.rollback()
            raise InternalServerError(f"Failed to create {self.model_class.__name__}")

    async def update(self, id: int, **kwargs) -> T:
        """Update an existing entity.

        Args:
            id: Entity ID
            **kwargs: Fields to update

        Returns:
            Updated entity instance

        Raises:
            NotFoundException: If entity not found
        """
        try:
            # Get current entity
            entity = await self.get_by_id_or_fail(id)

            # Update fields
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            await self.session.flush()

            self.logger.info("Entity updated successfully", entity_id=id)
            return entity

        except NotFoundException:
            raise
        except IntegrityError as e:
            self.logger.error("Integrity error updating entity", entity_id=id, error=str(e))
            await self.session.rollback()
            raise ValidationException("Entity update failed due to constraint violation")
        except SQLAlchemyError as e:
            self.logger.error("Database error updating entity", entity_id=id, error=str(e))
            await self.session.rollback()
            raise InternalServerError(f"Failed to update {self.model_class.__name__}")

    async def delete(self, id: int) -> bool:
        """Delete an entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found

        Raises:
            InternalServerError: If database operation fails
        """
        try:
            query = delete(self.model_class).where(self.model_class.id == id)
            result = await self.session.execute(query)

            deleted = result.rowcount > 0

            if deleted:
                self.logger.info("Entity deleted successfully", entity_id=id)
            else:
                self.logger.debug("Entity not found for deletion", entity_id=id)

            return deleted

        except SQLAlchemyError as e:
            self.logger.error("Database error deleting entity", entity_id=id, error=str(e))
            await self.session.rollback()
            raise InternalServerError(f"Failed to delete {self.model_class.__name__}")

    async def exists(self, id: int) -> bool:
        """Check if entity exists by ID.

        Args:
            id: Entity ID

        Returns:
            True if exists, False otherwise
        """
        try:
            query = select(self.model_class.id).where(self.model_class.id == id)
            result = await self.session.execute(query)
            exists = result.scalar_one_or_none() is not None

            self.logger.debug("Entity existence checked", entity_id=id, exists=exists)
            return exists

        except SQLAlchemyError as e:
            self.logger.error("Database error checking entity existence", entity_id=id, error=str(e))
            raise InternalServerError(f"Failed to check {self.model_class.__name__} existence")

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filters.

        Args:
            filters: Dictionary of field filters

        Returns:
            Number of entities matching filters
        """
        try:
            query = select(self.model_class)

            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model_class, field):
                        conditions.append(getattr(self.model_class, field) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            count = len(result.scalars().all())

            self.logger.debug("Entities counted", count=count, filters=filters)
            return count

        except SQLAlchemyError as e:
            self.logger.error("Database error counting entities", error=str(e))
            raise InternalServerError(f"Failed to count {self.model_class.__name__} entities")