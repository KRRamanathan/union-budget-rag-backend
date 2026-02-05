"""
Flask routes for document ingestion API.
"""
import os
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

from app.config import Config
from app.ingest_runner import run_ingestion, ingest_uploaded_file
from app.services.pinecone_client import get_index_stats

logger = logging.getLogger(__name__)

ingest_bp = Blueprint('ingest', __name__)


def allowed_file(filename: str) -> bool:
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


@ingest_bp.route('/ingest', methods=['POST'])
def ingest_pdf():
    """
    Upload and ingest a PDF file.

    Accepts:
        - multipart/form-data with 'file' field containing PDF

    Returns:
        JSON with ingestion result
    """
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({
            "status": "error",
            "error": "No file provided"
        }), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({
            "status": "error",
            "error": "No file selected"
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "status": "error",
            "error": "Only PDF files are allowed"
        }), 400

    # Secure the filename and save to PDF source directory
    filename = secure_filename(file.filename)
    save_path = Path(Config.PDF_SOURCE_DIR) / filename

    # Ensure directory exists
    save_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        file.save(str(save_path))
        logger.info(f"Saved uploaded file: {save_path}")

        # Trigger ingestion
        result = ingest_uploaded_file(str(save_path))

        return jsonify(result), 200 if result["status"] == "success" else 500

    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@ingest_bp.route('/ingest/all', methods=['POST'])
def ingest_all():
    """
    Trigger ingestion of all PDFs in the source directory.

    Query params:
        - force: If 'true', re-ingest all files even if already processed

    Returns:
        JSON with overall ingestion statistics
    """
    force = request.args.get('force', 'false').lower() == 'true'

    try:
        result = run_ingestion(force=force)
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error running ingestion: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@ingest_bp.route('/stats', methods=['GET'])
def index_stats():
    """
    Get Pinecone index statistics.

    Returns:
        JSON with index stats
    """
    try:
        stats = get_index_stats()
        return jsonify({
            "status": "success",
            **stats
        }), 200

    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@ingest_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Union Budget RAG"
    }), 200
