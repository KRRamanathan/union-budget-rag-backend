"""
Text chunking service using LangChain text splitters.
Splits documents into overlapping chunks for embedding generation.
"""
import logging
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.config import Config

logger = logging.getLogger(__name__)


def get_text_splitter(chunk_size: int = None, chunk_overlap: int = None) -> RecursiveCharacterTextSplitter:
    """
    Get a configured text splitter.

    Args:
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of overlapping characters between chunks

    Returns:
        Configured RecursiveCharacterTextSplitter
    """
    if chunk_size is None:
        chunk_size = Config.CHUNK_SIZE
    if chunk_overlap is None:
        chunk_overlap = Config.CHUNK_OVERLAP

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        is_separator_regex=False
    )


def chunk_documents(
    documents: List[Document],
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Document]:
    """
    Split documents into smaller chunks.

    Args:
        documents: List of LangChain Document objects
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of overlapping characters

    Returns:
        List of chunked Document objects with preserved metadata
    """
    if not documents:
        return []

    text_splitter = get_text_splitter(chunk_size, chunk_overlap)

    logger.info(f"Chunking {len(documents)} documents with size={chunk_size or Config.CHUNK_SIZE}, overlap={chunk_overlap or Config.CHUNK_OVERLAP}")

    chunked_docs = text_splitter.split_documents(documents)

    # Add chunk index to metadata
    chunk_counts = {}
    for doc in chunked_docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", 0)
        key = f"{source}_{page}"

        if key not in chunk_counts:
            chunk_counts[key] = 0

        doc.metadata["chunk_index"] = chunk_counts[key]
        chunk_counts[key] += 1

    logger.info(f"Created {len(chunked_docs)} chunks from {len(documents)} documents")
    return chunked_docs


def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    """
    Split a single text string into chunks.

    Args:
        text: The text to chunk
        chunk_size: Maximum size of each chunk
        chunk_overlap: Number of overlapping characters

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    text_splitter = get_text_splitter(chunk_size, chunk_overlap)
    chunks = text_splitter.split_text(text)

    logger.debug(f"Split text of {len(text)} chars into {len(chunks)} chunks")
    return chunks
