"""
ID generation utilities for documents and vectors.
"""
import uuid
import hashlib
from typing import Optional


def generate_doc_id(filename: str, content_hash: Optional[str] = None) -> str:
    """
    Generate a unique document ID.

    If content_hash is provided, creates a deterministic ID based on filename and content.
    Otherwise, generates a random UUID.

    Args:
        filename: Name of the document file
        content_hash: Optional hash of document content

    Returns:
        Unique document ID string
    """
    if content_hash:
        # Deterministic ID based on filename and content
        combined = f"{filename}:{content_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    else:
        # Random UUID
        return str(uuid.uuid4())


def generate_vector_id(doc_id: str, page_number: int, chunk_index: int) -> str:
    """
    Generate a unique vector ID following the format:
    {doc_id}_{page_number}_{chunk_index}

    Args:
        doc_id: Document ID
        page_number: Page number (1-indexed)
        chunk_index: Chunk index within the page (0-indexed)

    Returns:
        Unique vector ID string
    """
    return f"{doc_id}_{page_number}_{chunk_index}"


def generate_file_hash(file_path: str) -> str:
    """
    Generate a hash of a file's contents.
    Used for idempotency checking.

    Args:
        file_path: Path to the file

    Returns:
        SHA-256 hash of file contents
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()
