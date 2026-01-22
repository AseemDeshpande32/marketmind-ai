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
