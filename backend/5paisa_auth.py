"""
5paisa Authentication Script
Generates access token and stores it in token_store.json
"""
import os
import json
import requests
from datetime import date
from dotenv import load_dotenv


def generate_access_token():
    """
    Generate access token from 5paisa API and store it locally.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Read required credentials from environment variables
    app_key = os.getenv("APP_KEY")
    encryption_key = os.getenv("ENCRYPTION_KEY")
    user_id = os.getenv("USER_ID")
    app_source = os.getenv("APP_SOURCE")
    request_token = os.getenv("REQUEST_TOKEN")
    
    # Validate that REQUEST_TOKEN is present
    if not request_token:
        raise ValueError(
            "REQUEST_TOKEN is missing in .env file. "
            "Please add REQUEST_TOKEN to your .env file."
        )
    
    # Validate other required fields
    if not all([app_key, encryption_key, user_id]):
        raise ValueError(
            "Missing required credentials in .env file. "
            "Ensure APP_KEY, ENCRYPTION_KEY, and USER_ID are set."
        )
    
    print("📡 Requesting access token from 5paisa API...")
    
    # Prepare the API endpoint
    api_url = "https://Openapi.5paisa.com/VendorsAPI/Service1.svc/GetAccessToken"
    
    # Prepare the JSON payload with required structure
    payload = {
        "head": {
            "Key": app_key
        },
        "body": {
            "RequestToken": request_token,
            "EncryKey": encryption_key,
            "UserId": user_id
        }
    }
    
    # Send POST request to 5paisa API
    try:
        response = requests.post(api_url, json=payload, timeout=30)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to connect to 5paisa API: {str(e)}")
    
    # Check if the request was successful
    if response.status_code != 200:
        raise Exception(
            f"API request failed with status code {response.status_code}. "
            f"Response: {response.text}"
        )
    
    # Parse the JSON response
    try:
        response_data = response.json()
    except json.JSONDecodeError:
        raise Exception(f"Invalid JSON response from API: {response.text}")
    
    # Extract access token and client code from response
    try:
        access_token = response_data["body"]["AccessToken"]
        client_code = response_data["body"]["ClientCode"]
    except KeyError as e:
        raise Exception(
            f"Missing expected field in API response: {str(e)}. "
            f"Response: {response_data}"
        )
    
    # Prepare token data with today's date
    token_data = {
        "access_token": access_token,
        "client_code": client_code,
        "token_date": str(date.today())  # Format: YYYY-MM-DD
    }
    
    # Save token data to token_store.json
    token_file = "token_store.json"
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"✅ Access token generated successfully!")
    print(f"📁 Token stored in: {token_file}")
    print(f"👤 Client Code: {client_code}")
    print(f"📅 Token Date: {token_data['token_date']}")


if __name__ == "__main__":
    try:
        generate_access_token()
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        exit(1)
