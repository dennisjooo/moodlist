"""Spotify user profile tools for the agentic system."""

import structlog
from typing import Any, Dict, List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from ..agent_tools import RateLimitedTool, ToolResult


logger = structlog.get_logger(__name__)


class GetUserProfileInput(BaseModel):
    """Input schema for getting user profile."""

    access_token: str = Field(..., description="Spotify access token")


class GetUserProfileTool(RateLimitedTool):
    """Tool for getting user profile from Spotify API."""

    name: str = "get_user_profile"
    description: str = """
    Get user's Spotify profile information.
    Use this to get user details and preferences for personalized recommendations.
    """

    def __init__(self):
        """Initialize the user profile tool."""
        super().__init__(
            name="get_user_profile",
            description="Get user profile from Spotify API",
            base_url="https://api.spotify.com/v1",
            rate_limit_per_minute=60
        )

    def _get_input_schema(self) -> Type[BaseModel]:
        """Get the input schema for this tool."""
        return GetUserProfileInput

    async def _run(self, access_token: str) -> ToolResult:
        """Get user profile from Spotify.

        Args:
            access_token: Spotify access token

        Returns:
            ToolResult with user profile or error
        """
        try:
            logger.info("Getting user profile from Spotify")

            # Make API request
            response_data = await self._make_request(
                method="GET",
                endpoint="/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            # Validate response structure
            required_fields = ["id", "display_name"]
            if not self._validate_response(response_data, required_fields):
                return ToolResult.error_result(
                    "Invalid response structure from Spotify API",
                    api_response=response_data
                )

            # Parse user profile
            user_profile = {
                "id": response_data.get("id"),
                "display_name": response_data.get("display_name"),
                "email": response_data.get("email"),
                "spotify_uri": response_data.get("uri"),
                "profile_image_url": None,
                "country": response_data.get("country"),
                "followers": response_data.get("followers", {}).get("total", 0),
                "product": response_data.get("product")  # Premium, Free, etc.
            }

            # Get profile image if available
            images = response_data.get("images", [])
            if images:
                user_profile["profile_image_url"] = images[0].get("url")

            logger.info(f"Successfully retrieved profile for user {user_profile['id']}")

            return ToolResult.success_result(
                data=user_profile,
                metadata={
                    "source": "spotify",
                    "api_endpoint": "/me"
                }
            )

        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}", exc_info=True)
            return ToolResult.error_result(
                f"Failed to get user profile: {str(e)}",
                error_type=type(e).__name__
            )