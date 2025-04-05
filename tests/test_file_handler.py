import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from pathlib import Path
from watchdog.events import FileCreatedEvent

from magic_folder.file_handler import FileHandler

class TestFileHandler(unittest.TestCase):
    """Tests for the FileHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.drop_dir = os.path.join(self.temp_dir, "incoming")
        self.organized_dir = os.path.join(self.temp_dir, "sorted")
        
        os.makedirs(self.drop_dir, exist_ok=True)
        os.makedirs(self.organized_dir, exist_ok=True)
        
        # Create mock config
        self.mock_config = MagicMock()
        self.mock_config.drop_dir = self.drop_dir
        self.mock_config.organized_dir = self.organized_dir
        self.mock_config.excluded_extensions = [".tmp", ".part"]
        self.mock_config.excluded_files = [".DS_Store", "Thumbs.db"]
        self.mock_config.processing_delay = 0.1
        self.mock_config.check_interval = 0.1
        self.mock_config.dedup_enabled = False
        
        # Create mock analyzer
        self.mock_analyzer = MagicMock()
        
        # Create mock content extractor
        self.mock_extractor = MagicMock()
        
        # Path to create test files
        self.test_file_path = os.path.join(self.drop_dir, "test_file.txt")
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    @patch('magic_folder.file_handler.ContentExtractor')
    def test_file_created_event(self, mock_content_extractor):
        """Test handling of file creation event"""
        # Setup mock content extractor
        mock_content_extractor.return_value = self.mock_extractor
        self.mock_extractor.extract_text.return_value = "Test content"
        
        # Setup mock analyzer response
        self.mock_analyzer.analyze_content.return_value = ("test_category", "test_file_renamed.txt")
        
        # Create a handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(self.mock_config, self.mock_analyzer)
            
            # Create test file
            with open(self.test_file_path, 'w') as f:
                f.write("Test content")
            
            # Create event and process it
            event = FileCreatedEvent(self.test_file_path)
            handler.on_created(event)
            
            # Directly process the file since we're not using real threads
            with handler.processing_lock:
                test_file = handler.processing_queue.pop(0)
            handler._process_file(test_file)
            
            # Check if file was processed correctly
            expected_path = os.path.join(self.organized_dir, "test_category", "test_file_renamed.txt")
            self.mock_analyzer.analyze_content.assert_called_once_with("Test content", self.test_file_path)
            
            # Directory should have been created
            self.assertTrue(os.path.exists(os.path.join(self.organized_dir, "test_category")))
    
    @patch('magic_folder.file_handler.ContentExtractor')
    def test_ignore_excluded_extension(self, mock_content_extractor):
        """Test that files with excluded extensions are ignored"""
        # Setup mock content extractor
        mock_content_extractor.return_value = self.mock_extractor
        
        # Create a handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(self.mock_config, self.mock_analyzer)
            
            # Create test file with excluded extension
            excluded_file_path = os.path.join(self.drop_dir, "test_file.tmp")
            with open(excluded_file_path, 'w') as f:
                f.write("Test content")
            
            # Create event and process it
            event = FileCreatedEvent(excluded_file_path)
            handler.on_created(event)
            
            # Queue should be empty because file was ignored
            with handler.processing_lock:
                self.assertEqual(len(handler.processing_queue), 0)
    
    @patch('magic_folder.file_handler.ContentExtractor')
    def test_ignore_directory_event(self, mock_content_extractor):
        """Test that directory creation events are ignored"""
        # Setup mock content extractor
        mock_content_extractor.return_value = self.mock_extractor
        
        # Create a handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(self.mock_config, self.mock_analyzer)
            
            # Create test directory
            test_dir_path = os.path.join(self.drop_dir, "test_dir")
            os.makedirs(test_dir_path, exist_ok=True)
            
            # Mock directory event
            event = MagicMock()
            event.is_directory = True
            event.src_path = test_dir_path
            
            # Process the event
            handler.on_created(event)
            
            # Queue should be empty because directory events are ignored
            with handler.processing_lock:
                self.assertEqual(len(handler.processing_queue), 0)
    
    @patch('magic_folder.file_handler.ContentExtractor')
    @patch('magic_folder.file_handler.DeduplicationManager')
    def test_deduplication_enabled(self, mock_dedup_manager, mock_content_extractor):
        """Test that deduplication works when enabled"""
        # Setup config with deduplication enabled
        self.mock_config.dedup_enabled = True
        
        # Setup mock content extractor
        mock_content_extractor.return_value = self.mock_extractor
        self.mock_extractor.extract_text.return_value = "Test content"
        
        # Setup mock deduplication manager
        mock_dedup_instance = MagicMock()
        mock_dedup_manager.return_value = mock_dedup_instance
        mock_dedup_instance.is_duplicate.return_value = (True, "/path/to/original.txt", "hash123")
        mock_dedup_instance.handle_duplicate.return_value = True
        
        # Create a handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(self.mock_config, self.mock_analyzer)
            
            # Create test file
            with open(self.test_file_path, 'w') as f:
                f.write("Test content")
            
            # Process the file
            handler._process_file(self.test_file_path)
            
            # Check that deduplication was used
            mock_dedup_instance.is_duplicate.assert_called_once_with(self.test_file_path)
            mock_dedup_instance.handle_duplicate.assert_called_once_with(self.test_file_path, "/path/to/original.txt")
            
            # Analyzer should not have been called since file was a duplicate
            self.mock_analyzer.analyze_content.assert_not_called()

if __name__ == '__main__':
    unittest.main() 