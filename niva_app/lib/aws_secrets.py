"""
AWS Secrets Manager utility for retrieving environment variables from AWS Secrets Manager.
"""
import json
import os
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, Any, Optional


class AWSSecretsManager:
    """
    A utility class to retrieve secrets from AWS Secrets Manager.
    """
    
    def __init__(self, secret_name: str = "prod/NIVA-AI", region_name: str = "eu-central-1"):
        """
        Initialize the AWS Secrets Manager client.
        
        Args:
            secret_name: The name of the secret in AWS Secrets Manager
            region_name: The AWS region where the secret is stored
        """
        self.secret_name = secret_name
        self.region_name = region_name
        self._client = None
        self._secrets_cache = None
        self._aws_available = None  # Cache AWS availability check
    
    def is_aws_available(self) -> bool:
        """
        Check if AWS credentials are available and the service is accessible.
        
        Returns:
            True if AWS is available, False otherwise
        """
        if self._aws_available is not None:
            return self._aws_available
            
        try:
            # Try to create a client and check credentials
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=self.region_name
            )
            # Try to list secrets to verify credentials and permissions
            client.list_secrets(MaxResults=1)
            self._aws_available = True
        except (NoCredentialsError, ClientError) as e:
            print(f"AWS Secrets Manager not available: {e}")
            self._aws_available = False
        except Exception as e:
            print(f"Unexpected error checking AWS availability: {e}")
            self._aws_available = False
            
        return self._aws_available
    
    @property
    def client(self):
        """Lazy initialization of the boto3 client."""
        if self._client is None:
            session = boto3.session.Session()
            self._client = session.client(
                service_name='secretsmanager',
                region_name=self.region_name
            )
        return self._client
    
    def get_secrets(self) -> Dict[str, Any]:
        """
        Retrieve all secrets from AWS Secrets Manager.
        
        Returns:
            Dictionary containing all secrets
            
        Raises:
            ClientError: If there's an error retrieving the secret
        """
        if self._secrets_cache is not None:
            return self._secrets_cache
            
        # Check if AWS is available before trying to retrieve secrets
        if not self.is_aws_available():
            raise ClientError(
                error_response={'Error': {'Code': 'NoCredentials', 'Message': 'AWS credentials not available'}},
                operation_name='get_secret_value'
            )
            
        try:
            get_secret_value_response = self.client.get_secret_value(
                SecretId=self.secret_name
            )
        except ClientError as e:
            # Log the error and re-raise
            print(f"Error retrieving secret {self.secret_name}: {e}")
            raise e
        
        secret_string = get_secret_value_response['SecretString']
        self._secrets_cache = json.loads(secret_string)
        return self._secrets_cache
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Get a specific secret value by key.
        
        Args:
            key: The key of the secret to retrieve
            default: Default value if key is not found
            
        Returns:
            The secret value or default if not found
        """
        try:
            secrets = self.get_secrets()
            return secrets.get(key, default)
        except Exception as e:
            print(f"Error retrieving secret key '{key}': {e}")
            return default
    
    def get_env_var(self, key: str, default: str = "") -> str:
        """
        Get an environment variable, first from AWS Secrets Manager, then from local env.
        
        Args:
            key: The environment variable key
            default: Default value if not found
            
        Returns:
            The environment variable value
        """
        # First try to get from AWS Secrets Manager (only if AWS is available)
        if self.is_aws_available():
            try:
                secret_value = self.get_secret(key)
                if secret_value is not None:
                    return str(secret_value)
            except Exception as e:
                print(f"Could not retrieve {key} from AWS Secrets Manager: {e}")
        
        # Fallback to local environment variable
        return os.getenv(key, default)


# Global instance for easy access
secrets_manager = AWSSecretsManager()


def get_secret(key: str, default: Any = None) -> Any:
    """
    Convenience function to get a secret value.
    
    Args:
        key: The key of the secret to retrieve
        default: Default value if key is not found
        
    Returns:
        The secret value or default if not found
    """
    return secrets_manager.get_secret(key, default)


def get_env_var(key: str, default: str = "") -> str:
    """
    Convenience function to get an environment variable from AWS Secrets Manager or local env.
    
    Args:
        key: The environment variable key
        default: Default value if not found
        
    Returns:
        The environment variable value
    """
    return secrets_manager.get_env_var(key, default)
