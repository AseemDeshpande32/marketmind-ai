"""
Authentication Blueprint for MarketMind AI
Handles user registration, login, and JWT token management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash

# Create authentication blueprint with /api/auth prefix
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    
    Request JSON:
        - name: str (required)
        - email: str (required)
        - password: str (required)
    
    Returns:
        - 201: User registered successfully
        - 400: Missing fields or email already exists
    """
    from app import db
    from models import User

    data = request.get_json()

    # Validate request body exists
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Extract fields
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    # Validate all required fields
    if not name or not email or not password:
        return jsonify({"error": "All fields are required (name, email, password)"}), 400

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already exists"}), 400

    # Hash the password
    hashed_password = generate_password_hash(password)

    # Create new user
    new_user = User(
        username=name,
        email=email,
        password_hash=hashed_password
    )

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to register user"}), 500

    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Authenticate user and return JWT access token.
    
    Request JSON:
        - email: str (required)
        - password: str (required)
    
    Returns:
        - 200: JWT access token
        - 400: Missing fields
        - 401: Invalid credentials
    """
    from models import User

    data = request.get_json()

    # Validate request body exists
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Extract fields
    email = data.get("email")
    password = data.get("password")

    # Validate required fields
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find user by email
    user = User.query.filter_by(email=email).first()

    # Verify user exists and password is correct
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Generate JWT access token with user ID as string
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "access_token": access_token,
        "message": "Login successful"
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user's information.
    Requires valid JWT access token in Authorization header.
    
    Returns:
        - 200: User information
        - 401: Missing or invalid token
    """
    from models import User

    # Get user ID from JWT token and convert to integer
    current_user_id = int(get_jwt_identity())

    # Fetch user from database
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "name": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }), 200


@auth_bp.route("/change-password", methods=["POST"])
@jwt_required()
def change_password():
    """
    Change user's password.
    Requires valid JWT access token in Authorization header.
    
    Request JSON:
        - current_password: str (required)
        - new_password: str (required)
    
    Returns:
        - 200: Password changed successfully
        - 400: Missing fields or invalid current password
        - 401: Missing or invalid token
    """
    from app import db
    from models import User

    data = request.get_json()

    # Validate request body exists
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Extract fields
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    # Validate required fields
    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    # Get user ID from JWT token
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Verify current password is correct
    if not check_password_hash(user.password_hash, current_password):
        return jsonify({"error": "Current password is incorrect"}), 400

    # Validate new password
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    # Hash and update password
    user.password_hash = generate_password_hash(new_password)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update password"}), 500

    return jsonify({"message": "Password changed successfully"}), 200


@auth_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_account():
    """
    Delete user's account permanently.
    Requires valid JWT access token in Authorization header.
    
    Request JSON:
        - password: str (required) - User must confirm with password
    
    Returns:
        - 200: Account deleted successfully
        - 400: Missing password or incorrect password
        - 401: Missing or invalid token
    """
    from app import db
    from models import User

    data = request.get_json()

    # Validate request body exists
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    # Extract password
    password = data.get("password")

    # Validate password is provided
    if not password:
        return jsonify({"error": "Password is required to delete account"}), 400

    # Get user ID from JWT token
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    # Verify password is correct
    if not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Incorrect password"}), 400

    # Delete user account
    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete account"}), 500

    return jsonify({"message": "Account deleted successfully"}), 200
