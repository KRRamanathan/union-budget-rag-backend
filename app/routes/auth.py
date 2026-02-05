"""
Authentication routes for user registration and login.
"""
import logging
from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError

from app.db.session import get_db_session
from app.models.user import User
from app.auth.password import hash_password, verify_password
from app.auth.jwt import create_token, jwt_required, get_current_user_id

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        {
            "name": "User Name",
            "email": "user@example.com",
            "password": "password123"
        }

    Returns:
        User data and JWT token
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # Validate required fields
    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # Hash password
    password_hash = hash_password(password)

    # Create user
    db = get_db_session()
    try:
        user = User(
            name=name,
            email=email.lower().strip(),
            password_hash=password_hash
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create JWT token
        token = create_token(str(user.id), user.email)

        logger.info(f"User registered: {user.email}")

        return jsonify({
            "message": "User registered successfully",
            "user": user.to_dict(),
            "access_token": token
        }), 201

    except IntegrityError:
        db.rollback()
        return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        db.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed"}), 500
    finally:
        db.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login a user.

    Request body:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Returns:
        JWT token
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body required"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find user
    db = get_db_session()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()

        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401

        # Create JWT token
        token = create_token(str(user.id), user.email)

        logger.info(f"User logged in: {user.email}")

        return jsonify({
            "message": "Login successful",
            "user": user.to_dict(),
            "access_token": token
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500
    finally:
        db.close()


@auth_bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    """
    Get current user info (requires JWT).
    """
    user_id = get_current_user_id()

    db = get_db_session()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": user.to_dict()}), 200
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return jsonify({"error": "Failed to get user"}), 500
    finally:
        db.close()
