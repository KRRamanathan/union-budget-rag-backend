"""
Pinecone vector database client using LangChain.
Handles connection, index management, and vector operations.
Uses latest Pinecone SDK (v3+) - no environment parameter needed.
"""
import logging
import time
from typing import List, Dict, Optional
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec
from app.config import Config
from app.services.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# Global instances
_client: Optional[Pinecone] = None
_vector_store: Optional[PineconeVectorStore] = None


def get_pinecone_client() -> Pinecone:
    """
    Get or initialize the Pinecone client.
    Latest SDK only requires API key.

    Returns:
        Pinecone client instance
    """
    global _client

    if _client is None:
        logger.info("Initializing Pinecone client")
        _client = Pinecone(api_key=Config.PINECONE_API_KEY)
        logger.info("Pinecone client initialized")

    return _client


def get_vector_store() -> PineconeVectorStore:
    """
    Get or create the LangChain Pinecone vector store.

    Returns:
        PineconeVectorStore instance
    """
    global _vector_store

    if _vector_store is None:
        logger.info(f"Connecting to Pinecone index: {Config.PINECONE_INDEX_NAME}")

        # Ensure index exists
        ensure_index_exists()

        embeddings = get_embeddings()
        _vector_store = PineconeVectorStore(
            index_name=Config.PINECONE_INDEX_NAME,
            embedding=embeddings,
            pinecone_api_key=Config.PINECONE_API_KEY
        )
        logger.info("Connected to Pinecone vector store")

    return _vector_store


def ensure_index_exists() -> bool:
    """
    Ensure the Pinecone index exists, create if it doesn't.
    Uses serverless spec for free tier compatibility.

    Returns:
        True if index was created, False if it already existed
    """
    client = get_pinecone_client()
    index_name = Config.PINECONE_INDEX_NAME

    existing_indexes = [idx.name for idx in client.list_indexes()]

    if index_name in existing_indexes:
        logger.info(f"Index '{index_name}' already exists")
        return False

    logger.info(f"Creating index '{index_name}' with dimension {Config.EMBEDDING_DIMENSION}")

    # Create serverless index (works with free tier)
    client.create_index(
        name=index_name,
        dimension=Config.EMBEDDING_DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

    # Wait for index to be ready
    logger.info("Waiting for index to be ready...")
    while not client.describe_index(index_name).status['ready']:
        time.sleep(1)

    logger.info(f"Index '{index_name}' created successfully")
    return True


def add_documents(documents: List[Document], doc_id: str, doc_name: str) -> List[str]:
    """
    Add documents to the vector store.

    Args:
        documents: List of LangChain Document objects
        doc_id: Unique document identifier
        doc_name: Document filename

    Returns:
        List of vector IDs
    """
    if not documents:
        return []

    vector_store = get_vector_store()

    # Prepare documents with required metadata
    from datetime import datetime

    for i, doc in enumerate(documents):
        doc.metadata.update({
            "doc_id": doc_id,
            "doc_name": doc_name,
            "page_number": doc.metadata.get("page", 0) + 1,  # 1-indexed
            "chunk_index": doc.metadata.get("chunk_index", i),
            "source": "local_pdf",
            "ingested_at": datetime.utcnow().isoformat()
        })

    # Generate unique IDs for each vector
    ids = [
        f"{doc_id}_{doc.metadata['page_number']}_{doc.metadata['chunk_index']}"
        for doc in documents
    ]

    logger.info(f"Adding {len(documents)} documents to vector store")

    # Add documents in batches
    batch_size = Config.PINECONE_BATCH_SIZE
    all_ids = []

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]

        try:
            vector_store.add_documents(documents=batch_docs, ids=batch_ids)
            all_ids.extend(batch_ids)
            logger.debug(f"Added batch {i // batch_size + 1}: {len(batch_docs)} documents")
        except Exception as e:
            logger.error(f"Failed to add batch {i // batch_size + 1}: {str(e)}")
            continue

    logger.info(f"Successfully added {len(all_ids)} documents to vector store")
    return all_ids


def delete_by_doc_id(doc_id: str) -> bool:
    """
    Delete all vectors for a specific document.

    Args:
        doc_id: The document ID to delete vectors for

    Returns:
        True if successful
    """
    client = get_pinecone_client()
    index = client.Index(Config.PINECONE_INDEX_NAME)

    try:
        index.delete(filter={"doc_id": {"$eq": doc_id}})
        logger.info(f"Deleted vectors for doc_id: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete vectors for doc_id {doc_id}: {str(e)}")
        raise


def get_index_stats() -> Dict:
    """
    Get statistics about the Pinecone index.

    Returns:
        Dict with index statistics
    """
    client = get_pinecone_client()
    index = client.Index(Config.PINECONE_INDEX_NAME)
    stats = index.describe_index_stats()

    return {
        "total_vector_count": stats.total_vector_count,
        "dimension": stats.dimension,
        "namespaces": dict(stats.namespaces) if stats.namespaces else {}
    }
