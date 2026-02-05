"""
Flask application for Union Budget RAG.
Phase 2: Full RAG API with authentication.
"""
import logging
import sys
from flask import Flask
from flask_cors import CORS
from app.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)

    # Configure max upload size
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # Enable CORS for frontend integration
    # Allow all origins for development and production
    # In production, you can restrict this to specific domains
    CORS(app, 
         resources={
             r"/*": {
                 "origins": "*",
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
                 "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": False,
                 "max_age": 3600
             }
         },
         supports_credentials=False)

    # Register blueprints
    from app.routes.ingest import ingest_bp
    from app.routes.auth import auth_bp
    from app.routes.chats import chats_bp

    app.register_blueprint(ingest_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chats_bp, url_prefix='/api/chats')
    
    logger.info("Flask application created with all routes registered")
    return app


# Create app instance
app = create_app()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    from flask import jsonify
    return jsonify({
        "status": "healthy",
        "service": "Union Budget RAG",
        "version": "2.0"
    }), 200


if __name__ == '__main__':
    # Validate configuration
    try:
        Config.validate()
        Config.validate_phase2()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    logger.info(f"Starting Union Budget RAG API on port {Config.FLASK_PORT}")
    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
