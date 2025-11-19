import time
import json
import jwt
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.models.user import User
from app.auth.security import verify_token
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging all requests and responses to database."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Get request data
        request_data = await self._get_request_data(request)

        # Get current user if available
        user: Optional[User] = None
        try:
            user = await self._get_current_user(request)
        except Exception as e:
            logger.debug("Failed to extract user from request", error=str(e))

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_message = None
        except HTTPException as e:
            status_code = e.status_code
            error_message = e.detail
            response = JSONResponse(
                status_code=status_code, content={"detail": e.detail}
            )
        except Exception as e:
            status_code = 500
            error_message = str(e)
            response = JSONResponse(
                status_code=500, content={"detail": "Internal server error"}
            )

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log to database
        try:
            await self._log_to_database(
                request=request,
                user=user,
                status_code=status_code,
                request_data=request_data,
                response_data=await self._get_response_data(response),
                error_message=error_message,
                processing_time_ms=processing_time_ms,
            )
        except Exception as e:
            # Don't fail the request if logging fails
            logger.error("Failed to log request to database", error=str(e))

        return response

    async def _get_request_data(self, request: Request) -> Dict[str, Any]:
        """Extract relevant request data for logging."""
        # Don't consume request body for POST/PUT/PATCH requests as it prevents route handlers from reading it
        body_data = None
        if request.method in ["GET", "DELETE", "HEAD", "OPTIONS"]:
            try:
                body = await request.body()
                if body:
                    try:
                        body_data = json.loads(body)
                    except json.JSONDecodeError:
                        body_data = {"raw_body": body.decode("utf-8", errors="ignore")}
            except Exception:
                body_data = None
        else:
            # For POST/PUT/PATCH, just log that body was present but don't consume it
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > 0:
                body_data = {"body_present": True, "content_length": content_length}

        return {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "body": body_data,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
        }

    async def _get_response_data(self, response: Response) -> Dict[str, Any]:
        """Extract relevant response data for logging."""
        return {"status_code": response.status_code, "headers": dict(response.headers)}

    async def _get_current_user(self, request: Request) -> Optional[User]:
        """Extract authenticated user from request.

        Tries to extract user from JWT token in Authorization header or session cookie.

        Returns:
            User object if authenticated, None otherwise
        """
        user = None

        # Try JWT token first
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = verify_token(token)
                if payload:
                    logger.debug(
                        "Token verified, extracting user", spotify_id=payload.get("sub")
                    )
                    user = await self._get_user_by_spotify_id(request, payload["sub"])
                    if user:
                        logger.debug("User found via JWT", user_id=user.id)
                        return user
        except (ValueError, KeyError, jwt.JWTError) as e:
            logger.debug("JWT validation failed in middleware", error=str(e))
        except Exception as e:
            logger.error("Unexpected error validating JWT in middleware", error=str(e))

        # Try session cookie if JWT didn't work
        try:
            session_token = request.cookies.get("session_token")
            if session_token:
                logger.debug("Found session token, looking up session")
                user = await self._get_user_by_session_token(request, session_token)
                if user:
                    logger.debug("User found via session", user_id=user.id)
                    return user
        except Exception as e:
            logger.error(
                "Unexpected error validating session in middleware", error=str(e)
            )

        logger.debug("No user found via JWT or session")
        return None

    async def _get_user_by_spotify_id(
        self, request: Request, spotify_id: str
    ) -> Optional[User]:
        """Get user by Spotify ID from database."""
        db: Optional[AsyncSession] = getattr(request.state, "db", None)
        if not db:
            from app.core.database import async_session_factory

            async with async_session_factory() as session:
                user_repo = UserRepository(session)
                return await user_repo.get_active_user_by_spotify_id(spotify_id)
        else:
            user_repo = UserRepository(db)
            return await user_repo.get_active_user_by_spotify_id(spotify_id)

    async def _get_user_by_session_token(
        self, request: Request, session_token: str
    ) -> Optional[User]:
        """Get user by session token from database."""
        from app.repositories.session_repository import SessionRepository

        db: Optional[AsyncSession] = getattr(request.state, "db", None)
        if not db:
            from app.core.database import async_session_factory

            async with async_session_factory() as session:
                session_repo = SessionRepository(session)
                user_session = await session_repo.get_valid_session_by_token(
                    session_token
                )
                if user_session:
                    user_repo = UserRepository(session)
                    return await user_repo.get_active_user_by_id(user_session.user_id)
        else:
            session_repo = SessionRepository(db)
            user_session = await session_repo.get_valid_session_by_token(session_token)
            if user_session:
                user_repo = UserRepository(db)
                return await user_repo.get_active_user_by_id(user_session.user_id)

        return None

    async def _log_to_database(
        self,
        request: Request,
        user: Optional[User],
        status_code: int,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        error_message: Optional[str],
        processing_time_ms: int,
    ):
        """Log request/response to database."""
        try:
            # Get database session from request state if available
            db: Optional[AsyncSession] = getattr(request.state, "db", None)
            if not db:
                # Create a new session for logging
                from app.core.database import async_session_factory

                async with async_session_factory() as session:
                    await self._create_invocation_log(
                        session,
                        request,
                        user,
                        status_code,
                        request_data,
                        response_data,
                        error_message,
                        processing_time_ms,
                    )
            else:
                await self._create_invocation_log(
                    db,
                    request,
                    user,
                    status_code,
                    request_data,
                    response_data,
                    error_message,
                    processing_time_ms,
                )
        except Exception as e:
            logger.error("Failed to create invocation log", error=str(e))

    async def _create_invocation_log(
        self,
        db: AsyncSession,
        request: Request,
        user: Optional[User],
        status_code: int,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        error_message: Optional[str],
        processing_time_ms: int,
    ):
        """Create invocation log entry."""
        from app.repositories.invocation_repository import InvocationRepository

        invocation_repo = InvocationRepository(db)
        await invocation_repo.create_invocation_log(
            user_id=user.id if user else None,
            playlist_id=None,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            request_data=request_data,
            response_data=response_data,
            error_message=error_message,
            processing_time_ms=processing_time_ms,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            commit=True,
        )


class InvocationStatusMiddleware(BaseHTTPMiddleware):
    """Middleware to check invocation results and status."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check for failed invocations and handle them
        if request.url.path.startswith("/api/"):
            # You can add custom logic here to check invocation status
            # For example, check if there are recent failures for this endpoint
            pass

        response = await call_next(request)

        # Add custom headers for monitoring
        response.headers["X-Processing-Time"] = str(
            time.time() - time.time()
        )  # This would be calculated properly

        return response


class DatabaseMiddleware(BaseHTTPMiddleware):
    """Middleware to inject database session into request state."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Add database session to request state
        from app.core.database import async_session_factory

        async with async_session_factory() as db:
            request.state.db = db
            try:
                response = await call_next(request)
                await db.commit()
                return response
            except Exception:
                await db.rollback()
                raise
            finally:
                await db.close()
