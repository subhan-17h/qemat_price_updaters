#!/usr/bin/env python3
"""
Convert serviceAccountKey.json to .env format
This helps you create the .env file from your JSON file
"""

import json
import sys

def json_to_env(json_file_path='serviceAccountKey.json'):
    """Convert Firebase JSON key to .env format"""
    
    try:
        with open(json_file_path, 'r') as f:
            config = json.load(f)
        
        # Create .env content
        env_content = f"""# Firebase Service Account Configuration
# Generated from {json_file_path}

FIREBASE_TYPE={config.get('type', 'service_account')}
FIREBASE_PROJECT_ID={config.get('project_id', '')}
FIREBASE_PRIVATE_KEY_ID={config.get('private_key_id', '')}
FIREBASE_PRIVATE_KEY="{config.get('private_key', '').replace(chr(10), '\\n')}"
FIREBASE_CLIENT_EMAIL={config.get('client_email', '')}
FIREBASE_CLIENT_ID={config.get('client_id', '')}
FIREBASE_AUTH_URI={config.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')}
FIREBASE_TOKEN_URI={config.get('token_uri', 'https://oauth2.googleapis.com/token')}
FIREBASE_AUTH_PROVIDER_X509_CERT_URL={config.get('auth_provider_x509_cert_url', 'https://www.googleapis.com/oauth2/v1/certs')}
FIREBASE_CLIENT_X509_CERT_URL={config.get('client_x509_cert_url', '')}
FIREBASE_UNIVERSE_DOMAIN={config.get('universe_domain', 'googleapis.com')}

# Firebase Collection Name
FIREBASE_COLLECTION_NAME=test_collection
"""
        
        # Write to .env file
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Successfully created .env file from serviceAccountKey.json")
        print("📝 You can now delete serviceAccountKey.json if needed")
        print("⚠️  Remember: Never commit .env file to git!")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: {json_file_path} not found")
        return False
    except json.JSONDecodeError:
        print(f"❌ Error: {json_file_path} is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else 'serviceAccountKey.json'
    json_to_env(json_file)
