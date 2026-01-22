"""
Test script for MarketMind AI Authentication Endpoints
Run this while the Flask server is running on localhost:5000
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_health_check():
    """Test the health check endpoint."""
    print("\n1. Testing Health Check...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_register():
    """Test user registration."""
    print("2. Testing Registration...")
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "securepassword123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 201

def test_login():
    """Test user login and get JWT token."""
    print("3. Testing Login...")
    data = {
        "email": "john@example.com",
        "password": "securepassword123"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {result}\n")
    
    if response.status_code == 200:
        return result.get("access_token")
    return None

def test_protected_route(token):
    """Test accessing protected route with JWT token."""
    print("4. Testing Protected Route (/api/auth/me)...")
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_invalid_login():
    """Test login with wrong credentials."""
    print("5. Testing Invalid Login...")
    data = {
        "email": "john@example.com",
        "password": "wrongpassword"
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 401

def test_duplicate_registration():
    """Test registering with existing email."""
    print("6. Testing Duplicate Registration...")
    data = {
        "name": "Jane Doe",
        "email": "john@example.com",  # Same email
        "password": "anotherpassword"
    }
    response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 400

def main():
    """Run all tests."""
    print("=" * 60)
    print("MarketMind AI - Authentication Test Suite")
    print("=" * 60)
    
    try:
        # Test health check
        test_health_check()
        
        # Test registration
        test_register()
        
        # Test login and get token
        token = test_login()
        
        if token:
            # Test protected route with valid token
            test_protected_route(token)
        
        # Test invalid credentials
        test_invalid_login()
        
        # Test duplicate registration
        test_duplicate_registration()
        
        print("=" * 60)
        print("✓ All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server.")
        print("Make sure Flask is running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
