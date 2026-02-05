"""
Vector retriever for RAG pipeline.
Retrieves relevant documents from Pinecone.
"""
import logging
from typing import List, Dict
from langchain_core.documents import Document
from app.services.pinecone_client import get_vector_store
from app.config import Config

logger = logging.getLogger(__name__)


def get_retriever(top_k: int = None):
    """
    Get a retriever from the vector store.

    Args:
        top_k: Number of documents to retrieve

    Returns:
        LangChain retriever
    """
    if top_k is None:
        top_k = Config.RAG_TOP_K

    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k}
    )

    return retriever


def retrieve_documents(query: str, top_k: int = None) -> List[Document]:
    """
    Retrieve relevant documents for a query.

    Args:
        query: Search query
        top_k: Number of documents to retrieve

    Returns:
        List of relevant documents
    """
    if top_k is None:
        top_k = Config.RAG_TOP_K

    logger.info(f"Retrieving top {top_k} documents for query")

    vector_store = get_vector_store()
    docs = vector_store.similarity_search(query, k=top_k)

    logger.info(f"Retrieved {len(docs)} documents")
    return docs


def format_sources(documents: List[Document]) -> List[Dict]:
    """
    Format document sources for response.

    Args:
        documents: List of retrieved documents

    Returns:
        List of source dictionaries
    """
    sources = []
    seen = set()

    for doc in documents:
        doc_name = doc.metadata.get("doc_name", "Unknown")
        page_number = doc.metadata.get("page_number", 0)

        # Deduplicate sources
        key = f"{doc_name}_{page_number}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "doc_name": doc_name,
                "page_number": page_number
            })

    return sources
