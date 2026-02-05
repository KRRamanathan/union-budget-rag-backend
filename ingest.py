#!/usr/bin/env python3
"""
CLI script to ingest PDF documents into Pinecone.

Usage:
    python ingest.py              # Ingest all PDFs in the docs folder
    python ingest.py --force      # Force re-ingest all files
    python ingest.py --file path  # Ingest a specific file
"""
import argparse
import sys
import logging
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import Config
from app.ingest_runner import run_ingestion, ingest_single_pdf
from app.services.embeddings import preload_model

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Ingest PDF documents into Pinecone vector database'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-ingest all files even if already processed'
    )
    parser.add_argument(
        '--file', '-i',
        type=str,
        help='Path to a specific PDF file to ingest'
    )
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default=None,
        help=f'Directory containing PDFs (default: {Config.PDF_SOURCE_DIR})'
    )

    args = parser.parse_args()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  Union Budget RAG - PDF to Pinecone Ingestion Pipeline")
    print("=" * 60)
    print(f"  Embedding Model: {Config.EMBEDDING_MODEL_NAME}")
    print(f"  Pinecone Index:  {Config.PINECONE_INDEX_NAME}")
    print(f"  Source Dir:      {args.dir or Config.PDF_SOURCE_DIR}")
    print("=" * 60 + "\n")

    try:
        if args.file:
            # Ingest single file
            file_path = Path(args.file)
            if not file_path.exists():
                logger.error(f"File not found: {args.file}")
                sys.exit(1)

            if file_path.suffix.lower() != '.pdf':
                logger.error("File must be a PDF")
                sys.exit(1)

            preload_model()
            result = ingest_single_pdf(str(file_path), force=args.force)

            if result:
                print(f"\nResult: {result['status']}")
                if result['status'] == 'success':
                    print(f"  Chunks created: {result['chunks']}")
                    print(f"  Vectors added:  {result['vectors_added']}")
            else:
                print("\nFile was skipped (already processed)")
        else:
            # Ingest all files in directory
            source_dir = args.dir or Config.PDF_SOURCE_DIR
            result = run_ingestion(source_dir=source_dir, force=args.force)

            print(f"\nIngestion Complete!")
            print(f"  Status: {result['status']}")
            print(f"  Documents ingested: {result['documents_ingested']}")
            print(f"  Total chunks: {result['total_chunks']}")
            if result.get('errors', 0) > 0:
                print(f"  Errors: {result['errors']}")

    except KeyboardInterrupt:
        print("\n\nIngestion cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
