"""User repository for user-specific database operations."""

from typing import List, Optional
from datetime import datetime

import structlog
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import insert

from app.models.user import User
from app.repositories.base_repository import BaseRepository

logger = structlog.get_logger(__name__)


class UserRepository(BaseRepository[User]):
    """Repository for user-specific database operations."""

    @property
    def model_class(self) -> type[User]:
        """Return the User model class."""
        return User

    async def get_by_spotify_id(self, spotify_id: str, load_relationships: Optional[List[str]] = None) -> Optional[User]:
        """Get user by Spotify ID.

        Args:
            spotify_id: Spotify user ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            User instance or None if not found
        """
        try:
            query = select(User).where(User.spotify_id == spotify_id)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                self.logger.debug("User retrieved by Spotify ID", spotify_id=spotify_id)
            else:
                self.logger.debug("User not found for Spotify ID", spotify_id=spotify_id)

            return user

        except Exception as e:
            self.logger.error(
                "Database error retrieving user by Spotify ID",
                spotify_id=spotify_id,
                error=str(e)
            )
            raise

    async def get_by_email(self, email: str, load_relationships: Optional[List[str]] = None) -> Optional[User]:
        """Get user by email address.

        Args:
            email: User email address
            load_relationships: List of relationship names to eagerly load

        Returns:
            User instance or None if not found
        """
        try:
            query = select(User).where(User.email == email)

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                self.logger.debug("User retrieved by email", email=email)
            else:
                self.logger.debug("User not found for email", email=email)

            return user

        except Exception as e:
            self.logger.error(
                "Database error retrieving user by email",
                email=email,
                error=str(e)
            )
            raise

    async def get_active_users(
        self,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[User]:
        """Get all active users.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of active users
        """
        return await self.get_all(
            skip=skip,
            limit=limit,
            filters={"is_active": True},
            order_by="created_at",
            order_desc=True,
            load_relationships=load_relationships
        )

    async def update_tokens(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime
    ) -> User:
        """Update user's Spotify tokens.

        Args:
            user_id: User ID
            access_token: New access token
            refresh_token: New refresh token
            token_expires_at: Token expiration timestamp

        Returns:
            Updated user instance
        """
        return await self.update(
            user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at
        )

    async def update_profile(
        self,
        user_id: int,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        profile_image_url: Optional[str] = None
    ) -> User:
        """Update user's profile information.

        Args:
            user_id: User ID
            display_name: New display name
            email: New email address
            profile_image_url: New profile image URL

        Returns:
            Updated user instance
        """
        update_data = {}
        if display_name is not None:
            update_data["display_name"] = display_name
        if email is not None:
            update_data["email"] = email
        if profile_image_url is not None:
            update_data["profile_image_url"] = profile_image_url

        if not update_data:
            # No updates provided, just return the user
            return await self.get_by_id_or_fail(user_id)

        return await self.update(user_id, **update_data)

    async def deactivate_user(self, user_id: int) -> User:
        """Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance
        """
        return await self.update(user_id, is_active=False)

    async def reactivate_user(self, user_id: int) -> User:
        """Reactivate a user account.

        Args:
            user_id: User ID

        Returns:
            Updated user instance
        """
        return await self.update(user_id, is_active=True)

    async def get_users_created_after(
        self,
        created_after: datetime,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[User]:
        """Get users created after a specific timestamp.

        Args:
            created_after: Creation timestamp threshold
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of users created after the timestamp
        """
        try:
            query = select(User).where(User.created_at > created_after)

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by creation date (newest first)
            query = query.order_by(desc(User.created_at))

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            users = result.scalars().all()

            self.logger.debug(
                "Users retrieved by creation date",
                created_after=created_after.isoformat(),
                count=len(users),
                skip=skip,
                limit=limit
            )

            return list(users)

        except Exception as e:
            self.logger.error(
                "Database error retrieving users by creation date",
                created_after=created_after.isoformat(),
                error=str(e)
            )
            raise

    async def search_users(
        self,
        search_term: str,
        skip: int = 0,
        limit: Optional[int] = None,
        load_relationships: Optional[List[str]] = None
    ) -> List[User]:
        """Search users by display name or email.

        Args:
            search_term: Search term for display name or email
            skip: Number of records to skip
            limit: Maximum number of records to return
            load_relationships: List of relationship names to eagerly load

        Returns:
            List of matching users
        """
        try:
            search_pattern = f"%{search_term}%"
            query = select(User).where(
                and_(
                    User.is_active.is_(True),
                    or_(
                        User.display_name.ilike(search_pattern),
                        User.email.ilike(search_pattern)
                    )
                )
            )

            # Apply pagination
            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            # Order by display name
            query = query.order_by(User.display_name)

            # Apply eager loading
            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            users = result.scalars().all()

            self.logger.debug(
                "Users searched successfully",
                search_term=search_term,
                count=len(users),
                skip=skip,
                limit=limit
            )

            return list(users)

        except Exception as e:
            self.logger.error(
                "Database error searching users",
                search_term=search_term,
                error=str(e)
            )
            raise

    async def get_active_user_by_spotify_id(self, spotify_id: str, load_relationships: Optional[List[str]] = None) -> Optional[User]:
        """Get active user by Spotify ID.

        Args:
            spotify_id: Spotify user ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Active user instance or None if not found or inactive
        """
        try:
            query = select(User).where(
                and_(
                    User.spotify_id == spotify_id,
                    User.is_active.is_(True)
                )
            )

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                self.logger.debug("Active user retrieved by Spotify ID", spotify_id=spotify_id)
            else:
                self.logger.debug("Active user not found for Spotify ID", spotify_id=spotify_id)

            return user

        except Exception as e:
            self.logger.error(
                "Database error retrieving active user by Spotify ID",
                spotify_id=spotify_id,
                error=str(e)
            )
            raise

    async def get_active_user_by_id(self, user_id: int, load_relationships: Optional[List[str]] = None) -> Optional[User]:
        """Get active user by ID.

        Args:
            user_id: User ID
            load_relationships: List of relationship names to eagerly load

        Returns:
            Active user instance or None if not found or inactive
        """
        try:
            query = select(User).where(
                and_(
                    User.id == user_id,
                    User.is_active.is_(True)
                )
            )

            if load_relationships:
                for relationship in load_relationships:
                    query = query.options(selectinload(getattr(User, relationship)))

            result = await self.session.execute(query)
            user = result.scalar_one_or_none()

            if user:
                self.logger.debug("Active user retrieved by ID", user_id=user_id)
            else:
                self.logger.debug("Active user not found for ID", user_id=user_id)

            return user

        except Exception as e:
            self.logger.error(
                "Database error retrieving active user by ID",
                user_id=user_id,
                error=str(e)
            )
            raise

    async def create_or_update_user(
        self,
        spotify_id: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
        display_name: str,
        email: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        commit: bool = True
    ) -> User:
        """Create a new user or update existing user's tokens and profile.

        Args:
            spotify_id: Spotify user ID
            access_token: Spotify access token
            refresh_token: Spotify refresh token
            token_expires_at: Token expiration timestamp
            display_name: User display name
            email: User email (optional)
            profile_image_url: Profile image URL (optional)
            commit: Whether to commit the transaction

        Returns:
            Created or updated user instance
        """
        try:
            existing_user = await self.get_by_spotify_id(spotify_id)

            if existing_user:
                existing_user.access_token = access_token
                existing_user.refresh_token = refresh_token
                existing_user.token_expires_at = token_expires_at
                existing_user.display_name = display_name
                if email:
                    existing_user.email = email
                if profile_image_url:
                    existing_user.profile_image_url = profile_image_url
                existing_user.is_active = True

                if commit:
                    await self.session.commit()
                    await self.session.refresh(existing_user)
                else:
                    await self.session.flush()

                self.logger.info("Updated existing user", user_id=existing_user.id, spotify_id=spotify_id)
                return existing_user
            else:
                user = User(
                    spotify_id=spotify_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    token_expires_at=token_expires_at,
                    display_name=display_name,
                    email=email,
                    profile_image_url=profile_image_url,
                    is_active=True
                )

                self.session.add(user)

                if commit:
                    await self.session.commit()
                    await self.session.refresh(user)
                else:
                    await self.session.flush()

                self.logger.info("Created new user", user_id=getattr(user, "id", None), spotify_id=spotify_id)
                return user

        except Exception as e:
            self.logger.error(
                "Database error creating or updating user",
                spotify_id=spotify_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def upsert_user(
        self,
        spotify_id: str,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime,
        display_name: str,
        email: Optional[str] = None,
        profile_image_url: Optional[str] = None,
        is_spotify_whitelisted: bool = True,
    ) -> User:
        """Create or update user in a single database operation using UPSERT.
        
        This is significantly faster than the get_by_spotify_id + update/create pattern.
        Uses PostgreSQL's INSERT ... ON CONFLICT for optimal performance.
        
        Args:
            spotify_id: Spotify user ID
            access_token: Spotify access token
            refresh_token: Spotify refresh token  
            token_expires_at: Token expiration timestamp
            display_name: User display name
            email: User email (optional)
            profile_image_url: Profile image URL (optional)
            is_spotify_whitelisted: Whether user has Spotify API access (dev mode whitelist)

        Returns:
            Created or updated user instance
        """
        try:
            stmt = insert(User).values(
                spotify_id=spotify_id,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                display_name=display_name,
                email=email,
                profile_image_url=profile_image_url,
                is_active=True,
                is_spotify_whitelisted=is_spotify_whitelisted
            ).on_conflict_do_update(
                index_elements=['spotify_id'],
                set_={
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_expires_at': token_expires_at,
                    'display_name': display_name,
                    'email': email,
                    'profile_image_url': profile_image_url,
                    'is_active': True,
                    'is_spotify_whitelisted': is_spotify_whitelisted,
                    'updated_at': func.now()
                }
            ).returning(User)
            
            result = await self.session.execute(stmt)
            user = result.scalar_one()
            await self.session.flush()
            
            self.logger.info(
                "User upserted successfully",
                spotify_id=spotify_id,
                user_id=user.id
            )
            
            return user
            
        except Exception as e:
            self.logger.error(
                "Database error upserting user",
                spotify_id=spotify_id,
                error=str(e)
            )
            await self.session.rollback()
            raise

    async def update_tokens_and_commit(
        self,
        user_id: int,
        access_token: str,
        refresh_token: str,
        token_expires_at: datetime
    ) -> User:
        """Update user tokens and commit the transaction.

        Args:
            user_id: User ID
            access_token: New access token
            refresh_token: New refresh token
            token_expires_at: Token expiration timestamp

        Returns:
            Updated user instance
        """
        try:
            user = await self.get_by_id_or_fail(user_id)

            user.access_token = access_token
            user.refresh_token = refresh_token
            user.token_expires_at = token_expires_at

            await self.session.commit()
            await self.session.refresh(user)

            self.logger.info("User tokens updated", user_id=user_id)
            return user

        except Exception as e:
            self.logger.error(
                "Database error updating user tokens",
                user_id=user_id,
                error=str(e)
            )
            await self.session.rollback()
            raise
