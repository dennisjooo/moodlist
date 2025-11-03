#!/usr/bin/env python3
"""
Database initialization script for MoodList API.
This script creates all necessary database tables.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import engine, Base  # noqa: E402
import structlog  # noqa: E402

logger = structlog.get_logger(__name__)


async def init_database():
    """Initialize database by creating all tables."""
    try:
        logger.info("Creating database tables...")
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully!")
        
        # Print table information
        logger.info("Created tables:")
        for table_name in Base.metadata.tables.keys():
            logger.info(f"  - {table_name}")
        
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise


async def drop_tables():
    """Drop all tables (use with caution)."""
    try:
        logger.info("Dropping all database tables...")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("All tables dropped successfully!")
        
    except Exception as e:
        logger.error("Failed to drop database tables", error=str(e))
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "--drop", 
        action="store_true", 
        help="Drop all tables before creating them"
    )
    
    args = parser.parse_args()
    
    # Configure structlog for console output
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    async def main():
        if args.drop:
            await drop_tables()
        
        await init_database()
    
    asyncio.run(main())
