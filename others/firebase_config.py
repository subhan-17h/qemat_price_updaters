"""
Environment-based Firebase configuration loader
Loads Firebase credentials from environment variables instead of JSON file
"""
import os
import json
from typing import Dict

def load_firebase_config_from_env() -> Dict:
    """
    Load Firebase service account configuration from environment variables
    
    Returns:
        Dict: Firebase service account credentials
    """
    # Get private key and handle escaped newlines
    private_key = os.getenv('FIREBASE_PRIVATE_KEY', '')
    # Replace literal \n with actual newlines if needed
    if '\\n' in private_key:
        private_key = private_key.replace('\\n', '\n')
    
    config = {
        "type": os.getenv('FIREBASE_TYPE', 'service_account'),
        "project_id": os.getenv('FIREBASE_PROJECT_ID'),
        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID'),
        "private_key": private_key,
        "client_email": os.getenv('FIREBASE_CLIENT_EMAIL'),
        "client_id": os.getenv('FIREBASE_CLIENT_ID'),
        "auth_uri": os.getenv('FIREBASE_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth'),
        "token_uri": os.getenv('FIREBASE_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
        "auth_provider_x509_cert_url": os.getenv('FIREBASE_AUTH_PROVIDER_X509_CERT_URL', 
                                                   'https://www.googleapis.com/oauth2/v1/certs'),
        "client_x509_cert_url": os.getenv('FIREBASE_CLIENT_X509_CERT_URL'),
        "universe_domain": os.getenv('FIREBASE_UNIVERSE_DOMAIN', 'googleapis.com')
    }
    
    # Validate required fields
    required_fields = ['project_id', 'private_key', 'client_email']
    missing_fields = [field for field in required_fields if not config.get(field)]
    
    if missing_fields:
        raise ValueError(f"Missing required Firebase configuration: {', '.join(missing_fields)}")
    
    return config

def get_firebase_collection_name() -> str:
    """Get Firebase collection name from environment"""
    return os.getenv('FIREBASE_COLLECTION_NAME', 'test_collection')
