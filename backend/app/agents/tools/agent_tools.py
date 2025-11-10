"""Base tool definitions for the agentic system."""

import asyncio
import hashlib
import json
import structlog
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from datetime import datetime, timezone

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..core.cache import cache_manager



logger = structlog.get_logger(__name__)


# Global semaphore for RecoBeat API to prevent concurrent requests
_reccobeat_semaphore: Optional[asyncio.Semaphore] = None

# Request deduplication: Track in-flight requests to avoid duplicate API calls
_inflight_requests: Dict[str, asyncio.Future] = {}
_inflight_lock = asyncio.Lock()


def get_reccobeat_semaphore() -> asyncio.Semaphore:
    """Get or create the global RecoBeat API semaphore.

    Optimized to 6 concurrent requests with aggressive caching and request
    deduplication reducing actual API load significantly.

    Returns:
        Semaphore limiting concurrent RecoBeat API requests
    """
    global _reccobeat_semaphore
    if _reccobeat_semaphore is None:
        # Six concurrent requests keeps burst pressure well below rate limit
        _reccobeat_semaphore = asyncio.Semaphore(6)
    return _reccobeat_semaphore


class AgentTools:
    """Collection of tools available to agents."""

    def __init__(self):
        """Initialize the registry of tools available to the agent runtime.

        Creates the internal mapping of tool names to instances and hooks in any
        baseline tools required for agent execution.
        """
        self.tools: Dict[str, BaseTool] = {}
        self._register_core_tools()

    def _register_core_tools(self):
        """Register core system tools."""
        # These will be implemented as we build the specific tools
        pass

    def register_tool(self, tool: BaseTool):
        """Register a tool.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List all available tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())

    def get_tools_for_agent(self, agent_capabilities: List[str]) -> List[BaseTool]:
        """Get tools relevant to specific agent capabilities.

        Args:
            agent_capabilities: List of capability keywords

        Returns:
            List of relevant tools
        """
        relevant_tools = []
        for tool in self.tools.values():
            # Simple keyword matching - can be enhanced
            if any(cap in tool.description.lower() for cap in agent_capabilities):
                relevant_tools.append(tool)
        return relevant_tools


class APIError(Exception):
    """Exception raised for API-related errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BaseAPITool(BaseTool, ABC):
    """Base class for API tools."""

    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra attributes beyond the BaseTool fields

    def __init__(
        self,
        name: str,
        description: str,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        **kwargs
    ):
        """Initialize the API tool.

        Args:
            name: Tool name
            description: Tool description
            base_url: Base URL for the API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        # Only pass valid BaseTool fields to parent
        super().__init__(name=name, description=description, **kwargs)
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client with optimized connection pooling for better performance
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=10.0),  # Shorter connect timeout
            limits=httpx.Limits(
                max_keepalive_connections=50,  # Increased for better connection reuse
                max_connections=200,  # Increased for higher concurrency
                keepalive_expiry=30.0  # Keep connections alive longer
            ),
            # Enable HTTP/2 for better performance
            http2=True
        )
        self._closed = False

    async def close(self):
        """Close HTTP client and cleanup resources."""
        if not self._closed and self.client:
            await self.client.aclose()
            self._closed = True

    def __del__(self):
        """Warn if client wasn't properly closed."""
        if not self._closed and self.client:
            import warnings
            warnings.warn(
                f"HTTP client for {self.__class__.__name__} was not properly closed. "
                f"Use 'async with' or call 'await close()' explicitly.",
                ResourceWarning,
                stacklevel=2
            )

    async def __aenter__(self):
        """Prepare the tool for use within an async context and return it."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources on context exit regardless of success or failure."""
        await self.close()

    def _make_cache_key(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None,
                       json_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate a cache key for API requests.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data

        Returns:
            Cache key string
        """
        # Create a consistent key from request details
        key_parts = [method.upper(), endpoint]

        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            key_parts.append(str(sorted_params))

        if json_data:
            # Sort JSON data for consistent key generation
            sorted_json = sorted(json_data.items()) if isinstance(json_data, dict) else json_data
            key_parts.append(str(sorted_json))

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached API response.

        Args:
            cache_key: Cache key

        Returns:
            Cached response data or None
        """
        try:
            cached_data = await cache_manager.cache.get(cache_key)
            if cached_data:
                logger.debug(f"Cache hit for {self.name} (key: {cache_key[:8]}...)")
                return cached_data
        except Exception as e:
            logger.warning(f"Error retrieving cached response: {e}")
        return None

    async def _cache_response(self, cache_key: str, response_data: Dict[str, Any], ttl: int = 300) -> None:
        """Cache API response.

        Args:
            cache_key: Cache key
            response_data: Response data to cache
            ttl: Time to live in seconds (default 5 minutes)
        """
        try:
            await cache_manager.cache.set(cache_key, response_data, ttl=ttl)
            logger.debug(f"Cached response for {self.name} (key: {cache_key[:8]}..., ttl: {ttl}s)")
        except Exception as e:
            logger.warning(f"Error caching response: {e}")

    @abstractmethod
    def _get_input_schema(self) -> Type[BaseModel]:
        """Define the input schema for this tool."""
        pass

    async def _execute_with_retry(self, request_func):
        """Execute a request with retry logic.

        Args:
            request_func: Async function that makes the HTTP request

        Returns:
            Response data

        Raises:
            APIError: If all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await request_func()

            except httpx.TimeoutException:
                last_exception = APIError(f"Request timeout on attempt {attempt + 1}", response_data={"error": "timeout"})
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.warning(f"Timeout when calling {self.name}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.HTTPStatusError as e:
                error_data = {"status_code": e.response.status_code, "error": str(e)}
                try:
                    error_data.update(e.response.json())
                except (ValueError, json.JSONDecodeError, AttributeError):
                    # Response body wasn't JSON or doesn't have json() method
                    pass

                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    # Retry on server errors
                    wait_time = (2 ** attempt) * 0.5
                    logger.warning(f"Server error ({e.response.status_code}) when calling {self.name}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                # Handle 429 rate limits with aggressive backoff
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    retry_after = e.response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        # Aggressive exponential backoff: 2s, 8s, 32s
                        wait_time = (2 ** (attempt + 1)) * 2.0
                    logger.warning(f"Rate limit (429) when calling {self.name}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

                last_exception = APIError(
                    f"HTTP {e.response.status_code}: {str(e)}",
                    status_code=e.response.status_code,
                    response_data=error_data
                )
                break

            except Exception as e:
                last_exception = APIError(f"Unexpected error: {str(e)}", response_data={"error": str(e)})
                break

        # All retries failed
        logger.error(f"All {self.max_retries} attempts failed for {self.name} when calling {self.name}")
        raise last_exception or APIError("Unknown error occurred")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """Make an HTTP request.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            use_cache: Whether to use caching for this request
            cache_ttl: Cache TTL in seconds (default 5 minutes)

        Returns:
            Response JSON data
        """
        # Check cache first if caching is enabled
        if use_cache:
            cache_key = self._make_cache_key(method, endpoint, params, json_data)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response is not None:
                return cached_response

        url = f"{self.base_url}{endpoint}"

        # Default headers
        request_headers = {
            "Accept": "application/json",
            "User-Agent": "MoodList-Agent/1.0"
        }
        if headers:
            request_headers.update(headers)

        if json_data:
            request_headers["Content-Type"] = "application/json"

        async def _request():
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=request_headers
            )
            response.raise_for_status()
            return response.json()

        response = await self._execute_with_retry(_request)

        # Cache the response if caching is enabled
        if use_cache:
            cache_key = self._make_cache_key(method, endpoint, params, json_data)
            await self._cache_response(cache_key, response, cache_ttl)

        return response

    def _validate_response(self, response_data: Dict[str, Any], required_fields: List[str]) -> bool:
        """Validate response contains required fields.

        Args:
            response_data: Response JSON data
            required_fields: List of required field names

        Returns:
            Whether validation passed
        """
        for field in required_fields:
            if field not in response_data:
                logger.error(f"Required field '{field}' missing from response for {self.name}")
                return False
        return True


class RateLimitedTool(BaseAPITool):
    """Base class for rate-limited API tools."""

    def __init__(
        self,
        name: str,
        description: str,
        base_url: str,
        rate_limit_per_minute: int = 60,
        min_request_interval: float = 0.0,
        use_global_semaphore: bool = False,  # NEW: Enable global request queuing
        **kwargs
    ):
        """Initialize rate-limited tool.

        Args:
            name: Tool name
            description: Tool description
            base_url: Base URL for the API
            rate_limit_per_minute: Maximum requests per minute
            min_request_interval: Minimum seconds between requests
            use_global_semaphore: Use global semaphore to limit concurrent requests
            **kwargs: Additional arguments for BaseAPITool
        """
        super().__init__(name=name, description=description, base_url=base_url, **kwargs)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.min_request_interval = min_request_interval
        self.use_global_semaphore = use_global_semaphore
        self.request_times: List[datetime] = []

        # Rate limiting state
        self._last_cleanup = datetime.now(timezone.utc)
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None

    async def _check_rate_limit(self):
        """Check if we're within rate limits."""
        now = datetime.now(timezone.utc)

        # Clean old requests (older than 1 minute)
        cutoff = now.replace(second=0, microsecond=0)
        self.request_times = [t for t in self.request_times if t > cutoff]
        self._last_cleanup = now

        if len(self.request_times) >= self.rate_limit_per_minute:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_seconds = 60 - (now - oldest_request).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"Rate limit reached for {self.name}, waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)

    async def _record_request(self):
        """Record a request for rate limiting."""
        now = datetime.now(timezone.utc)
        self.request_times.append(now)
        self._request_count += 1

    def _format_params(self, params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Format parameters for the API request.
        
        By default, converts list values to comma-separated strings.
        Override this method if the API requires different formatting.
        
        Args:
            params: Raw query parameters
            
        Returns:
            Formatted query parameters
        """
        if not params:
            return params
            
        formatted = {}
        for key, value in params.items():
            if isinstance(value, list):
                # Convert lists to comma-separated strings by default
                formatted[key] = ','.join(str(v) for v in value)
            else:
                formatted[key] = value
        return formatted

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """Make a rate-limited HTTP request."""
        # Use global semaphore if enabled (for APIs that don't handle concurrency well)
        if self.use_global_semaphore:
            semaphore = get_reccobeat_semaphore()
            async with semaphore:
                return await self._make_request_internal(method, endpoint, params, json_data, headers, use_cache, cache_ttl)
        else:
            return await self._make_request_internal(method, endpoint, params, json_data, headers, use_cache, cache_ttl)
    
    async def _make_request_internal(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300
    ) -> Dict[str, Any]:
        """Internal method to make a rate-limited HTTP request.

        Checks cache before applying rate limits to avoid unnecessary delays on cache hits.
        Implements request deduplication to avoid multiple in-flight requests for the same data.
        """
        # Check cache first to bypass rate limiting on cache hits
        if use_cache:
            cache_key = self._make_cache_key(method, endpoint, params, json_data)
            cached_response = await self._get_cached_response(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for {self.name} - bypassing rate limiter")
                return cached_response

            # Request deduplication: Check if same request is already in flight
            global _inflight_requests, _inflight_lock
            request_key = f"{self.name}:{cache_key}"
            
            created_future: Optional[asyncio.Future] = None
            async with _inflight_lock:
                if request_key in _inflight_requests:
                    logger.debug(f"Deduplicating in-flight request for {self.name}")
                    # Wait for the existing request to complete
                    try:
                        return await _inflight_requests[request_key]
                    except Exception:
                        # If the in-flight request failed, continue to make our own
                        pass
                else:
                    # Create a future for this request
                    created_future = asyncio.Future()
                    _inflight_requests[request_key] = created_future

            try:
                # Check minimum interval since last request (only for cache misses)
                if hasattr(self, '_last_request_time') and self._last_request_time and self.min_request_interval > 0:
                    elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
                    if elapsed < self.min_request_interval:
                        wait_time = self.min_request_interval - elapsed
                        logger.debug(f"Enforcing minimum interval for {self.name}, waiting {wait_time:.2f}s")
                        await asyncio.sleep(wait_time)

                await self._check_rate_limit()

                # Format parameters (convert lists to appropriate format)
                formatted_params = self._format_params(params)

                # Track request timing for monitoring
                request_start = datetime.now(timezone.utc)

                # Make the actual request (pass use_cache=False since we handled caching above)
                response = await super()._make_request(method, endpoint, formatted_params, json_data, headers, use_cache=False, cache_ttl=cache_ttl)

                # Log slow requests (>20s) for RecoBeat API monitoring
                request_duration = (datetime.now(timezone.utc) - request_start).total_seconds()
                if request_duration > 20.0:
                    logger.warning(
                        f"Slow RecoBeat API request detected",
                        tool=self.name,
                        endpoint=endpoint,
                        duration_seconds=request_duration,
                        params=formatted_params
                    )

                # Cache the response if caching was requested
                if use_cache:
                    await self._cache_response(cache_key, response, cache_ttl)

                self._last_request_time = datetime.now(timezone.utc)  # Track request time
                await self._record_request()

                # Set the result for other waiting requests
                if created_future and not created_future.done():
                    created_future.set_result(response)

                return response

            except Exception as exc:
                if created_future and not created_future.done():
                    created_future.set_exception(exc)
                raise

            finally:
                # Clean up in-flight tracking (only if we created the future)
                if created_future is not None:
                    async with _inflight_lock:
                        stored_future = _inflight_requests.get(request_key)
                        if stored_future is created_future:
                            _inflight_requests.pop(request_key, None)
        else:
            # Non-cached requests: use original flow without deduplication
            if hasattr(self, '_last_request_time') and self._last_request_time and self.min_request_interval > 0:
                elapsed = (datetime.now(timezone.utc) - self._last_request_time).total_seconds()
                if elapsed < self.min_request_interval:
                    wait_time = self.min_request_interval - elapsed
                    logger.debug(f"Enforcing minimum interval for {self.name}, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            await self._check_rate_limit()
            formatted_params = self._format_params(params)
            
            # Track request timing for monitoring
            request_start = datetime.now(timezone.utc)
            
            response = await super()._make_request(method, endpoint, formatted_params, json_data, headers, use_cache=False, cache_ttl=cache_ttl)
            
            # Log slow requests (>20s) for monitoring
            request_duration = (datetime.now(timezone.utc) - request_start).total_seconds()
            if request_duration > 20.0:
                logger.warning(
                    f"Slow API request detected",
                    tool=self.name,
                    endpoint=endpoint,
                    duration_seconds=request_duration,
                    params=formatted_params
                )
            
            self._last_request_time = datetime.now(timezone.utc)
            await self._record_request()
            return response


class ToolResult(BaseModel):
    """Standardized tool result."""

    success: bool = Field(..., description="Whether the tool execution was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @classmethod
    def success_result(cls, data: Dict[str, Any], **metadata) -> "ToolResult":
        """Create a successful result.

        Args:
            data: Result data
            **metadata: Additional metadata

        Returns:
            Success ToolResult
        """
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, **metadata) -> "ToolResult":
        """Create an error result.

        Args:
            error: Error message
            **metadata: Additional metadata

        Returns:
            Error ToolResult
        """
        return cls(success=False, error=error, metadata=metadata)
