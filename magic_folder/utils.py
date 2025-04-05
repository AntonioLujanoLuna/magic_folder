"""
Utility functions for Magic Folder
"""

import os
from datetime import datetime

# Global log file path, will be set in Config
LOG_FILE = None

def set_log_file(path):
    """
    Set the global log file path
    
    Args:
        path (str): Path to the log file
    """
    global LOG_FILE
    LOG_FILE = path

def log_activity(message):
    """
    Log activity to file and console
    
    Args:
        message (str): The message to log
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    
    print(log_entry)
    
    global LOG_FILE
    if LOG_FILE:
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + "\n")

def get_file_size_str(size_bytes):
    """
    Convert file size in bytes to a human-readable string
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Human-readable file size
    """
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
    if filename in excluded_files:
        return True
        
    _, ext = os.path.splitext(filename)
    if ext.lower() in excluded_extensions:
        return True
        
    return False