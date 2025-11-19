"""Root application routes."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
