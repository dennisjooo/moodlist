"""Enhanced error handling for the agentic system."""

import structlog
import traceback
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from enum import Enum

from fastapi import HTTPException


logger = structlog.get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AgentError(Exception):
    """Base exception for agent-related errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "cause": str(self.cause) if self.cause else None
        }


class WorkflowError(AgentError):
    """Error in workflow execution."""

    def __init__(self, message: str, session_id: str, **kwargs):
        super().__init__(message, "WORKFLOW_ERROR", **kwargs)
        self.session_id = session_id
        self.details["session_id"] = session_id


class AgentExecutionError(AgentError):
    """Error in agent execution."""

    def __init__(self, message: str, agent_name: str, **kwargs):
        super().__init__(message, "AGENT_EXECUTION_ERROR", **kwargs)
        self.agent_name = agent_name
        self.details["agent_name"] = agent_name


class APIError(AgentError):
    """Error in external API calls."""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, "API_ERROR", **kwargs)
        self.api_name = api_name
        self.status_code = status_code
        self.details.update({
            "api_name": api_name,
            "status_code": status_code
        })


class ConfigurationError(AgentError):
    """Error in system configuration."""

    def __init__(self, message: str, config_key: str, **kwargs):
        super().__init__(message, "CONFIGURATION_ERROR", severity=ErrorSeverity.HIGH, **kwargs)
        self.config_key = config_key
        self.details["config_key"] = config_key


class ErrorHandler:
    """Centralized error handling for the agentic system."""

    def __init__(self):
        """Initialize the error handler."""
        self.error_counts = {}
        self.last_error_cleanup = datetime.now(timezone.utc)

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle and log an error with context.

        Args:
            error: The exception that occurred
            context: Additional context information

        Returns:
            Structured error information
        """
        context = context or {}

        # Create error info
        error_info = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Determine severity
        severity = self._determine_severity(error)

        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error_info}", exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error_info}", exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error_info}")
        else:
            logger.info(f"Low severity error: {error_info}")

        # Track error counts
        self._track_error(error, context)

        return error_info

    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine the severity of an error.

        Args:
            error: The exception to analyze

        Returns:
            Error severity level
        """
        # Critical errors
        if isinstance(error, ConfigurationError):
            return ErrorSeverity.CRITICAL

        # High severity errors
        if isinstance(error, (WorkflowError, AgentExecutionError)):
            return ErrorSeverity.HIGH

        # Medium severity errors
        if isinstance(error, APIError):
            return ErrorSeverity.MEDIUM

        # Default to medium for unknown errors
        return ErrorSeverity.MEDIUM

    def _track_error(self, error: Exception, context: Dict[str, Any]):
        """Track error occurrences for monitoring.

        Args:
            error: The exception that occurred
            context: Error context
        """
        # Clean up old error counts periodically
        now = datetime.now(timezone.utc)
        if (now - self.last_error_cleanup).seconds > 3600:  # Every hour
            self.error_counts.clear()
            self.last_error_cleanup = now

        # Track error
        error_key = f"{type(error).__name__}:{context.get('agent_name', 'unknown')}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics for monitoring.

        Returns:
            Error statistics
        """
        return {
            "total_errors_tracked": sum(self.error_counts.values()),
            "error_types": dict(self.error_counts),
            "last_cleanup": self.last_error_cleanup.isoformat()
        }

    def create_http_exception(
        self,
        error: AgentError,
        status_code: int = 500
    ) -> HTTPException:
        """Create an HTTP exception from an agent error.

        Args:
            error: Agent error to convert
            status_code: HTTP status code

        Returns:
            HTTP exception
        """
        # Map error codes to appropriate HTTP status codes
        status_code_map = {
            "WORKFLOW_ERROR": 500,
            "AGENT_EXECUTION_ERROR": 500,
            "API_ERROR": 502,
            "CONFIGURATION_ERROR": 500,
            "VALIDATION_ERROR": 400
        }

        http_status = status_code_map.get(error.error_code, status_code)

        return HTTPException(
            status_code=http_status,
            detail={
                "error_code": error.error_code,
                "message": error.message,
                "severity": error.severity.value,
                "details": error.details,
                "timestamp": error.timestamp.isoformat()
            }
        )


# Global error handler instance
error_handler = ErrorHandler()


def handle_agent_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function for handling agent errors.

    Args:
        error: The exception that occurred
        context: Additional context information

    Returns:
        Structured error information
    """
    return error_handler.handle_error(error, context)


def create_agent_error(
    message: str,
    error_code: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    **kwargs
) -> AgentError:
    """Convenience function for creating agent errors.

    Args:
        message: Error message
        error_code: Error code
        severity: Error severity
        **kwargs: Additional error parameters

    Returns:
        Agent error instance
    """
    return AgentError(message, error_code, severity, **kwargs)