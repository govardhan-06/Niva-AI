import json
import logging
import os
from base64 import b64decode
from google.auth import default
from google.cloud import storage
from google.oauth2 import service_account
from pathlib import Path

logger = logging.getLogger(__name__)

from app.config import GCP_SA_KEY

logger = logging.getLogger(__name__)

class StorageService:
    """
    A service for managing Google Cloud Storage operations.
    """
    _client_cache = None
    _credentials_cache = None
    
    @staticmethod
    def get_client():
        """
        Get or create a Google Cloud Storage client with proper credential handling
        """
        # Return cached client if available
        if StorageService._client_cache is not None:
            return StorageService._client_cache
        
        logger.info(f"Creating GCS client with GCP_SA_KEY: {GCP_SA_KEY}")
        
        try:
            credentials = StorageService._get_credentials()
            StorageService._client_cache = storage.Client(credentials=credentials)
            logger.info("Successfully created and cached storage client")
            return StorageService._client_cache
            
        except Exception as e:
            logger.error(f"Failed to create storage client: {e}")
            raise RuntimeError(f"Unable to initialize Google Cloud Storage client: {e}")
    
    @staticmethod
    def _get_credentials():
        """
        Get Google Cloud credentials using the formatted service account key
        """
        if StorageService._credentials_cache is not None:
            return StorageService._credentials_cache
        
        try:
            if GCP_SA_KEY is not None and GCP_SA_KEY.strip() != "":
                # Use the GCP Key Formatter to parse and validate the key
                logger.info("Formatting and validating GCP service account key")
                key_data = GCPKeyFormatter.get_formatted_key_data(GCP_SA_KEY)
                
                # Create credentials from the validated key data
                credentials = service_account.Credentials.from_service_account_info(key_data)
                logger.info(f"Successfully created credentials for project: {key_data.get('project_id')}")
                logger.info(f"Service account email: {key_data.get('client_email')}")
                
                StorageService._credentials_cache = credentials
                return credentials
            
            # Check for GOOGLE_APPLICATION_CREDENTIALS environment variable
            google_app_creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if google_app_creds and os.path.exists(google_app_creds):
                logger.info(f"Using GOOGLE_APPLICATION_CREDENTIALS: {google_app_creds}")
                credentials = service_account.Credentials.from_service_account_file(google_app_creds)
                StorageService._credentials_cache = credentials
                return credentials
            
            # Try default credentials as last resort
            logger.info("Attempting to use default credentials")
            credentials, project = default()
            logger.info("Using default credentials for storage client")
            StorageService._credentials_cache = credentials
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get credentials: {e}")
            raise
    
    @staticmethod
    def clear_cache():
        """Clear cached client and credentials (useful for testing or credential rotation)"""
        StorageService._client_cache = None
        StorageService._credentials_cache = None
        logger.info("Cleared storage client and credentials cache")

    @classmethod
    def delete_blob(cls, bucket_name, blob_path):
        try:
            client = cls.get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.delete()
            logger.info(f"Successfully deleted blob: {blob_path}")
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_path}: {e}")
            raise

    @classmethod
    def upload_blob(cls, bucket_name, source_file_name, destination_blob_name):
        """Upload a file to the bucket."""
        try:
            client = cls.get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            blob.upload_from_filename(source_file_name)
            logger.info(f"File {source_file_name} uploaded to {destination_blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload blob {destination_blob_name}: {e}")
            raise

    @classmethod
    def download_blob(cls, bucket_name, source_blob_name, destination_file_name):
        """Download a blob from the bucket."""
        try:
            client = cls.get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(source_blob_name)
            
            blob.download_to_filename(destination_file_name)
            logger.info(f"Blob {source_blob_name} downloaded to {destination_file_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to download blob {source_blob_name}: {e}")
            raise

    @classmethod
    def blob_exists(cls, bucket_name, blob_name):
        """Check if a blob exists in the bucket."""
        try:
            client = cls.get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check if blob {blob_name} exists: {e}")
            return False

    @classmethod
    def get_blob_info(cls, bucket_name, blob_name):
        """Get information about a blob."""
        try:
            client = cls.get_client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            if blob.exists():
                blob.reload()
                return {
                    'name': blob.name,
                    'size': blob.size,
                    'content_type': blob.content_type,
                    'updated': blob.updated,
                    'created': blob.time_created
                }
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get blob info for {blob_name}: {e}")
            return None

    @classmethod
    def test_connection(cls):
        """Test the storage connection and return diagnostic information"""
        try:
            client = cls.get_client()
            
            # Try to list buckets (this requires minimal permissions)
            try:
                buckets = list(client.list_buckets())
                bucket_count = len(buckets)
                logger.info(f"Storage connection test successful. Found {bucket_count} buckets.")
                return {
                    'success': True,
                    'bucket_count': bucket_count,
                    'message': f'Successfully connected. Found {bucket_count} buckets.'
                }
            except Exception as e:
                logger.warning(f"Could not list buckets (might be permissions): {e}")
                # Still return success if we can create a client
                return {
                    'success': True,
                    'bucket_count': 'unknown',
                    'message': 'Client created successfully, but could not list buckets (check permissions)'
                }
                
        except Exception as e:
            logger.error(f"Storage connection test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Connection failed: {e}'
            }

class GCPKeyFormatter:
    """
    Utility to format, validate, and save Google Cloud Service Account keys
    """
    
    @staticmethod
    def format_and_save_key(input_key, output_file_path="gcp_service_account.json"):
        """
        Takes a service account key in various formats and saves it as a properly formatted JSON file
        
        Args:
            input_key (str): The service account key (can be base64, JSON string, or file path)
            output_file_path (str): Where to save the formatted JSON file
            
        Returns:
            dict: The parsed service account data
        """
        try:
            # Step 1: Parse the input key
            key_data = GCPKeyFormatter._parse_input_key(input_key)
            
            # Step 2: Validate the key
            GCPKeyFormatter._validate_service_account_key(key_data)
            
            # Step 3: Save to file with proper formatting
            output_path = Path(output_file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(key_data, f, indent=2, sort_keys=True)
            
            logger.info(f"Service account key saved to: {output_path.absolute()}")
            logger.info(f"Project ID: {key_data.get('project_id')}")
            logger.info(f"Client Email: {key_data.get('client_email')}")
            
            # Set proper file permissions (readable only by owner)
            os.chmod(output_path, 0o600)
            logger.info(f"File permissions set to 600 (owner read/write only)")
            
            return key_data
            
        except Exception as e:
            logger.error(f"Error formatting service account key: {e}")
            raise
    
    @staticmethod
    def _parse_input_key(input_key):
        """Parse the input key from various formats"""
        if not input_key or not input_key.strip():
            raise ValueError("Input key is empty")
        
        key = input_key.strip()
        
        # Method 1: Check if it's a file path
        if GCPKeyFormatter._looks_like_file_path(key):
            logger.info(f"Detected file path: {key}")
            if not os.path.exists(key):
                raise FileNotFoundError(f"Service account file not found: {key}")
            
            with open(key, 'r') as f:
                return json.load(f)
        
        # Method 2: Try direct JSON
        try:
            data = json.loads(key)
            logger.info("Detected direct JSON format")
            return data
        except json.JSONDecodeError:
            pass
        
        # Method 3: Try base64 encoded JSON
        try:
            logger.info("Attempting base64 decode...")
            decoded_bytes = b64decode(key)
            decoded_str = decoded_bytes.decode('utf-8')
            data = json.loads(decoded_str)
            logger.info("Successfully decoded from base64")
            return data
        except Exception as e:
            logger.error(f"Base64 decode failed: {e}")
        
        raise ValueError("Could not parse input key. Expected JSON, base64-encoded JSON, or file path")
    
    @staticmethod
    def _looks_like_file_path(key):
        """Check if the key looks like a file path"""
        return (key.endswith('.json') or 
                '/' in key or 
                '\\' in key or 
                key.startswith('./') or 
                key.startswith('../'))
    
    @staticmethod
    def _validate_service_account_key(key_data):
        """Validate that the key data is a proper service account key"""
        if not isinstance(key_data, dict):
            raise ValueError("Service account key must be a JSON object")
        
        required_fields = [
            'type', 'project_id', 'private_key_id', 'private_key', 
            'client_email', 'client_id', 'auth_uri', 'token_uri'
        ]
        
        missing_fields = [field for field in required_fields if field not in key_data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
        
        if key_data.get('type') != 'service_account':
            raise ValueError(f"Expected type 'service_account', got '{key_data.get('type')}'")
        
        # Validate email format
        client_email = key_data.get('client_email', '')
        if '@' not in client_email or not client_email.endswith('.iam.gserviceaccount.com'):
            raise ValueError(f"Invalid client_email format: {client_email}")
        
        logger.info("Service account key validation passed")
    
    @staticmethod
    def get_formatted_key_data(input_key):
        """
        Get the service account key data without saving to file
        
        Args:
            input_key (str): The service account key input
            
        Returns:
            dict: The parsed service account data
        """
        key_data = GCPKeyFormatter._parse_input_key(input_key)
        GCPKeyFormatter._validate_service_account_key(key_data)
        return key_data