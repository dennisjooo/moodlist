"""Logging configuration for the agentic system."""

import json
import logging
import logging.config
from typing import Dict, Any
from datetime import datetime, timezone


def setup_agent_logging(
    log_level: str = "INFO",
    log_format: str = "detailed",
    enable_file_logging: bool = True,
    log_directory: str = "logs"
) -> None:
    """Set up comprehensive logging for the agentic system.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format style (simple, detailed, json)
        enable_file_logging: Whether to enable file logging
        log_directory: Directory for log files
    """
    # Base logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            },
            "json": {
                "format": "%(asctime)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "()": lambda: json_formatter()
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": log_format,
                "level": log_level,
                "stream": "ext://sys.stdout"
            }
        },
        "loggers": {
            "app.agents": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "app.agents.core": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "app.agents.tools": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "app.agents.agents": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console"]
        }
    }

    # Add file logging if enabled
    if enable_file_logging:
        import os
        os.makedirs(log_directory, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        file_handler = {
            "class": "logging.FileHandler",
            "formatter": log_format,
            "level": log_level,
            "filename": f"{log_directory}/agentic_system_{timestamp}.log",
            "encoding": "utf-8"
        }
        config["handlers"]["file"] = file_handler

        # Add file handler to all loggers
        for logger_config in config["loggers"].values():
            logger_config["handlers"].append("file")

        config["root"]["handlers"].append("file")

    # Apply configuration
    logging.config.dictConfig(config)

    # Set specific levels for noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Agentic system logging configured with level: {log_level}")


def json_formatter():
    """Create a JSON formatter for structured logging."""
    try:
        from pythonjsonlogger import jsonlogger
        return jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    except ImportError:
        # Fallback to simple formatter if pythonjsonlogger not available
        return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class AgentLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds agent-specific context to log records."""

    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        """Initialize the logger adapter.

        Args:
            logger: Base logger instance
            extra: Additional context to add to all log records
        """
        super().__init__(logger, extra or {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process log record with additional context.

        Args:
            msg: Log message
            kwargs: Log record keyword arguments

        Returns:
            Processed message and kwargs
        """
        # Add timestamp if not present
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        kwargs["extra"].update(self.extra)
        kwargs["extra"]["agent_timestamp"] = datetime.now(timezone.utc).isoformat()

        return msg, kwargs


def get_agent_logger(name: str, **context) -> AgentLoggerAdapter:
    """Get a logger adapter for an agent with context.

    Args:
        name: Logger name
        **context: Additional context to include

    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(f"app.agents.{name}")
    return AgentLoggerAdapter(logger, context)


class PerformanceLogger:
    """Logger for tracking agent performance metrics."""

    def __init__(self, logger_name: str = "performance"):
        """Initialize performance logger.

        Args:
            logger_name: Name for the performance logger
        """
        self.logger = logging.getLogger(f"app.agents.performance.{logger_name}")
        self.metrics = {}

    def log_agent_execution(
        self,
        agent_name: str,
        execution_time: float,
        success: bool,
        **metadata
    ):
        """Log agent execution metrics.

        Args:
            agent_name: Name of the agent
            execution_time: Execution time in seconds
            success: Whether execution was successful
            **metadata: Additional metadata
        """
        self.logger.info(
            f"Agent execution: {agent_name}",
            extra={
                "agent_name": agent_name,
                "execution_time": execution_time,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
        )

    def log_workflow_step(
        self,
        session_id: str,
        step: str,
        duration: float,
        **metadata
    ):
        """Log workflow step metrics.

        Args:
            session_id: Workflow session ID
            step: Current workflow step
            duration: Step duration in seconds
            **metadata: Additional metadata
        """
        self.logger.info(
            f"Workflow step: {step}",
            extra={
                "session_id": session_id,
                "workflow_step": step,
                "step_duration": duration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
        )

    def log_api_call(
        self,
        api_name: str,
        endpoint: str,
        duration: float,
        success: bool,
        **metadata
    ):
        """Log API call metrics.

        Args:
            api_name: Name of the API (spotify, reccobeat)
            endpoint: API endpoint called
            duration: Call duration in seconds
            success: Whether call was successful
            **metadata: Additional metadata
        """
        self.logger.info(
            f"API call: {api_name}.{endpoint}",
            extra={
                "api_name": api_name,
                "endpoint": endpoint,
                "call_duration": duration,
                "success": success,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **metadata
            }
        )


# Global performance logger
performance_logger = PerformanceLogger()