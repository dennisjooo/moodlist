"""Base tool definitions for the agentic system."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..states.agent_state import AgentState


logger = logging.getLogger(__name__)


class AgentTools:
    """Collection of tools available to agents."""

    def __init__(self):
        """Initialize the tool collection."""
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

        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

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

            except httpx.TimeoutException as e:
                last_exception = APIError(f"Request timeout on attempt {attempt + 1}", response_data={"error": "timeout"})
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.warning(f"Timeout, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.HTTPStatusError as e:
                error_data = {"status_code": e.response.status_code, "error": str(e)}
                try:
                    error_data.update(e.response.json())
                except:
                    pass

                if e.response.status_code >= 500 and attempt < self.max_retries - 1:
                    # Retry on server errors
                    wait_time = (2 ** attempt) * 0.5
                    logger.warning(f"Server error ({e.response.status_code}), retrying in {wait_time}s...")
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
        logger.error(f"All {self.max_retries} attempts failed for {self.name}")
        raise last_exception or APIError("Unknown error occurred")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request.

        Args:
            method: HTTP method
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers

        Returns:
            Response JSON data
        """
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

        return await self._execute_with_retry(_request)

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
                logger.error(f"Required field '{field}' missing from response")
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
        **kwargs
    ):
        """Initialize rate-limited tool.

        Args:
            name: Tool name
            description: Tool description
            base_url: Base URL for the API
            rate_limit_per_minute: Maximum requests per minute
            **kwargs: Additional arguments for BaseAPITool
        """
        super().__init__(name=name, description=description, base_url=base_url, **kwargs)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.request_times: List[datetime] = []

        # Rate limiting state
        self._last_cleanup = datetime.utcnow()
        self._request_count = 0

    async def _check_rate_limit(self):
        """Check if we're within rate limits."""
        now = datetime.utcnow()

        # Clean old requests (older than 1 minute)
        cutoff = now.replace(second=0, microsecond=0)
        self.request_times = [t for t in self.request_times if t > cutoff]
        self._last_cleanup = now

        if len(self.request_times) >= self.rate_limit_per_minute:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_seconds = 60 - (now - oldest_request).total_seconds()
            if wait_seconds > 0:
                logger.warning(f"Rate limit reached, waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)

    async def _record_request(self):
        """Record a request for rate limiting."""
        now = datetime.utcnow()
        self.request_times.append(now)
        self._request_count += 1

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make a rate-limited HTTP request."""
        await self._check_rate_limit()

        response = await super()._make_request(method, endpoint, params, json_data, headers)

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