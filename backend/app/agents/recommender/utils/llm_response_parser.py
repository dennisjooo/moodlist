"""LLM response parsing utilities."""

import json
import structlog
from typing import Any, Dict, Optional, Union

from langchain_core.messages import AIMessage

logger = structlog.get_logger(__name__)


class LLMResponseParser:
    """Utilities for parsing LLM responses and extracting structured data."""

    @staticmethod
    def extract_json_from_response(
        response_content: Union[str, AIMessage],
        fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract JSON from LLM response content with robust error handling.

        Args:
            response_content: Raw LLM response (string or AIMessage)
            fallback: Fallback dictionary to return if parsing fails

        Returns:
            Parsed JSON dictionary or fallback if parsing fails
        """
        try:
            # Extract content from response object if needed
            content = (
                response_content.content
                if hasattr(response_content, 'content')
                else str(response_content)
            )

            # Find JSON boundaries
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]

                # Parse JSON
                result = json.loads(json_str)
                logger.debug(f"Successfully parsed JSON from LLM response: {list(result.keys())}")
                return result
            else:
                logger.warning("No JSON object found in LLM response")
                return fallback or {}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            return fallback or {}
        except Exception as e:
            logger.error(f"Unexpected error parsing LLM response: {e}")
            return fallback or {}

    @staticmethod
    def safe_json_parse(
        json_str: str,
        fallback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Safely parse a JSON string with error handling.

        Args:
            json_str: JSON string to parse
            fallback: Fallback dictionary if parsing fails

        Returns:
            Parsed JSON dictionary or fallback
        """
        try:
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed for string: {e}")
            return fallback or {}
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON string: {e}")
            return fallback or {}

    @staticmethod
    def extract_json_array_from_response(
        response_content: Union[str, AIMessage],
        fallback: Optional[list] = None
    ) -> list:
        """Extract JSON array from LLM response content.

        Args:
            response_content: Raw LLM response (string or AIMessage)
            fallback: Fallback list to return if parsing fails

        Returns:
            Parsed JSON array or fallback if parsing fails
        """
        try:
            # Extract content from response object if needed
            content = (
                response_content.content
                if hasattr(response_content, 'content')
                else str(response_content)
            )

            # Find JSON array boundaries
            array_start = content.find('[')
            array_end = content.rfind(']') + 1

            if array_start >= 0 and array_end > array_start:
                json_str = content[array_start:array_end]

                # Parse JSON array
                result = json.loads(json_str)
                if isinstance(result, list):
                    logger.debug(f"Successfully parsed JSON array from LLM response: {len(result)} items")
                    return result
                else:
                    logger.warning("Parsed JSON is not an array")
                    return fallback or []
            else:
                logger.warning("No JSON array found in LLM response")
                return fallback or []

        except json.JSONDecodeError as e:
            logger.warning(f"JSON array parsing failed: {e}")
            return fallback or []
        except Exception as e:
            logger.error(f"Unexpected error parsing LLM response array: {e}")
            return fallback or []
