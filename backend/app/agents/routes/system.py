"""System monitoring endpoints for agent workflows."""

from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, Query

from ...core.exceptions import InternalServerError
from ..core.cache import cache_manager
from ..core.id_registry import RecoBeatIDRegistry
from ..core.profiling import PerformanceProfiler
from ..tools.reccobeat_service import RecoBeatService
from ..tools.spotify_service import SpotifyService
from ..workflows.workflow_manager import WorkflowManager
from .dependencies import (
    get_agents,
    get_reccobeat_service,
    get_spotify_service,
    get_workflow_manager,
)

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/system/status")
async def get_system_status(
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
    agents: Dict[str, Any] = Depends(get_agents),
    reccobeat_service: RecoBeatService = Depends(get_reccobeat_service),
    spotify_service: SpotifyService = Depends(get_spotify_service),
):
    """Get the current status of the agentic system."""
    try:
        workflow_stats = await workflow_manager.get_performance_stats()

        agent_stats = {
            name: agent.get_performance_stats() for name, agent in agents.items()
        }

        return {
            "system_status": "operational",
            "workflow_manager": workflow_stats,
            "agents": agent_stats,
            "available_tools": {
                "reccobeat": reccobeat_service.get_available_tools(),
                "spotify": spotify_service.get_available_tools(),
            },
        }

    except Exception as exc:
        logger.error("Error getting system status", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get system status: {exc}") from exc


@router.get("/workflows/active")
async def list_active_workflows(
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """List all currently active workflows."""
    try:
        active_workflows = workflow_manager.list_active_workflows()

        return {
            "active_workflows": active_workflows,
            "total_count": len(active_workflows),
        }

    except Exception as exc:
        logger.error("Error listing active workflows", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to list active workflows: {exc}") from exc


@router.get("/workflows/recent")
async def list_recent_workflows(
    limit: int = Query(default=10, le=50),
    workflow_manager: WorkflowManager = Depends(get_workflow_manager),
):
    """List recent completed workflows."""
    try:
        recent_workflows = workflow_manager.list_recent_workflows(limit)

        return {
            "recent_workflows": recent_workflows,
            "total_count": len(recent_workflows),
        }

    except Exception as exc:
        logger.error("Error listing recent workflows", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to list recent workflows: {exc}") from exc


@router.get("/system/profiling/metrics")
async def get_profiling_metrics(
    metric_name: Optional[str] = Query(
        None, description="Specific metric name to retrieve"
    ),
):
    """Get performance profiling metrics.

    Continuous profiling endpoint for monitoring performance and detecting regressions.
    """
    try:
        if metric_name:
            # Get specific metric stats
            stats = PerformanceProfiler.get_metric_stats(metric_name)
            return {"metric": metric_name, "stats": stats}
        else:
            # Get all metrics
            all_metrics = PerformanceProfiler.list_all_metrics()
            stats_by_metric = {
                metric: PerformanceProfiler.get_metric_stats(metric)
                for metric in all_metrics
            }
            return {
                "metrics": all_metrics,
                "stats": stats_by_metric,
                "total_metrics": len(all_metrics),
            }

    except Exception as exc:
        logger.error(
            "Error retrieving profiling metrics", error=str(exc), exc_info=True
        )
        raise InternalServerError(f"Failed to get profiling metrics: {exc}") from exc


@router.get("/system/profiling/samples/{metric_name}")
async def get_profiling_samples(
    metric_name: str,
    limit: int = Query(
        default=10, le=100, description="Number of recent samples to return"
    ),
):
    """Get recent samples for a specific metric.

    Retrieve detailed profiling samples for analysis.
    """
    try:
        samples = PerformanceProfiler.get_metrics(metric_name, limit)
        return {"metric_name": metric_name, "samples": samples, "count": len(samples)}

    except Exception as exc:
        logger.error(
            "Error retrieving profiling samples", error=str(exc), exc_info=True
        )
        raise InternalServerError(f"Failed to get profiling samples: {exc}") from exc


@router.get("/system/cache/stats")
async def get_cache_stats():
    """Get comprehensive cache statistics.

    Monitor cache performance across all layers
    (in-memory, Redis, workflow artifacts, ID registry).
    """
    try:
        # Base cache stats
        base_stats = cache_manager.get_cache_stats()

        # ID registry stats
        registry_stats = await RecoBeatIDRegistry.get_registry_stats()

        return {
            "cache": base_stats,
            "id_registry": registry_stats,
        }

    except Exception as exc:
        logger.error("Error getting cache stats", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get cache stats: {exc}") from exc


@router.post("/system/cache/invalidate")
async def invalidate_cache(
    category: Optional[str] = Query(
        None, description="Cache category to invalidate (all if not specified)"
    ),
):
    """Invalidate cache entries.

    Administrative endpoint for cache management.
    """
    try:
        if category:
            # Invalidate specific category (simplified - would need more logic for targeted invalidation)
            logger.info(f"Invalidating cache category: {category}")
            result = {"invalidated_category": category}
        else:
            # Clear entire cache
            await cache_manager.cache.clear()
            logger.info("Cleared entire cache")
            result = {"invalidated": "all"}

        return {"status": "success", "result": result}

    except Exception as exc:
        logger.error("Error invalidating cache", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to invalidate cache: {exc}") from exc


@router.get("/system/id-registry/stats")
async def get_id_registry_stats():
    """Get RecoBeat ID registry statistics.

    Monitor ID validation and missing ID tracking.
    """
    try:
        stats = await RecoBeatIDRegistry.get_registry_stats()

        return {
            "id_registry": stats,
            "description": "Tracks validated and missing Spotify<->RecoBeat ID mappings",
            "ttls": {
                "missing_ids": f"{RecoBeatIDRegistry.MISSING_ID_TTL / 86400} days",
                "validated_ids": f"{RecoBeatIDRegistry.VALIDATED_ID_TTL / 86400} days",
            },
        }

    except Exception as exc:
        logger.error("Error getting ID registry stats", error=str(exc), exc_info=True)
        raise InternalServerError(f"Failed to get ID registry stats: {exc}") from exc
