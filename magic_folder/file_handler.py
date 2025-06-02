"""
File handling and processing logic
"""

import os
import re
import time
import json
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
        
        # Initialize feedback mechanism if enabled
        if config.enable_feedback_system:
            self.feedback_dir = os.path.join(config.base_dir, "feedback")
            self.feedback_file = os.path.join(self.feedback_dir, "user_feedback.json")
            self.feedback_data = self._load_feedback_data()
            self._setup_feedback_watcher()
            log_activity("Feedback system enabled")
        
        # Start the processing thread
        self.processing_thread = threading.Thread(target=self._process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _setup_feedback_watcher(self):
        """Set up the feedback directory and watcher"""
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
            
        # Create directories for each category inside feedback dir for easy user correction
        for category in self.config.categories:
            category_dir = os.path.join(self.feedback_dir, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
                
        # Start a separate thread to watch for feedback
        self.feedback_thread = threading.Thread(target=self._monitor_feedback)
        self.feedback_thread.daemon = True
        self.feedback_thread.start()
    
    def _load_feedback_data(self):
        """Load feedback data from the JSON file"""
        if not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
            
        if os.path.exists(self.feedback_file):
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log_activity(f"Error loading feedback data: {e}")
                
        # Initialize empty feedback structure
        return {
            "corrections": [],
            "keywords": {}
        }
    
    def _save_feedback_data(self):
        """Save feedback data to the JSON file"""
        try:
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, indent=4)
        except Exception as e:
            log_activity(f"Error saving feedback data: {e}")
    
    def _monitor_feedback(self):
        """Monitor feedback directory for user corrections"""
        while True:
            try:
                # Check each category directory for files
                for category in self.config.categories:
                    category_dir = os.path.join(self.feedback_dir, category)
                    
                    if os.path.exists(category_dir):
                        files = [f for f in os.listdir(category_dir) if os.path.isfile(os.path.join(category_dir, f))]
                        
                        for file in files:
                            file_path = os.path.join(category_dir, file)
                            
                            # Process the feedback
                            original_path = None
                            original_category = None
                            
                            # Check if this is a corrected file (format: original_category--filename)
                            parts = file.split('--', 1)
                            if len(parts) == 2 and parts[0] in self.config.categories:
                                original_category = parts[0]
                                original_name = parts[1]
                                
                                # Record the correction
                                correction = {
                                    "filename": original_name,
                                    "original_category": original_category,
                                    "corrected_category": category,
                                    "timestamp": datetime.now().isoformat()
                                }
                                
                                self.feedback_data["corrections"].append(correction)
                                
                                # Extract content and update keywords
                                try:
                                    content = self.content_extractor.extract_text(file_path)
                                    if content:
                                        self._update_keywords(content, category)
                                except Exception as e:
                                    log_activity(f"Error extracting content for feedback: {e}")
                                
                                # Move the file to the correct organized category
                                dest_dir = os.path.join(self.config.organized_dir, category)
                                if not os.path.exists(dest_dir):
                                    os.makedirs(dest_dir)
                                    
                                # Use just the original filename without the category prefix
                                dest_path = os.path.join(dest_dir, original_name)
                                
                                # Ensure filename is unique
                                if os.path.exists(dest_path):
                                    base, ext = os.path.splitext(original_name)
                                    dest_path = os.path.join(dest_dir, f"{base}_corrected{ext}")
                                
                                try:
                                    shutil.move(file_path, dest_path)
                                    log_activity(f"Applied user correction: {original_name} moved from {original_category} to {category}")
                                    
                                    # Update the model with this feedback
                                    self._apply_feedback_to_model()
                                except Exception as e:
                                    log_activity(f"Error moving corrected file: {e}")
            except Exception as e:
                log_activity(f"Error monitoring feedback: {e}")
                
            # Save feedback data
            self._save_feedback_data()
            
            # Check every 10 seconds
            time.sleep(10)
    
    def _update_keywords(self, content, category):
        """
        Update keywords for a category based on content
        
        Args:
            content (str): The text content
            category (str): The category to update
        """
        if category not in self.feedback_data["keywords"]:
            self.feedback_data["keywords"][category] = {}
            
        # Simple word frequency analysis
        words = re.findall(r'\b[a-zA-Z]{3,15}\b', content.lower())
        
        # Update word counts
        for word in words:
            if word not in self.feedback_data["keywords"][category]:
                self.feedback_data["keywords"][category][word] = 0
            self.feedback_data["keywords"][category][word] += 1
    
    def _apply_feedback_to_model(self):
        """Apply feedback data to improve the analyzer model"""
        # Update category keywords in the analyzer based on feedback
        if self.feedback_data["keywords"]:
            # For each category with feedback
            for category, words in self.feedback_data["keywords"].items():
                if category in self.analyzer.category_keywords:
                    existing_keywords = set(self.analyzer.category_keywords[category])
                    
                    # Add top keywords that aren't already in the list
                    top_words = sorted(words.items(), key=lambda x: x[1], reverse=True)[:20]
                    for word, count in top_words:
                        if count >= 2 and word not in existing_keywords:  # Only add if seen at least twice
                            self.analyzer.category_keywords[category].append(word)
                            
            # Regenerate embeddings with new keywords
            if hasattr(self.analyzer, '_generate_category_embeddings'):
                self.analyzer._generate_category_embeddings()
                
            log_activity("Applied user feedback to improve category recognition")
        
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
            
            # Also create a copy in the feedback directory with original category prefix
            # This allows the user to easily correct categorizations by moving files
            if self.config.enable_feedback_system:
                feedback_file = f"{category}--{new_name}"
                feedback_path = os.path.join(self.feedback_dir, "recent", feedback_file)
                
                # Ensure the recent directory exists
                recent_dir = os.path.join(self.feedback_dir, "recent")
                if not os.path.exists(recent_dir):
                    os.makedirs(recent_dir)
                    
                # Create a symbolic link or copy to the original file
                try:
                    # Try symlink first (more efficient)
                    if hasattr(os, 'symlink'):
                        os.symlink(destination, feedback_path)
                    else:
                        # Fall back to copying on platforms without symlink support
                        shutil.copy2(destination, feedback_path)
                        
                    # Limit the number of recent files to 50
                    recent_files = [os.path.join(recent_dir, f) for f in os.listdir(recent_dir)]
                    if len(recent_files) > 50:
                        # Sort by modification time and remove oldest
                        recent_files.sort(key=lambda x: os.path.getmtime(x))
                        for old_file in recent_files[:-50]:
                            os.remove(old_file)
                            
                except Exception as e:
                    log_activity(f"Error creating feedback link: {e}")
            
            # Add file to deduplication database if enabled
            if self.dedup_manager and not is_duplicate and file_hash:
                self.dedup_manager.add_file_record(file_hash, destination, category)
            
        except Exception as e:
            log_activity(f"Error processing {os.path.basename(file_path)}: {e}")