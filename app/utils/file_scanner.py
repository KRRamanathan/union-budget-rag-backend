"""
File scanning utilities for the PDF source directory.
"""
import os
import logging
from typing import List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def scan_pdf_directory(directory: str) -> List[Dict]:
    """
    Scan a directory for PDF files.

    Args:
        directory: Path to the directory to scan

    Returns:
        List of dictionaries containing file information

    Raises:
        ValueError: If directory doesn't exist
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    pdf_files = []

    logger.info(f"Scanning directory: {directory}")

    for file_path in dir_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() == '.pdf':
            pdf_files.append({
                "path": str(file_path.absolute()),
                "filename": file_path.name,
                "size_bytes": file_path.stat().st_size
            })
            logger.debug(f"Found PDF: {file_path.name}")
        elif file_path.is_file():
            logger.debug(f"Skipping non-PDF file: {file_path.name}")

    logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
    return pdf_files


def ensure_directory_exists(directory: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Path to the directory

    Returns:
        True if directory was created, False if it already existed
    """
    dir_path = Path(directory)

    if dir_path.exists():
        return False

    dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created directory: {directory}")
    return True


def get_pdf_file_info(file_path: str) -> Dict:
    """
    Get information about a specific PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary with file information

    Raises:
        ValueError: If file doesn't exist or isn't a PDF
    """
    path = Path(file_path)

    if not path.exists():
        raise ValueError(f"File does not exist: {file_path}")

    if path.suffix.lower() != '.pdf':
        raise ValueError(f"File is not a PDF: {file_path}")

    return {
        "path": str(path.absolute()),
        "filename": path.name,
        "size_bytes": path.stat().st_size
    }
