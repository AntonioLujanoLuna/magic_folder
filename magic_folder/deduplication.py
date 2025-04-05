"""
File deduplication handling for Magic Folder
"""

import os
import hashlib
import sqlite3
from datetime import datetime
from magic_folder.utils import log_activity

class DeduplicationManager:
    """Handles detection and management of duplicate files"""
    
    def __init__(self, config):
        """
        Initialize the deduplication manager
        
        Args:
            config (Config): The application configuration
        """
        self.config = config
        self.db_path = os.path.join(config.base_dir, "file_hashes.db")
        self.hash_method = config.dedup_hash_method
        self.dedup_action = config.dedup_action
        self.duplicates_dir = os.path.join(config.base_dir, "duplicates")
        
        # Initialize database
        self._init_database()
        
        # Create duplicates directory if needed
        if self.dedup_action == 'move' and not os.path.exists(self.duplicates_dir):
            os.makedirs(self.duplicates_dir)
    
    def _init_database(self):
        """Initialize the database for storing file hashes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_hashes (
                    hash TEXT PRIMARY KEY,
                    file_path TEXT,
                    file_name TEXT,
                    category TEXT,
                    file_size INTEGER,
                    date_added TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            log_activity(f"Error initializing deduplication database: {e}")
    
    def compute_file_hash(self, file_path):
        """
        Compute hash for a file
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: Hash of the file
        """
        try:
            hasher = self._get_hash_function()
            
            # For very large files, we might want to just hash portions
            if os.path.getsize(file_path) > 100 * 1024 * 1024:  # 100MB
                return self._hash_large_file(file_path, hasher)
            
            # For regular files, hash the whole content
            with open(file_path, 'rb') as f:
                content = f.read()
                return hasher(content).hexdigest()
                
        except Exception as e:
            log_activity(f"Error computing hash for {file_path}: {e}")
            return None
    
    def _hash_large_file(self, file_path, hasher_func):
        """
        Compute hash for a large file by sampling
        
        Args:
            file_path (str): Path to the file
            hasher_func: Hash function to use
            
        Returns:
            str: Hash of the file
        """
        hasher = hasher_func()
        
        try:
            file_size = os.path.getsize(file_path)
            
            with open(file_path, 'rb') as f:
                # Read first 4MB
                hasher.update(f.read(4 * 1024 * 1024))
                
                # Read 4MB from the middle
                f.seek(file_size // 2)
                hasher.update(f.read(4 * 1024 * 1024))
                
                # Read last 4MB
                f.seek(max(0, file_size - (4 * 1024 * 1024)))
                hasher.update(f.read(4 * 1024 * 1024))
            
            return hasher.hexdigest()
            
        except Exception as e:
            log_activity(f"Error sampling large file {file_path}: {e}")
            return None
    
    def _get_hash_function(self):
        """
        Get the appropriate hash function based on configuration
        
        Returns:
            function: Hash function to use
        """
        if self.hash_method == 'sha256':
            return lambda x: hashlib.sha256(x)
        elif self.hash_method == 'sha1':
            return lambda x: hashlib.sha1(x)
        else:  # Default to md5 for speed
            return lambda x: hashlib.md5(x)
    
    def is_duplicate(self, file_path):
        """
        Check if a file is a duplicate
        
        Args:
            file_path (str): Path to the file to check
            
        Returns:
            tuple: (is_duplicate, original_path, file_hash)
        """
        file_hash = self.compute_file_hash(file_path)
        
        if not file_hash:
            return False, None, None
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT file_path FROM file_hashes WHERE hash = ?", (file_hash,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return True, result[0], file_hash
            else:
                return False, None, file_hash
                
        except Exception as e:
            log_activity(f"Error checking for duplicates: {e}")
            return False, None, file_hash
    
    def add_file_record(self, file_hash, file_path, category):
        """
        Add a file record to the database
        
        Args:
            file_hash (str): Hash of the file
            file_path (str): Path to the file
            category (str): Category of the file
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute('''
                INSERT INTO file_hashes (hash, file_path, file_name, category, file_size, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (file_hash, file_path, file_name, category, file_size, date_added))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            log_activity(f"Error adding file record to database: {e}")
    
    def handle_duplicate(self, file_path, original_path):
        """
        Handle a duplicate file according to the configured policy
        
        Args:
            file_path (str): Path to the duplicate file
            original_path (str): Path to the original file
            
        Returns:
            bool: True if the file was handled, False if it should be processed normally
        """
        # Skip the file (don't process it)
        if self.dedup_action == 'skip':
            log_activity(f"Skipping duplicate file: {os.path.basename(file_path)}")
            # Delete the file
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                log_activity(f"Error removing duplicate file: {e}")
                return True
        
        # Move the file to duplicates directory
        elif self.dedup_action == 'move':
            try:
                filename = os.path.basename(file_path)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_name = f"duplicate_{timestamp}_{filename}"
                destination = os.path.join(self.duplicates_dir, new_name)
                
                import shutil
                shutil.move(file_path, destination)
                
                log_activity(f"Moved duplicate file to: {destination}")
                return True
            except Exception as e:
                log_activity(f"Error moving duplicate file: {e}")
                return False
        
        # Process the file normally but add a note
        elif self.dedup_action == 'process':
            log_activity(f"Processing duplicate of {os.path.basename(original_path)}")
            return False
        
        # Any other action: process normally
        return False