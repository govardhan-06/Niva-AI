import os
import boto3
import uuid
import logging
from botocore.exceptions import ClientError
from django.conf import settings
from app.config import AWS_BUCKET_NAME

logger = logging.getLogger(__name__)

class S3StorageService:
    """
    A service for managing AWS S3 file storage operations.
    """
    
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or AWS_BUCKET_NAME
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self._verify_bucket()
    
    def _verify_bucket(self):
        """Verify that the S3 bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"S3 bucket verified: {self.bucket_name}")
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                logger.error(f"S3 bucket not found: {self.bucket_name}")
                raise ValueError(f"S3 bucket '{self.bucket_name}' does not exist")
            else:
                logger.error(f"Error accessing S3 bucket: {e}")
                raise
    
    def save_file(self, file, subdirectory='', filename=None, content_type=None):
        """
        Upload a file to S3
        
        Args:
            file: File object (Django UploadedFile or similar)
            subdirectory: Subdirectory within bucket
            filename: Custom filename (optional)
            content_type: MIME content type (optional)
            
        Returns:
            str: S3 key (path) of the uploaded file
        """
        try:
            # Use provided filename or original filename
            if filename is None:
                filename = file.name
            
            # Create S3 key (path)
            if subdirectory:
                s3_key = f"{subdirectory}/{filename}"
            else:
                s3_key = filename
            
            # Determine content type
            if content_type is None:
                content_type = file.content_type if hasattr(file, 'content_type') else 'application/octet-stream'
            
            # Upload file to S3
            extra_args = {
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256'
            }
            
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded to S3: s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            raise ValueError(f"Failed to upload file to S3: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise
    
    def get_file_url(self, s3_key, expiration=3600):
        """
        Generate a presigned URL for accessing a file
        
        Args:
            s3_key: S3 key (path) of the file
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL for the file
        """
        try:
            response = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return response
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise ValueError(f"Failed to generate file URL: {str(e)}")
    
    def file_exists(self, s3_key):
        """
        Check if a file exists in S3
        
        Args:
            s3_key: S3 key (path) of the file
            
        Returns:
            bool: True if file exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking file existence: {e}")
                raise
    
    def delete_file(self, s3_key):
        """
        Delete a file from S3
        
        Args:
            s3_key: S3 key (path) of the file
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"File deleted from S3: s3://{self.bucket_name}/{s3_key}")
            
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            raise ValueError(f"Failed to delete file from S3: {str(e)}")
    
    def get_file_info(self, s3_key):
        """
        Get information about a file in S3
        
        Args:
            s3_key: S3 key (path) of the file
            
        Returns:
            dict: File information or None if file doesn't exist
        """
        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            
            return {
                'name': os.path.basename(s3_key),
                'key': s3_key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', ''),
                'last_modified': response['LastModified'],
                'etag': response['ETag'].strip('"')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return None
            else:
                logger.error(f"Error getting file info: {e}")
                raise
    
    def list_files(self, prefix=''):
        """
        List files in S3 with optional prefix
        
        Args:
            prefix: Prefix to filter files (optional)
            
        Returns:
            list: List of file keys
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append(obj['Key'])
            
            return files
            
        except ClientError as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def copy_file(self, source_key, destination_key):
        """
        Copy a file within S3
        
        Args:
            source_key: Source S3 key
            destination_key: Destination S3 key
        """
        try:
            copy_source = {'Bucket': self.bucket_name, 'Key': source_key}
            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key,
                ServerSideEncryption='AES256'
            )
            logger.info(f"File copied in S3: {source_key} -> {destination_key}")
            
        except ClientError as e:
            logger.error(f"Error copying file in S3: {e}")
            raise ValueError(f"Failed to copy file in S3: {str(e)}")
    
    def download_file(self, s3_key, local_path):
        """
        Download a file from S3 to local storage
        
        Args:
            s3_key: S3 key (path) of the file
            local_path: Local path to save the file
        """
        try:
            # Ensure local directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"File downloaded from S3: {s3_key} -> {local_path}")
            
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            raise ValueError(f"Failed to download file from S3: {str(e)}")
    
    def get_storage_stats(self, prefix=''):
        """
        Get storage statistics for files with optional prefix
        
        Args:
            prefix: Prefix to filter files (optional)
            
        Returns:
            dict: Storage statistics
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            total_size = 0
            file_count = 0
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'bucket_name': self.bucket_name,
                'prefix': prefix
            }
            
        except ClientError as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'bucket_name': self.bucket_name,
                'prefix': prefix,
                'error': str(e)
            }