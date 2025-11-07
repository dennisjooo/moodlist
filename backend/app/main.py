"""Main application entry point."""
from app.core.app_factory import create_application
from app.routes import router as root_router

# Create the FastAPI application instance
app = create_application()

# Include root routes
app.include_router(root_router)