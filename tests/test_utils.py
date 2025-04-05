import os
import unittest
from unittest.mock import patch, mock_open
import tempfile
from datetime import datetime

from magic_folder.utils import log_activity, sanitize_filename, get_unique_filename

class TestUtils(unittest.TestCase):
    """Tests for utility functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    @patch('magic_folder.utils.datetime')
    def test_log_activity(self, mock_datetime):
        """Test logging activity"""
        # Mock the datetime to return a fixed timestamp
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
        
        # Create a mock file for log writing
        with patch('builtins.open', mock_open()) as mock_file:
            log_activity("Test log message")
            
            # Check if file was opened for appending
            mock_file.assert_called_once()
            mock_file().write.assert_called_once()
            
            # Check if timestamp was included
            log_call = mock_file().write.call_args[0][0]
            self.assertIn("2023-01-01 12:00:00", log_call)
            self.assertIn("Test log message", log_call)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test with various special characters
        test_cases = [
            ("File with spaces.txt", "File_with_spaces.txt"),
            ("File/with/slashes.txt", "File_with_slashes.txt"),
            ("File:with:colons.txt", "File_with_colons.txt"),
            ("File<with>invalid*chars?.txt", "File_with_invalid_chars_.txt"),
            ("..\\..\\Dangerous\\Path.txt", ".._.._.._Dangerous_Path.txt"),
            ("Very      long " + "a"*300 + ".txt", "Very_long_" + "a"*245 + ".txt"),
            ("Filename-with!@#$%^&()+=.txt", "Filename-with________.txt"),
            ("", "unnamed_file"),
        ]
        
        for input_name, expected_output in test_cases:
            sanitized = sanitize_filename(input_name)
            self.assertEqual(sanitized, expected_output)
    
    def test_get_unique_filename(self):
        """Test generating unique filenames"""
        # Create a directory with existing files
        test_dir = os.path.join(self.temp_dir, "unique_test")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create some test files
        existing_files = ["test.txt", "test_1.txt", "test_2.txt"]
        for filename in existing_files:
            with open(os.path.join(test_dir, filename), 'w') as f:
                f.write("Test content")
        
        # Test getting a unique filename
        unique_name = get_unique_filename(test_dir, "test.txt")
        self.assertEqual(unique_name, "test_3.txt")
        
        # Test with a filename that doesn't exist yet
        unique_name = get_unique_filename(test_dir, "new_file.txt")
        self.assertEqual(unique_name, "new_file.txt")
        
        # Test with no extension
        unique_name = get_unique_filename(test_dir, "no_extension")
        self.assertEqual(unique_name, "no_extension")
        
        # Test with existing file without extension
        with open(os.path.join(test_dir, "no_extension"), 'w') as f:
            f.write("Test content")
        unique_name = get_unique_filename(test_dir, "no_extension")
        self.assertEqual(unique_name, "no_extension_1")

if __name__ == '__main__':
    unittest.main() 