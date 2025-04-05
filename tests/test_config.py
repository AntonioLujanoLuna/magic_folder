import os
import unittest
import tempfile
import json
import shutil
from unittest.mock import patch, mock_open
from pathlib import Path

from magic_folder.config import Config

class TestConfig(unittest.TestCase):
    """Tests for the Config class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        
        # Create a sample config file
        self.sample_config = {
            "base_dir": "~/Documents/magic_folder",
            "drop_dir": "incoming",
            "organized_dir": "sorted", 
            "log_file": "magic_folder_log.txt",
            "model": {
                "name": "test-model",
                "sample_length": 500
            },
            "categories": [
                "test_category_1",
                "test_category_2"
            ],
            "category_keywords": {
                "test_category_1": ["keyword1", "keyword2"],
                "test_category_2": ["keyword3", "keyword4"]
            },
            "excluded_extensions": [".tmp"],
            "excluded_files": [".DS_Store"],
            "processing": {
                "delay_seconds": 1.5,
                "check_interval": 0.5
            },
            "deduplication": {
                "enabled": True,
                "hash_algorithm": "sha256",
                "strategy": "move_to_duplicates"
            },
            "ocr": {
                "languages": ["eng"]
            }
        }
        
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        with open(self.config_path, "w") as f:
            json.dump(self.sample_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_load_config_from_file(self):
        """Test loading configuration from a file"""
        config = Config(self.config_path)
        
        # Check if config was loaded correctly
        self.assertEqual(config.model_name, "test-model")
        self.assertEqual(config.sample_length, 500)
        self.assertEqual(config.categories, ["test_category_1", "test_category_2"])
        self.assertEqual(config.excluded_extensions, [".tmp"])
        self.assertEqual(config.processing_delay, 1.5)
        self.assertEqual(config.check_interval, 0.5)
        self.assertTrue(config.dedup_enabled)
        self.assertEqual(config.dedup_hash_algo, "sha256")
        self.assertEqual(config.dedup_strategy, "move_to_duplicates")
        self.assertEqual(config.ocr_languages, ["eng"])
    
    def test_default_values(self):
        """Test that default values are used when config is missing entries"""
        # Create a minimal config
        minimal_config = {
            "base_dir": "~/test_folder"
        }
        
        minimal_config_path = os.path.join(self.temp_dir, "minimal_config.json")
        
        with open(minimal_config_path, "w") as f:
            json.dump(minimal_config, f)
        
        # Load with minimal config and check defaults
        config = Config(minimal_config_path)
        
        # Base dir should be loaded from config
        self.assertEqual(os.path.basename(config.base_dir), "test_folder")
        
        # These should use default values
        self.assertIsNotNone(config.drop_dir)
        self.assertIsNotNone(config.organized_dir)
        self.assertIsNotNone(config.model_name)
        self.assertIsNotNone(config.categories)
        self.assertIsNotNone(config.processing_delay)
    
    def test_expand_paths(self):
        """Test path expansion in configuration"""
        with patch('os.path.expanduser') as mock_expanduser:
            mock_expanduser.side_effect = lambda path: path.replace('~', '/home/testuser')
            
            config = Config(self.config_path)
            
            # Check if home directory was expanded
            self.assertEqual(config.base_dir, "/home/testuser/Documents/magic_folder")
    
    def test_update_paths(self):
        """Test that paths are updated when base_dir changes"""
        config = Config(self.config_path)
        
        # Change the base directory
        orig_drop_dir = config.drop_dir
        config.base_dir = "/new/base/path"
        config.update_paths()
        
        # Check that drop_dir was updated
        self.assertNotEqual(config.drop_dir, orig_drop_dir)
        self.assertEqual(config.drop_dir, os.path.join("/new/base/path", "incoming"))
    
    def test_ensure_directories(self):
        """Test directory creation"""
        # Setup config with temp dir as base
        modified_config = self.sample_config.copy()
        modified_config["base_dir"] = self.temp_dir
        
        modified_config_path = os.path.join(self.temp_dir, "modified_config.json")
        with open(modified_config_path, "w") as f:
            json.dump(modified_config, f)
        
        # Load config and ensure directories
        config = Config(modified_config_path)
        config.ensure_directories()
        
        # Check that directories were created
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "incoming")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "sorted")))
        
        # Check category directories
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "sorted", "test_category_1")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "sorted", "test_category_2")))

if __name__ == '__main__':
    unittest.main() 