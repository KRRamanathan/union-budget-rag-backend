"""
Database session management using SQLAlchemy.
Connects to Neon PostgreSQL.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import Config

logger = logging.getLogger(__name__)

# Create SQLAlchemy base class for models
Base = declarative_base()

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine."""
    global _engine

    if _engine is None:
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not configured")

        logger.info("Creating database engine")
        _engine = create_engine(
            Config.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        logger.info("Database engine created")

    return _engine


def get_session_factory():
    """Get the session factory."""
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _SessionLocal


def get_db():
    """
    Get a database session.
    Use as a context manager or generator for Flask.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get a database session directly (not as generator)."""
    SessionLocal = get_session_factory()
    return SessionLocal()


def init_db():
    """Initialize database tables."""
    from app.models.user import User
    from app.models.chat_session import ChatSession
    from app.models.chat_message import ChatMessage

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
