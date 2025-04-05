import os
import unittest
import tempfile
import sys
from unittest.mock import patch, MagicMock
from io import StringIO

from magic_folder.__main__ import main, parse_arguments

class TestMain(unittest.TestCase):
    """Tests for the main module and CLI functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        # Save original stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Redirect stdout and stderr for capturing CLI output
        sys.stdout = StringIO()
        sys.stderr = StringIO()
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Restore original stdout and stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def test_parse_arguments_defaults(self):
        """Test the argument parser with default values"""
        with patch('sys.argv', ['magic_folder']):
            args = parse_arguments()
            
            self.assertIsNone(args.config)
            self.assertIsNone(args.base_dir)
            self.assertIsNone(args.model)
    
    def test_parse_arguments_custom(self):
        """Test the argument parser with custom values"""
        with patch('sys.argv', [
            'magic_folder',
            '--config', '/path/to/config.json',
            '--base-dir', '~/custom_folder',
            '--model', 'custom-model'
        ]):
            args = parse_arguments()
            
            self.assertEqual(args.config, '/path/to/config.json')
            self.assertEqual(args.base_dir, '~/custom_folder')
            self.assertEqual(args.model, 'custom-model')
    
    @patch('magic_folder.__main__.get_default_config_path')
    @patch('magic_folder.__main__.Config')
    @patch('magic_folder.__main__.AIAnalyzer')
    @patch('magic_folder.__main__.FileHandler')
    @patch('magic_folder.__main__.Observer')
    def test_main_with_defaults(self, mock_observer, mock_file_handler, 
                               mock_analyzer, mock_config, mock_get_default_config):
        """Test the main function with default configuration"""
        # Set up mocks
        mock_get_default_config.return_value = self.config_path
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.drop_dir = os.path.join(self.temp_dir, "incoming")
        mock_config_instance.organized_dir = os.path.join(self.temp_dir, "sorted")
        
        mock_observer_instance = MagicMock()
        mock_observer.return_value = mock_observer_instance
        
        # Simulate a KeyboardInterrupt to exit the main loop
        mock_observer_instance.start.side_effect = KeyboardInterrupt()
        
        # Run the main function
        with patch('sys.argv', ['magic_folder']):
            main()
        
        # Check that all expected function calls were made
        mock_get_default_config.assert_called_once()
        mock_config.assert_called_once_with(self.config_path)
        mock_config_instance.ensure_directories.assert_called_once()
        mock_analyzer.assert_called_once_with(mock_config_instance)
        mock_file_handler.assert_called_once()
        mock_observer.assert_called_once()
        mock_observer_instance.schedule.assert_called_once()
        mock_observer_instance.start.assert_called_once()
        mock_observer_instance.stop.assert_called_once()
        mock_observer_instance.join.assert_called_once()
    
    @patch('magic_folder.__main__.get_default_config_path')
    @patch('magic_folder.__main__.Config')
    @patch('magic_folder.__main__.AIAnalyzer')
    @patch('magic_folder.__main__.FileHandler')
    @patch('magic_folder.__main__.Observer')
    def test_main_with_custom_args(self, mock_observer, mock_file_handler,
                                  mock_analyzer, mock_config, mock_get_default_config):
        """Test the main function with custom command line arguments"""
        # Set up mocks
        custom_config_path = "/path/to/custom_config.json"
        custom_base_dir = "/custom/base/dir"
        custom_model = "custom-model"
        
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        
        mock_observer_instance = MagicMock()
        mock_observer.return_value = mock_observer_instance
        
        # Simulate a KeyboardInterrupt to exit the main loop
        mock_observer_instance.start.side_effect = KeyboardInterrupt()
        
        # Run the main function with custom arguments
        with patch('sys.argv', [
            'magic_folder',
            '--config', custom_config_path,
            '--base-dir', custom_base_dir,
            '--model', custom_model
        ]):
            main()
        
        # Check that arguments were applied correctly
        mock_config.assert_called_once_with(custom_config_path)
        self.assertEqual(mock_config_instance.base_dir, custom_base_dir)
        self.assertEqual(mock_config_instance.model_name, custom_model)
        mock_config_instance.update_paths.assert_called_once()

if __name__ == '__main__':
    unittest.main() 