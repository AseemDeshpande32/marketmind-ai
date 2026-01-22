"""
Debug auth flow
"""
from app import create_app, db
from models import User
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, decode_token

app = create_app()

with app.app_context():
    # Clear existing test user
    test_user = User.query.filter_by(email="debug@test.com").first()
    if test_user:
        db.session.delete(test_user)
        db.session.commit()
        print("✅ Deleted existing test user")
    
    # Create test user
    hashed_pw = generate_password_hash("test123")
    user = User(username="Debug User", email="debug@test.com", password_hash=hashed_pw)
    db.session.add(user)
    db.session.commit()
    print(f"✅ Created test user: ID={user.id}, Email={user.email}")
    
    # Generate token
    token = create_access_token(identity=user.id)
    print(f"✅ Generated token: {token[:50]}...")
    
    # Try to decode token
    try:
        decoded = decode_token(token)
        print(f"✅ Token decoded successfully: {decoded}")
    except Exception as e:
        print(f"❌ Token decode error: {str(e)}")
    
    # Verify password
    if check_password_hash(user.password_hash, "test123"):
        print("✅ Password verification works")
    else:
        print("❌ Password verification failed")
    
    print("\n📝 Use these credentials in Postman:")
    print("Email: debug@test.com")
    print("Password: test123")
    print(f"Token: {token}")
