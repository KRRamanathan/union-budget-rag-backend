"""
PDF text extraction service using LangChain document loaders.
Extracts text page-by-page from PDF documents.
"""
import logging
from typing import List
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def load_pdf(pdf_path: str) -> List[Document]:
    """
    Load a PDF file and extract text as LangChain Documents.
    Each page becomes a separate Document with page metadata.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        List of LangChain Document objects

    Raises:
        Exception: If PDF cannot be opened or processed
    """
    try:
        logger.info(f"Loading PDF: {pdf_path}")
        loader = PyMuPDFLoader(pdf_path)
        documents = loader.load()

        # Filter out empty documents
        non_empty_docs = [
            doc for doc in documents
            if doc.page_content and doc.page_content.strip()
        ]

        logger.info(f"Loaded {len(non_empty_docs)} non-empty pages from PDF")
        return non_empty_docs

    except Exception as e:
        logger.error(f"Error loading PDF {pdf_path}: {str(e)}")
        raise


def load_multiple_pdfs(pdf_paths: List[str]) -> List[Document]:
    """
    Load multiple PDF files.

    Args:
        pdf_paths: List of paths to PDF files

    Returns:
        List of all Documents from all PDFs
    """
    all_documents = []

    for path in pdf_paths:
        try:
            docs = load_pdf(path)
            # Add source filename to metadata
            for doc in docs:
                doc.metadata["source_file"] = path
            all_documents.extend(docs)
        except Exception as e:
            logger.error(f"Skipping {path} due to error: {str(e)}")
            continue

    return all_documents
