"""
JWT token handling for authentication.
"""
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict
import jwt
from flask import request, jsonify, g
from app.config import Config

logger = logging.getLogger(__name__)


def create_token(user_id: str, email: str) -> str:
    """
    Create a JWT token for a user.

    Args:
        user_id: User's UUID
        email: User's email

    Returns:
        JWT token string
    """
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=Config.JWT_EXPIRY_DAYS),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")
    return token


def decode_token(token: str) -> Optional[Dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None


def jwt_required(f):
    """
    Decorator to require JWT authentication for a route.
    Sets g.current_user with user_id and email from token.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Authorization token required"}), 401

        # Decode token
        payload = decode_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Set current user in Flask g object
        g.current_user = {
            "user_id": payload["user_id"],
            "email": payload["email"]
        }

        return f(*args, **kwargs)

    return decorated


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from the request context."""
    if hasattr(g, 'current_user'):
        return g.current_user.get("user_id")
    return None
