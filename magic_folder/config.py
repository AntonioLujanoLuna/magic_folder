"""
Configuration management for Magic Folder
"""

import os
import json
from pathlib import Path

class Config:
    """Configuration manager for the magic folder"""
    
    def __init__(self, config_path=None):
        """
        Initialize configuration from a JSON file
        
        Args:
            config_path (str, optional): Path to the configuration file
        """
        # Default configuration
        self.base_dir = os.path.expanduser("~/magic_folder")
        self.drop_dir_name = "drop"
        self.organized_dir_name = "organized"
        self.log_file_name = "activity_log.txt"
        self.model_name = "distilbert-base-uncased"
        self.sample_length = 1000
        self.categories = ["taxes", "receipts", "personal_id", "medical", 
                          "work", "education", "financial", "legal", 
                          "correspondence", "other"]
        self.category_keywords = {}
        self.excluded_extensions = ['.tmp', '.part', '.crdownload']
        self.excluded_files = ['.DS_Store', 'Thumbs.db']
        self.processing_delay = 1
        self.check_interval = 0.5
        
        # Deduplication settings
        self.dedup_enabled = True
        self.dedup_hash_method = "md5"  # md5, sha1, sha256
        self.dedup_action = "move"  # skip, move, process
        
        # Advanced file type settings
        self.enable_audio_analysis = True
        self.enable_video_analysis = True
        self.enable_archive_inspection = True
        self.ocr_languages = ["eng"]
        
        # New settings for performance and feedback
        self.enable_content_cache = True
        self.content_cache_size = 500
        self.enable_feedback_system = True
        self.feedback_dir_name = "feedback"
        self.embedding_similarity_threshold = 0.3
        self.enable_embedding_cache = True
        self.embedding_cache_size = 1000
        
        # Load from file if provided
        if config_path:
            self.load_config(config_path)
            
        # Set derived paths
        self.update_paths()
        
    def update_paths(self):
        """Update derived paths based on base directory"""
        self.drop_dir = os.path.join(self.base_dir, self.drop_dir_name)
        self.organized_dir = os.path.join(self.base_dir, self.organized_dir_name)
        self.log_file = os.path.join(self.base_dir, self.log_file_name)
        self.config_file = os.path.join(self.base_dir, "config.json")
        self.feedback_dir = os.path.join(self.base_dir, self.feedback_dir_name)
        
    def load_config(self, config_path):
        """
        Load configuration from file
        
        Args:
            config_path (str): Path to the configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Base settings
            self.base_dir = os.path.expanduser(config.get('base_dir', self.base_dir))
            self.drop_dir_name = config.get('drop_dir', self.drop_dir_name)
            self.organized_dir_name = config.get('organized_dir', self.organized_dir_name)
            self.log_file_name = config.get('log_file', self.log_file_name)
            
            # Model settings
            model_config = config.get('model', {})
            self.model_name = model_config.get('name', self.model_name)
            self.sample_length = model_config.get('sample_length', self.sample_length)
            
            # Categories and keywords
            self.categories = config.get('categories', self.categories)
            self.category_keywords = config.get('category_keywords', self.category_keywords)
            
            # File exclusions
            self.excluded_extensions = config.get('excluded_extensions', self.excluded_extensions)
            self.excluded_files = config.get('excluded_files', self.excluded_files)
            
            # Processing settings
            processing = config.get('processing', {})
            self.processing_delay = processing.get('delay_seconds', self.processing_delay)
            self.check_interval = processing.get('check_interval', self.check_interval)
            
            # Deduplication settings
            dedup_config = config.get('deduplication', {})
            self.dedup_enabled = dedup_config.get('enabled', self.dedup_enabled)
            self.dedup_hash_method = dedup_config.get('hash_method', self.dedup_hash_method)
            self.dedup_action = dedup_config.get('action', self.dedup_action)
            
            # Advanced file type settings
            file_types = config.get('advanced_file_types', {})
            self.enable_audio_analysis = file_types.get('enable_audio_analysis', self.enable_audio_analysis)
            self.enable_video_analysis = file_types.get('enable_video_analysis', self.enable_video_analysis)
            self.enable_archive_inspection = file_types.get('enable_archive_inspection', self.enable_archive_inspection)
            self.ocr_languages = file_types.get('ocr_languages', self.ocr_languages)
            
            # Performance and feedback settings
            performance = config.get('performance', {})
            self.enable_content_cache = performance.get('enable_content_cache', self.enable_content_cache)
            self.content_cache_size = performance.get('content_cache_size', self.content_cache_size)
            self.enable_embedding_cache = performance.get('enable_embedding_cache', self.enable_embedding_cache)
            self.embedding_cache_size = performance.get('embedding_cache_size', self.embedding_cache_size)
            
            feedback = config.get('feedback', {})
            self.enable_feedback_system = feedback.get('enable_feedback_system', self.enable_feedback_system)
            self.feedback_dir_name = feedback.get('feedback_dir_name', self.feedback_dir_name)
            self.embedding_similarity_threshold = feedback.get('embedding_similarity_threshold', self.embedding_similarity_threshold)
            
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            print("Using default configuration")
            
    def save_config(self):
        """Save current configuration to file"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        config = {
            'base_dir': self.base_dir,
            'drop_dir': self.drop_dir_name,
            'organized_dir': self.organized_dir_name,
            'log_file': self.log_file_name,
            'model': {
                'name': self.model_name,
                'sample_length': self.sample_length
            },
            'categories': self.categories,
            'category_keywords': self.category_keywords,
            'excluded_extensions': self.excluded_extensions,
            'excluded_files': self.excluded_files,
            'processing': {
                'delay_seconds': self.processing_delay,
                'check_interval': self.check_interval
            },
            'deduplication': {
                'enabled': self.dedup_enabled,
                'hash_method': self.dedup_hash_method,
                'action': self.dedup_action
            },
            'advanced_file_types': {
                'enable_audio_analysis': self.enable_audio_analysis,
                'enable_video_analysis': self.enable_video_analysis,
                'enable_archive_inspection': self.enable_archive_inspection,
                'ocr_languages': self.ocr_languages
            },
            'performance': {
                'enable_content_cache': self.enable_content_cache,
                'content_cache_size': self.content_cache_size,
                'enable_embedding_cache': self.enable_embedding_cache,
                'embedding_cache_size': self.embedding_cache_size
            },
            'feedback': {
                'enable_feedback_system': self.enable_feedback_system,
                'feedback_dir_name': self.feedback_dir_name,
                'embedding_similarity_threshold': self.embedding_similarity_threshold
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
            
    def ensure_directories(self):
        """Ensure all necessary directories exist"""
        # Create base directory if it doesn't exist
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
        # Create drop directory if it doesn't exist
        if not os.path.exists(self.drop_dir):
            os.makedirs(self.drop_dir)
            
        # Create organized directory if it doesn't exist
        if not os.path.exists(self.organized_dir):
            os.makedirs(self.organized_dir)
            
        # Create feedback directory if enabled
        if self.enable_feedback_system and not os.path.exists(self.feedback_dir):
            os.makedirs(self.feedback_dir)
            # Create 'recent' subdirectory
            recent_dir = os.path.join(self.feedback_dir, "recent")
            if not os.path.exists(recent_dir):
                os.makedirs(recent_dir)
            
        # Create category directories
        for category in self.categories:
            # In organized directory
            category_dir = os.path.join(self.organized_dir, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
                
            # In feedback directory if enabled
            if self.enable_feedback_system:
                feedback_category_dir = os.path.join(self.feedback_dir, category)
                if not os.path.exists(feedback_category_dir):
                    os.makedirs(feedback_category_dir)