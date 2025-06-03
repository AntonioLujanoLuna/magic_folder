"""
Tests for security improvements and robustness features
"""

import os
import tempfile
import threading
import queue
import time
import unittest
from unittest.mock import Mock, patch

from magic_folder.config import Config
from magic_folder.analyzer import AIAnalyzer
from magic_folder.file_handler import FileHandler
from magic_folder.content_extractor import ContentExtractor


class TestSecurityImprovements(unittest.TestCase):
    """Test security improvements and robustness features"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        # Don't initialize config in setUp since some tests need to test invalid paths
        # Individual tests will create configs as needed
    
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_path_validation_dangerous_paths(self):
        """Test that dangerous system paths are rejected"""
        import platform
        
        if platform.system() == 'Windows':
            dangerous_paths = [
                'C:\\',
                'C:\\Windows',
                'C:\\Program Files',
                'C:\\Program Files (x86)',
                'C:\\Windows\\System32'
            ]
        else:
            dangerous_paths = [
                '/',
                '/bin',
                '/etc',
                '/var/log',
                '/home',
                '/root'
            ]
        
        for dangerous_path in dangerous_paths:
            config = Config.__new__(Config)  # Create without calling __init__
            config.base_dir = dangerous_path
            # Set minimal attributes needed for validation
            config.drop_dir_name = "drop"
            config.organized_dir_name = "organized"
            config.log_file_name = "activity_log.txt"
            config.feedback_dir_name = "feedback"
            
            with self.assertRaises(ValueError):
                config.update_paths()
    
    def test_path_validation_too_shallow(self):
        """Test that paths too close to filesystem root are rejected"""
        import platform
        
        if platform.system() == 'Windows':
            shallow_paths = [
                'C:\\',
                'D:\\'
            ]
        else:
            shallow_paths = [
                '/',
                '/tmp',
                '/Users',
                '/var'
            ]
        
        for shallow_path in shallow_paths:
            config = Config.__new__(Config)  # Create without calling __init__
            config.base_dir = shallow_path
            # Set minimal attributes needed for validation
            config.drop_dir_name = "drop"
            config.organized_dir_name = "organized"
            config.log_file_name = "activity_log.txt"
            config.feedback_dir_name = "feedback"
            
            with self.assertRaises(ValueError):
                config.update_paths()
    
    def test_thread_safe_queue_operations(self):
        """Test that file processing queue is thread-safe"""
        # Create a simple config for testing
        config = Config.__new__(Config)
        config.base_dir = self.temp_dir
        config.drop_dir_name = "drop"
        config.organized_dir_name = "organized"
        config.log_file_name = "activity_log.txt"
        config.feedback_dir_name = "feedback"
        config.dedup_enabled = False
        config.enable_feedback_system = False
        config.excluded_extensions = []
        config.excluded_files = []
        config.processing_delay = 1
        config.update_paths()
        config.ensure_directories()
        
        analyzer = AIAnalyzer(config, offline_mode=True)
        handler = FileHandler(config, analyzer, dry_run=True)
        
        # Test queue is actually a thread-safe queue
        self.assertIsInstance(handler.processing_queue, queue.Queue)
        
        # Test queue size limit
        max_size = handler.processing_queue.maxsize
        self.assertEqual(max_size, 100)
        
        # Test adding files beyond limit
        for i in range(max_size + 10):
            try:
                handler.processing_queue.put_nowait(f"test_file_{i}.txt")
            except queue.Full:
                # This is expected when queue is full
                break
        
        # Queue should be at max capacity
        self.assertTrue(handler.processing_queue.full())
        
        # Clean up
        handler.shutdown()
    
    def test_keyword_updates_thread_safety(self):
        """Test that keyword updates are thread-safe"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        analyzer = AIAnalyzer(config, offline_mode=True)
        handler = FileHandler(config, analyzer, dry_run=True)
        
        # Verify lock exists
        self.assertIsInstance(handler.keyword_update_lock, threading.Lock)
        
        # Simulate concurrent keyword updates
        def update_keywords(category, words):
            for word in words:
                with handler.keyword_update_lock:
                    if category not in analyzer.category_keywords:
                        analyzer.category_keywords[category] = []
                    analyzer.category_keywords[category].append(word)
        
        threads = []
        for i in range(5):
            t = threading.Thread(
                target=update_keywords,
                args=(f"category_{i}", [f"word_{i}_{j}" for j in range(10)])
            )
            threads.append(t)
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify all keywords were added
        total_keywords = sum(len(keywords) for keywords in analyzer.category_keywords.values())
        self.assertEqual(total_keywords, 50)  # 5 categories * 10 words each
        
        # Clean up
        handler.shutdown()
    
    def test_large_file_memory_management(self):
        """Test memory management for large files"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        extractor = ContentExtractor(config)
        
        # Create a large dummy file
        large_file = os.path.join(self.temp_dir, "large_test.txt")
        with open(large_file, 'w') as f:
            # Write 10MB of text
            for i in range(100000):
                f.write("This is a test line to make the file large. " * 10 + "\n")
        
        file_size = os.path.getsize(large_file)
        self.assertGreater(file_size, 10 * 1024 * 1024)  # > 10MB
        
        # Test extraction with size warnings
        with patch('magic_folder.utils.log_activity') as mock_log:
            content = extractor.extract_text(large_file)
            
            # Should have logged a warning about large file
            warning_logged = any(
                "Warning: Large file" in str(call) 
                for call in mock_log.call_args_list
            )
            self.assertTrue(warning_logged)
            
            # Content should be limited to sample length
            self.assertLessEqual(len(content), extractor.sample_length)
    
    def test_file_hash_calculation_memory_efficient(self):
        """Test that file hashing is memory efficient for large files"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        extractor = ContentExtractor(config)
        
        # Create a large file (>10MB)
        large_file = os.path.join(self.temp_dir, "large_hash_test.bin")
        with open(large_file, 'wb') as f:
            # Write 15MB of data
            chunk = b'0' * 1024 * 1024  # 1MB chunk
            for i in range(15):
                f.write(chunk)
        
        file_size = os.path.getsize(large_file)
        self.assertGreater(file_size, 10 * 1024 * 1024)
        
        # Calculate hash - should not crash or use excessive memory
        file_hash = extractor._calculate_file_hash(large_file)
        self.assertIsNotNone(file_hash)
        self.assertEqual(len(file_hash), 32)  # MD5 hex digest length
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown of file handler"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        analyzer = AIAnalyzer(config, offline_mode=True)
        handler = FileHandler(config, analyzer, dry_run=True)
        
        # Verify shutdown event exists
        self.assertIsInstance(handler.shutdown_event, threading.Event)
        self.assertFalse(handler.shutdown_event.is_set())
        
        # Test shutdown
        handler.shutdown()
        
        # Shutdown event should be set
        self.assertTrue(handler.shutdown_event.is_set())
    
    def test_file_size_limits(self):
        """Test file size handling and limits"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        extractor = ContentExtractor(config)
        
        # Test with normal size file
        normal_file = os.path.join(self.temp_dir, "normal.txt")
        with open(normal_file, 'w') as f:
            f.write("This is a normal sized file for testing.")
        
        # Should process normally without warnings
        with patch('magic_folder.utils.log_activity') as mock_log:
            content = extractor.extract_text(normal_file)
            
            # Should not log size warnings
            size_warnings = [
                call for call in mock_log.call_args_list 
                if "Warning: Large file" in str(call)
            ]
            self.assertEqual(len(size_warnings), 0)
    
    def test_offline_mode_functionality(self):
        """Test that offline mode works without network dependencies"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        analyzer = AIAnalyzer(config, offline_mode=True)
        
        # Should not have model available
        self.assertFalse(analyzer.model_available)
        self.assertTrue(analyzer.offline_mode)
        
        # Should still be able to analyze content using keywords
        test_content = "This is a medical report about patient health."
        category, filename = analyzer.analyze_content(test_content, "test.txt")
        
        # Should return a valid category and filename
        self.assertIsInstance(category, str)
        self.assertIsInstance(filename, str)
        self.assertIn(category, config.categories)
    
    def test_dry_run_mode(self):
        """Test dry run mode functionality"""
        config = Config()
        config.base_dir = self.temp_dir
        config.update_paths()
        config.ensure_directories()
        analyzer = AIAnalyzer(config, offline_mode=True)
        handler = FileHandler(config, analyzer, dry_run=True)
        
        # Verify dry run mode is set
        self.assertTrue(handler.dry_run)
        
        # Clean up quickly to avoid background threads
        handler.shutdown()


if __name__ == '__main__':
    unittest.main() 