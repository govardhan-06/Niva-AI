import os
import shutil
import logging
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

class LocalStorageService:
    """
    A service for managing local file storage operations.
    """
    
    def __init__(self, storage_root=None):
        # Use Django's MEDIA_ROOT or a custom storage directory
        self.storage_root = storage_root or getattr(settings, 'MEDIA_ROOT', './storage')
        self.ensure_storage_directory()
    
    def ensure_storage_directory(self):
        """Ensure the storage directory exists"""
        os.makedirs(self.storage_root, exist_ok=True)
        logger.info(f"Storage directory ensured: {self.storage_root}")
    
    def save_file(self, file, subdirectory='', filename=None):
        """
        Save a file to local storage
        
        Args:
            file: File object (Django UploadedFile or similar)
            subdirectory: Subdirectory within storage root
            filename: Custom filename (optional)
            
        Returns:
            str: Relative path to the saved file
        """
        try:
            # Use provided filename or original filename
            if filename is None:
                filename = file.name
            
            # Create subdirectory path
            if subdirectory:
                directory_path = os.path.join(self.storage_root, subdirectory)
                os.makedirs(directory_path, exist_ok=True)
                file_path = os.path.join(subdirectory, filename)
                full_path = os.path.join(directory_path, filename)
            else:
                file_path = filename
                full_path = os.path.join(self.storage_root, filename)
            
            # Save the file
            with open(full_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            logger.info(f"File saved to: {full_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    def get_file_path(self, relative_path):
        """
        Get the full file path from a relative path
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            str: Full file path
        """
        return os.path.join(self.storage_root, relative_path)
    
    def file_exists(self, relative_path):
        """
        Check if a file exists
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            bool: True if file exists
        """
        full_path = self.get_file_path(relative_path)
        return os.path.exists(full_path)
    
    def delete_file(self, relative_path):
        """
        Delete a file from local storage
        
        Args:
            relative_path: Relative path from storage root
        """
        try:
            full_path = self.get_file_path(relative_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"File deleted: {full_path}")
                
                # Clean up empty directories
                directory = os.path.dirname(full_path)
                try:
                    if directory != self.storage_root and not os.listdir(directory):
                        os.rmdir(directory)
                        logger.info(f"Empty directory removed: {directory}")
                except OSError:
                    pass  # Directory not empty or other error
            else:
                logger.warning(f"File not found for deletion: {full_path}")
                
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    def get_file_info(self, relative_path):
        """
        Get information about a file
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            dict: File information or None if file doesn't exist
        """
        try:
            full_path = self.get_file_path(relative_path)
            
            if os.path.exists(full_path):
                stat = os.stat(full_path)
                return {
                    'name': os.path.basename(relative_path),
                    'path': relative_path,
                    'full_path': full_path,
                    'size': stat.st_size,
                    'created': stat.st_ctime,
                    'modified': stat.st_mtime
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return None
    
    def list_files(self, subdirectory=''):
        """
        List files in a directory
        
        Args:
            subdirectory: Subdirectory to list (optional)
            
        Returns:
            list: List of file paths relative to storage root
        """
        try:
            if subdirectory:
                search_path = os.path.join(self.storage_root, subdirectory)
            else:
                search_path = self.storage_root
            
            if not os.path.exists(search_path):
                return []
            
            files = []
            for root, dirs, filenames in os.walk(search_path):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    # Get relative path from storage root
                    relative_path = os.path.relpath(full_path, self.storage_root)
                    files.append(relative_path)
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def get_file_url(self, relative_path):
        """
        Get a URL for accessing the file (for serving files)
        
        Args:
            relative_path: Relative path from storage root
            
        Returns:
            str: URL to access the file
        """
        # This would typically be handled by your web server
        # For development, you might serve files through Django
        from django.conf import settings
        
        if hasattr(settings, 'MEDIA_URL'):
            return f"{settings.MEDIA_URL}{relative_path}"
        else:
            return f"/media/{relative_path}"
    
    def copy_file(self, source_path, destination_path):
        """
        Copy a file within the storage system
        
        Args:
            source_path: Source relative path
            destination_path: Destination relative path
        """
        try:
            source_full = self.get_file_path(source_path)
            dest_full = self.get_file_path(destination_path)
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_full), exist_ok=True)
            
            shutil.copy2(source_full, dest_full)
            logger.info(f"File copied from {source_full} to {dest_full}")
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            raise
    
    def move_file(self, source_path, destination_path):
        """
        Move a file within the storage system
        
        Args:
            source_path: Source relative path
            destination_path: Destination relative path
        """
        try:
            source_full = self.get_file_path(source_path)
            dest_full = self.get_file_path(destination_path)
            
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dest_full), exist_ok=True)
            
            shutil.move(source_full, dest_full)
            logger.info(f"File moved from {source_full} to {dest_full}")
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            raise
    
    def get_storage_stats(self):
        """
        Get storage statistics
        
        Returns:
            dict: Storage statistics
        """
        try:
            total_size = 0
            file_count = 0
            
            for root, dirs, files in os.walk(self.storage_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'storage_root': self.storage_root
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'storage_root': self.storage_root,
                'error': str(e)
            }