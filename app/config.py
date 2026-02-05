"""
Configuration module for Union Budget RAG.
Loads all settings from environment variables.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Database Configuration (Neon PostgreSQL)
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "union-budget-rag")

    # LLM Configuration (Gemini)
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash-exp")

    # JWT Configuration
    JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-key")
    JWT_EXPIRY_DAYS = int(os.getenv("JWT_EXPIRY_DAYS", "7"))

    # PDF Source Configuration
    PDF_SOURCE_DIR = os.getenv("PDF_SOURCE_DIR", "./docs")

    # Embedding Model Configuration
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "embed-english-light-v3.0"  # Cohere embedding model (free tier available)
    )
    EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "384"))  # Dimension for embed-english-v3.0
    
    # Cohere API Configuration (required for embeddings - free tier available)
    COHERE_API_KEY = os.getenv("COHERE_API_KEY")

    # Chunking Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

    # RAG Configuration
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "8"))

    # Flask Configuration
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
    FLASK_PORT = int(os.getenv("FLASK_PORT", "4000"))
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

    # Pinecone batch size for upserts
    PINECONE_BATCH_SIZE = 100

    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        errors = []

        if not cls.PINECONE_API_KEY:
            errors.append("PINECONE_API_KEY is required")

        if not cls.PINECONE_INDEX_NAME:
            errors.append("PINECONE_INDEX_NAME is required")
        
        if not cls.COHERE_API_KEY:
            errors.append("COHERE_API_KEY is required for embeddings (get free key at https://cohere.com/)")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

        return True

    @classmethod
    def validate_phase2(cls):
        """Validate Phase 2 specific configuration."""
        errors = []

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")

        if not cls.GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is required")

        if not cls.JWT_SECRET or cls.JWT_SECRET == "change-this-secret-key":
            errors.append("JWT_SECRET must be set to a secure value")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

        return True
