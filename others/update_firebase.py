import csv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
# Try environment variables first, fall back to JSON file
try:
    # Import the config loader
    from firebase_config import load_firebase_config_from_env, get_firebase_collection_name
    
    # Try to load from environment variables
    if os.getenv('FIREBASE_PROJECT_ID'):
        print("Loading Firebase config from environment variables...")
        firebase_config = load_firebase_config_from_env()
        cred = credentials.Certificate(firebase_config)
    else:
        print("Loading Firebase config from serviceAccountKey.json...")
        cred = credentials.Certificate('./serviceAccountKey.json')
except Exception as e:
    print(f"Loading Firebase config from serviceAccountKey.json (env failed: {e})...")
    cred = credentials.Certificate('./serviceAccountKey.json')

firebase_admin.initialize_app(cred)

# Get Firestore client
db = firestore.client()

def parse_json_field(value):
    """Parse JSON string fields from CSV"""
    if not value or value.strip() == '':
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return []

def parse_number(value):
    """Parse numeric values from CSV"""
    if not value or value.strip() == '':
        return 0
    try:
        return float(value) if '.' in value else int(value)
    except ValueError:
        return 0

def update_products_from_csv(csv_file_path, collection_name='products'):
    """
    Read CSV file and update Firebase records based on product_id
    
    Args:
        csv_file_path: Path to the CSV file
        collection_name: Name of the Firestore collection (default: 'products')
    """
    
    updated_count = 0
    error_count = 0
    
    print(f"Starting to process CSV file: {csv_file_path}")
    print(f"Target collection: {collection_name}")
    print("-" * 50)
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            
            for row_num, row in enumerate(csv_reader, start=2):  # start=2 because row 1 is header
                try:
                    product_id = row.get('product_id', '').strip()
                    
                    if not product_id:
                        print(f"Row {row_num}: Skipping - No product_id found")
                        error_count += 1
                        continue
                    
                    # Prepare the update data
                    update_data = {
                        'category': row.get('category', '').strip(),
                        'categoryNameVariations': parse_json_field(row.get('categoryNameVariations', '')),
                        'created_at': row.get('created_at', '').strip(),
                        'image_url': row.get('image_url', '').strip(),
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                        'matched_products': parse_json_field(row.get('matched_products', '')),
                        'matched_products_count': parse_number(row.get('matched_products_count', '0')),
                        'name': row.get('name', '').strip(),
                        'original_url': row.get('original_url', '').strip(),
                        'price': parse_number(row.get('price', '0')),
                        'price_history': parse_json_field(row.get('price_history', '')),
                        'product_id': product_id,
                        'store_id': row.get('store_id', '').strip()
                    }
                    
                    # Remove empty strings (optional - uncomment if you want to skip empty fields)
                    # update_data = {k: v for k, v in update_data.items() if v != ''}
                    
                    # Update the document in Firebase
                    doc_ref = db.collection(collection_name).document(product_id)
                    doc_ref.set(update_data, merge=True)
                    
                    updated_count += 1
                    print(f"Row {row_num}: Updated product_id: {product_id} - {update_data['name']}")
                    
                except Exception as e:
                    error_count += 1
                    print(f"Row {row_num}: Error updating product - {str(e)}")
                    continue
        
        print("-" * 50)
        print(f"Processing complete!")
        print(f"Successfully updated: {updated_count} records")
        print(f"Errors: {error_count}")
        
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_file_path}")
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    # Configuration
    CSV_FILE_PATH = 'consolidated.csv'  # Change this to your CSV file path
    
    # Get collection name from environment or use default
    try:
        from firebase_config import get_firebase_collection_name
        COLLECTION_NAME = get_firebase_collection_name()
    except:
        COLLECTION_NAME = os.getenv('FIREBASE_COLLECTION_NAME', 'test_collection')
    
    # Run the update
    update_products_from_csv(CSV_FILE_PATH, COLLECTION_NAME)