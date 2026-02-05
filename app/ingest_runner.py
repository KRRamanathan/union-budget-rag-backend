"""
Main ingestion runner for processing PDFs from local directory.
Orchestrates the full pipeline: scan -> load -> chunk -> embed -> store
"""
import logging
import json
from typing import Dict, List, Optional
from pathlib import Path

from app.config import Config
from app.utils.file_scanner import scan_pdf_directory, ensure_directory_exists
from app.utils.id_generator import generate_doc_id, generate_file_hash
from app.services.pdf_loader import load_pdf
from app.services.chunker import chunk_documents
from app.services.pinecone_client import add_documents, delete_by_doc_id
from app.services.embeddings import preload_model

logger = logging.getLogger(__name__)

# Track processed files for idempotency (by filename + hash)
# In production, this should be persisted to a database
_processed_files: Dict[str, str] = {}


def load_processed_files_cache(cache_path: str = ".processed_files.json"):
    """Load the processed files cache from disk."""
    global _processed_files
    cache_file = Path(cache_path)

    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                _processed_files = json.load(f)
            logger.info(f"Loaded {len(_processed_files)} processed files from cache")
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
            _processed_files = {}


def save_processed_files_cache(cache_path: str = ".processed_files.json"):
    """Save the processed files cache to disk."""
    try:
        with open(cache_path, "w") as f:
            json.dump(_processed_files, f, indent=2)
        logger.debug("Saved processed files cache")
    except Exception as e:
        logger.warning(f"Could not save cache: {e}")


def is_file_processed(filename: str, file_hash: str) -> bool:
    """
    Check if a file has already been processed.
    Uses filename + content hash for idempotency.

    Args:
        filename: Name of the PDF file
        file_hash: SHA-256 hash of file contents

    Returns:
        True if file was already processed with same hash
    """
    return _processed_files.get(filename) == file_hash


def mark_file_processed(filename: str, file_hash: str, doc_id: str):
    """Mark a file as processed in the cache."""
    _processed_files[filename] = file_hash
    save_processed_files_cache()


def ingest_single_pdf(
    pdf_path: str,
    force: bool = False
) -> Optional[Dict]:
    """
    Ingest a single PDF file into Pinecone.

    Args:
        pdf_path: Path to the PDF file
        force: If True, re-ingest even if already processed

    Returns:
        Dict with ingestion results or None if skipped
    """
    path = Path(pdf_path)
    filename = path.name

    logger.info(f"Processing PDF: {filename}")

    # Generate file hash for idempotency
    file_hash = generate_file_hash(pdf_path)

    # Check if already processed (idempotency)
    if not force and is_file_processed(filename, file_hash):
        logger.info(f"Skipping {filename} - already processed with same content")
        return None

    # Generate document ID
    doc_id = generate_doc_id(filename, file_hash)

    try:
        # If force mode, delete existing vectors first
        if force:
            try:
                delete_by_doc_id(doc_id)
                logger.info(f"Deleted existing vectors for {filename}")
            except Exception:
                pass  # Ignore if no vectors exist

        # Step 1: Load PDF
        documents = load_pdf(pdf_path)
        if not documents:
            logger.warning(f"No content extracted from {filename}")
            return {
                "status": "warning",
                "filename": filename,
                "message": "No content extracted",
                "chunks": 0
            }

        # Step 2: Chunk documents
        chunked_docs = chunk_documents(documents)

        # Step 3: Add to Pinecone (embeddings generated automatically by LangChain)
        vector_ids = add_documents(chunked_docs, doc_id, filename)

        # Mark as processed
        mark_file_processed(filename, file_hash, doc_id)

        result = {
            "status": "success",
            "filename": filename,
            "doc_id": doc_id,
            "pages": len(documents),
            "chunks": len(chunked_docs),
            "vectors_added": len(vector_ids)
        }

        logger.info(f"Successfully ingested {filename}: {len(chunked_docs)} chunks")
        return result

    except Exception as e:
        logger.error(f"Failed to ingest {filename}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "filename": filename,
            "error": str(e)
        }


def run_ingestion(
    source_dir: str = None,
    force: bool = False
) -> Dict:
    """
    Run the full ingestion pipeline on all PDFs in the source directory.

    Args:
        source_dir: Directory containing PDF files (defaults to config)
        force: If True, re-ingest all files even if already processed

    Returns:
        Dict with overall ingestion statistics
    """
    if source_dir is None:
        source_dir = Config.PDF_SOURCE_DIR

    logger.info("=" * 50)
    logger.info("Starting document ingestion pipeline")
    logger.info(f"Source directory: {source_dir}")
    logger.info("=" * 50)

    # Ensure directory exists
    ensure_directory_exists(source_dir)

    # Load processed files cache
    load_processed_files_cache()

    # Preload embedding model
    preload_model()

    # Scan for PDFs
    pdf_files = scan_pdf_directory(source_dir)

    if not pdf_files:
        logger.warning("No PDF files found in source directory")
        return {
            "status": "success",
            "message": "No PDF files found",
            "documents_ingested": 0,
            "total_chunks": 0
        }

    # Process each PDF
    results = []
    documents_ingested = 0
    total_chunks = 0
    errors = 0

    for pdf_info in pdf_files:
        result = ingest_single_pdf(pdf_info["path"], force=force)

        if result:
            results.append(result)

            if result["status"] == "success":
                documents_ingested += 1
                total_chunks += result.get("chunks", 0)
            elif result["status"] == "error":
                errors += 1

    logger.info("=" * 50)
    logger.info("Ingestion complete")
    logger.info(f"Documents ingested: {documents_ingested}")
    logger.info(f"Total chunks: {total_chunks}")
    logger.info(f"Errors: {errors}")
    logger.info("=" * 50)

    return {
        "status": "success" if errors == 0 else "partial",
        "documents_ingested": documents_ingested,
        "total_chunks": total_chunks,
        "errors": errors,
        "details": results
    }


def ingest_uploaded_file(file_path: str) -> Dict:
    """
    Ingest a single uploaded PDF file.
    Used by the Flask API endpoint.

    Args:
        file_path: Path to the uploaded PDF file

    Returns:
        Dict with ingestion result
    """
    # Preload model if not already loaded
    preload_model()

    result = ingest_single_pdf(file_path, force=True)

    if result is None:
        return {
            "status": "skipped",
            "message": "File already processed"
        }

    return result
