"""Aggregate agent routers for FastAPI."""

from fastapi import APIRouter

from .recommendations import router as recommendations_router
from .system import router as system_router

router = APIRouter()
router.include_router(recommendations_router)
router.include_router(system_router)
