#!/usr/bin/env python3
"""
Run the Union Budget RAG Flask API server.

Usage:
    python run.py
"""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.app import app
from app.config import Config

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  Union Budget RAG - RAG API Server")
    print("=" * 60)
    print(f"  Pinecone Index: {Config.PINECONE_INDEX_NAME}")
    print(f"  LLM Model:      {Config.LLM_MODEL}")
    print(f"  Port:           {Config.FLASK_PORT}")
    print("=" * 60 + "\n")

    app.run(
        host='0.0.0.0',
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
