"""
Utility functions for Magic Folder
"""

import os
from datetime import datetime
import logging


class Logger:
    """Thread-safe logger for Magic Folder activities"""
    
    def __init__(self, log_file_path):
        """
        Initialize the logger with a log file path
        
        Args:
            log_file_path (str): Path to the log file
        """
        self.log_file = log_file_path
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up Python's logging system"""
        # Ensure log directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('magic_folder')
    
    def log_activity(self, message):
        """
        Log activity to file and console
        
        Args:
            message (str): The message to log
        """
        try:
            self.logger.info(message)
        except Exception as e:
            # Fallback to print if logging fails
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] {message}")
            print(f"[{timestamp}] Logging error: {e}")


# Global logger instance - will be initialized by set_log_file
_logger_instance = None

def set_log_file(path):
    """
    Set up the global logger instance
    
    Args:
        path (str): Path to the log file
    """
    global _logger_instance
    _logger_instance = Logger(path)

def log_activity(message):
    """
    Log activity using the global logger instance
    
    Args:
        message (str): The message to log
    """
    global _logger_instance
    if _logger_instance:
        _logger_instance.log_activity(message)
    else:
        # Fallback if logger not initialized
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

def get_file_size_str(size_bytes):
    """
    Convert file size in bytes to a human-readable string
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Human-readable file size
    """
    if size_bytes < 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def is_temp_file(filename, excluded_extensions, excluded_files):
    """
    Check if a file is a temporary file
    
    Args:
        filename (str): Name of the file
        excluded_extensions (list): List of excluded extensions
        excluded_files (list): List of excluded filenames
        
    Returns:
        bool: True if the file is temporary, False otherwise
    """
    if not filename or not isinstance(filename, str):
        return True
        
    if filename in excluded_files:
        return True
        
    _, ext = os.path.splitext(filename)
    if ext.lower() in excluded_extensions:
        return True
        
    return False

def validate_config_values(config):
    """
    Validate configuration values and return any errors
    
    Args:
        config: Configuration object to validate
        
    Returns:
        list: List of validation error messages
    """
    errors = []
    
    # Check required directories
    if not config.base_dir:
        errors.append("Base directory is required")
    
    # Validate categories
    if not config.categories or len(config.categories) == 0:
        errors.append("At least one category is required")
    
    # Validate model settings
    if config.sample_length <= 0:
        errors.append("Sample length must be positive")
    
    # Validate processing settings
    if config.processing_delay < 0:
        errors.append("Processing delay cannot be negative")
        
    if config.check_interval <= 0:
        errors.append("Check interval must be positive")
    
    return errors