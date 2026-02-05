#!/usr/bin/env python3
"""
Database migration script for Union Budget RAG.
Runs SQL migrations against the configured database.

Usage:
    python migrate.py          # Run all migrations
    python migrate.py --check  # Check database connection
"""
import argparse
import sys
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_connection():
    """Check database connection."""
    from sqlalchemy import create_engine, text

    if not Config.DATABASE_URL:
        logger.error("DATABASE_URL is not configured")
        return False

    try:
        engine = create_engine(Config.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection successful!")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def run_migrations():
    """Run SQL migrations."""
    from sqlalchemy import create_engine, text

    if not Config.DATABASE_URL:
        logger.error("DATABASE_URL is not configured")
        sys.exit(1)

    migrations_file = Path(__file__).parent / "app" / "db" / "migrations.sql"

    if not migrations_file.exists():
        logger.error(f"Migrations file not found: {migrations_file}")
        sys.exit(1)

    logger.info("Reading migrations file...")
    sql = migrations_file.read_text()

    logger.info("Connecting to database...")
    engine = create_engine(Config.DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Split by semicolon and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]

            for i, statement in enumerate(statements, 1):
                if statement:
                    logger.info(f"Executing statement {i}/{len(statements)}...")
                    conn.execute(text(statement))

            conn.commit()

        logger.info("All migrations completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


def init_tables():
    """Initialize tables using SQLAlchemy models."""
    from app.db.session import init_db

    logger.info("Initializing database tables via SQLAlchemy...")

    try:
        init_db()
        logger.info("Tables initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize tables: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Database migration script')
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check database connection only'
    )
    parser.add_argument(
        '--orm',
        action='store_true',
        help='Use SQLAlchemy ORM to create tables instead of SQL migrations'
    )

    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  Union Budget RAG - Database Migration")
    print("=" * 50 + "\n")

    if args.check:
        success = check_connection()
        sys.exit(0 if success else 1)
    elif args.orm:
        if not check_connection():
            sys.exit(1)
        init_tables()
    else:
        if not check_connection():
            sys.exit(1)
        run_migrations()


if __name__ == '__main__':
    main()
