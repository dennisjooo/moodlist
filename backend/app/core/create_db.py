#!/usr/bin/env python3
"""
Database creation script for MoodList API.
This script creates the database on RDS if it doesn't exist.
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings  # noqa: E402
import structlog  # noqa: E402

logger = structlog.get_logger(__name__)


async def create_database():
    """Create the database if it doesn't exist."""
    try:
        # Parse connection string to get database name and construct postgres db connection string
        import urllib.parse

        parsed = urllib.parse.urlparse(settings.POSTGRES_CONN_STRING)
        db_name = parsed.path.lstrip("/")

        # Build connection string to 'postgres' database
        postgres_conn_string = f"{parsed.scheme}://{parsed.netloc}/postgres"
        if parsed.query:
            postgres_conn_string += f"?{parsed.query}"

        logger.info("Connecting to PostgreSQL instance")

        # Connect to the default 'postgres' database first
        conn = await asyncpg.connect(postgres_conn_string)

        logger.info("Connected to PostgreSQL instance successfully")

        # Check if database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )

        if result:
            logger.info(f"Database '{db_name}' already exists!")
        else:
            # Create the database
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database '{db_name}' created successfully!")

        await conn.close()
        return True

    except Exception as e:
        logger.error("Failed to create database", error=str(e))
        return False


async def drop_database():
    """Drop the database (use with extreme caution)."""
    try:
        # Parse connection string to get database name and construct postgres db connection string
        import urllib.parse

        parsed = urllib.parse.urlparse(settings.POSTGRES_CONN_STRING)
        db_name = parsed.path.lstrip("/")

        # Build connection string to 'postgres' database
        postgres_conn_string = f"{parsed.scheme}://{parsed.netloc}/postgres"
        if parsed.query:
            postgres_conn_string += f"?{parsed.query}"

        logger.warning(f"Attempting to drop database '{db_name}'")

        # Connect to the default 'postgres' database
        conn = await asyncpg.connect(postgres_conn_string)

        # Terminate all connections to the database
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
              AND pid <> pg_backend_pid()
        """)

        # Drop the database
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        logger.info(f"Database '{db_name}' dropped successfully!")

        await conn.close()
        return True

    except Exception as e:
        logger.error("Failed to drop database", error=str(e))
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database creation script")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop the database instead of creating it (DANGEROUS!)",
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
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    async def main():
        if args.drop:
            # Ask for confirmation before dropping
            import urllib.parse

            parsed = urllib.parse.urlparse(settings.POSTGRES_CONN_STRING)
            db_name = parsed.path.lstrip("/")
            response = input(
                f"Are you sure you want to drop database '{db_name}'? This cannot be undone! (yes/no): "
            )
            if response.lower() == "yes":
                success = await drop_database()
            else:
                logger.info("Database drop cancelled")
                return
        else:
            success = await create_database()

        if not success:
            sys.exit(1)

    asyncio.run(main())
