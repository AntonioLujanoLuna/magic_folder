"""
File handling and processing logic
"""

import os
import time
import shutil
import threading
from datetime import datetime
from watchdog.events import FileSystemEventHandler

from magic_folder.content_extractor import ContentExtractor
from magic_folder.utils import log_activity
from magic_folder.deduplication import DeduplicationManager

class FileHandler(FileSystemEventHandler):
    """Handles file system events for the watched folder"""
    
    def __init__(self, config, analyzer):
        """
        Initialize the file handler
        
        Args:
            config (Config): The application configuration
            analyzer (AIAnalyzer): The AI analyzer instance
        """
        self.config = config
        self.analyzer = analyzer
        self.content_extractor = ContentExtractor(config)
        self.processing_queue = []
        self.processing_lock = threading.Lock()
        
        # Initialize deduplication manager if enabled
        self.dedup_manager = None
        if config.dedup_enabled:
            self.dedup_manager = DeduplicationManager(config)
            log_activity("Deduplication enabled")
        
        # Start the processing thread
        self.processing_thread = threading.Thread(target=self._process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def on_created(self, event):
        """
        Handle file creation events
        
        Args:
            event (FileSystemEvent): The file system event
        """
        if event.is_directory:
            return
            
        file_path = event.src_path
        filename = os.path.basename(file_path)
        extension = os.path.splitext(file_path)[1].lower()
        
        # Ignore excluded extensions and files
        if (extension in self.config.excluded_extensions or 
            filename in self.config.excluded_files):
            return
            
        # Add to processing queue
        with self.processing_lock:
            self.processing_queue.append(file_path)
        
        log_activity(f"New file detected: {filename}")
    
    def _process_queue(self):
        """Process files in the queue"""
        while True:
            file_to_process = None
            
            # Get a file from the queue
            with self.processing_lock:
                if self.processing_queue:
                    file_to_process = self.processing_queue.pop(0)
            
            if file_to_process:
                # Wait a moment to ensure file is fully written
                time.sleep(self.config.processing_delay)
                
                try:
                    self._process_file(file_to_process)
                except Exception as e:
                    log_activity(f"Error processing file {os.path.basename(file_to_process)}: {e}")
            
            # Sleep before checking queue again
            time.sleep(self.config.check_interval)
    
    def _process_file(self, file_path):
        """
        Process a single file
        
        Args:
            file_path (str): Path to the file to process
        """
        try:
            # Make sure file exists and is not being written to
            if not os.path.exists(file_path):
                return
                
            # Try to get exclusive access to ensure file is not being written to
            try:
                with open(file_path, 'rb') as f:
                    pass
            except PermissionError:
                # File is still being written, add it back to the queue
                with self.processing_lock:
                    self.processing_queue.append(file_path)
                return
                
            # Check for duplicates if deduplication is enabled
            if self.dedup_manager:
                is_duplicate, original_path, file_hash = self.dedup_manager.is_duplicate(file_path)
                
                if is_duplicate:
                    log_activity(f"Duplicate detected: {os.path.basename(file_path)}")
                    if self.dedup_manager.handle_duplicate(file_path, original_path):
                        return  # File was handled according to dedup policy
            
            # Extract content
            filename = os.path.basename(file_path)
            log_activity(f"Extracting content from {filename}")
            content = self.content_extractor.extract_text(file_path)
            
            # Analyze with AI
            log_activity(f"Analyzing {filename}")
            category, new_name = self.analyzer.analyze_content(content, file_path)
            
            # Ensure the category directory exists
            category_dir = os.path.join(self.config.organized_dir, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
                
            # Move and rename the file
            destination = os.path.join(category_dir, new_name)
            
            # Ensure destination filename is unique
            counter = 1
            base_name, extension = os.path.splitext(new_name)
            while os.path.exists(destination):
                new_name = f"{base_name}_{counter}{extension}"
                destination = os.path.join(category_dir, new_name)
                counter += 1
                
            shutil.move(file_path, destination)
            log_activity(f"Processed: {filename} → {category}/{new_name}")
            
            # Add file to deduplication database if enabled
            if self.dedup_manager and not is_duplicate and file_hash:
                self.dedup_manager.add_file_record(file_hash, destination, category)
            
        except Exception as e:
            log_activity(f"Error processing {os.path.basename(file_path)}: {e}")