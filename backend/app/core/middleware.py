import time
import json
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.database import get_db
from app.models.invocation import Invocation
from app.models.user import User
from app.auth.dependencies import get_current_user_optional

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
            # Try to get user from JWT token
            user = await get_current_user_optional(
                credentials=getattr(request.state, 'credentials', None),
                db=getattr(request.state, 'db', None)
            )
        except Exception:
            pass
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_message = None
        except HTTPException as e:
            status_code = e.status_code
            error_message = e.detail
            response = JSONResponse(
                status_code=status_code,
                content={"detail": e.detail}
            )
        except Exception as e:
            status_code = 500
            error_message = str(e)
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
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
                processing_time_ms=processing_time_ms
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
            "user_agent": request.headers.get("user-agent")
        }
    
    async def _get_response_data(self, response: Response) -> Dict[str, Any]:
        """Extract relevant response data for logging."""
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
    
    async def _log_to_database(
        self,
        request: Request,
        user: Optional[User],
        status_code: int,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        error_message: Optional[str],
        processing_time_ms: int
    ):
        """Log request/response to database."""
        try:
            # Get database session from request state if available
            db: Optional[AsyncSession] = getattr(request.state, 'db', None)
            if not db:
                # Create a new session for logging
                from app.core.database import async_session_factory
                async with async_session_factory() as session:
                    await self._create_invocation_log(
                        session, request, user, status_code, 
                        request_data, response_data, error_message, processing_time_ms
                    )
            else:
                await self._create_invocation_log(
                    db, request, user, status_code,
                    request_data, response_data, error_message, processing_time_ms
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
        processing_time_ms: int
    ):
        """Create invocation log entry."""
        invocation = Invocation(
            user_id=user.id if user else None,
            endpoint=request.url.path,
            method=request.method,
            status_code=status_code,
            request_data=request_data,
            response_data=response_data,
            error_message=error_message,
            processing_time_ms=processing_time_ms,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        db.add(invocation)
        await db.commit()


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
        response.headers["X-Processing-Time"] = str(time.time() - time.time())  # This would be calculated properly
        
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