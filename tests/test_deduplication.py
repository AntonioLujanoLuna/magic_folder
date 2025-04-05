import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch
import hashlib

from magic_folder.deduplication import DeduplicationManager

class TestDeduplicationManager(unittest.TestCase):
    """Tests for the DeduplicationManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.duplicates_dir = os.path.join(self.temp_dir, "duplicates")
        os.makedirs(self.duplicates_dir, exist_ok=True)
        
        # Create a test file
        self.test_file_path = os.path.join(self.temp_dir, "original.txt")
        with open(self.test_file_path, 'w') as f:
            f.write("This is a test file for deduplication")
        
        # Create a duplicate file with the same content
        self.duplicate_file_path = os.path.join(self.temp_dir, "duplicate.txt")
        with open(self.duplicate_file_path, 'w') as f:
            f.write("This is a test file for deduplication")
        
        # Create a different file
        self.different_file_path = os.path.join(self.temp_dir, "different.txt")
        with open(self.different_file_path, 'w') as f:
            f.write("This file has different content")
        
        # Calculate the hash of the test file
        with open(self.test_file_path, 'rb') as f:
            self.test_file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Setup mock config
        self.mock_config = MagicMock()
        self.mock_config.dedup_enabled = True
        self.mock_config.dedup_hash_algo = "sha256"
        self.mock_config.dedup_strategy = "move_to_duplicates"
        self.mock_config.dedup_dir = self.duplicates_dir
        self.mock_config.organized_dir = self.temp_dir
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_init_db(self, mock_sqlite3):
        """Test database initialization"""
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Check if database was initialized
        mock_sqlite3.connect.assert_called_once()
        mock_cursor.execute.assert_called()  # Should call execute to create table
    
    def test_calculate_file_hash(self):
        """Test hash calculation"""
        # Create the deduplication manager with mocked database connection
        with patch('magic_folder.deduplication.sqlite3'):
            dedup_manager = DeduplicationManager(self.mock_config)
            
            # Calculate hash of the test file
            file_hash = dedup_manager._calculate_file_hash(self.test_file_path)
            
            # Check if hash matches the pre-calculated hash
            self.assertEqual(file_hash, self.test_file_hash)
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_is_duplicate_true(self, mock_sqlite3):
        """Test duplicate detection when a duplicate exists"""
        # Set up mock cursor to return a match for the file hash
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (self.test_file_hash, self.test_file_path, "category")
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Check if duplicate detection works
        is_duplicate, original_path, file_hash = dedup_manager.is_duplicate(self.duplicate_file_path)
        
        self.assertTrue(is_duplicate)
        self.assertEqual(original_path, self.test_file_path)
        self.assertEqual(file_hash, self.test_file_hash)
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_is_duplicate_false(self, mock_sqlite3):
        """Test duplicate detection when no duplicate exists"""
        # Set up mock cursor to return no match for the file hash
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Check non-duplicate detection
        is_duplicate, original_path, file_hash = dedup_manager.is_duplicate(self.different_file_path)
        
        self.assertFalse(is_duplicate)
        self.assertIsNone(original_path)
        self.assertIsNotNone(file_hash)  # Should still return the hash
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_handle_duplicate_delete(self, mock_sqlite3):
        """Test handling duplicates with delete strategy"""
        # Set up mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configure for delete strategy
        self.mock_config.dedup_strategy = "delete"
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Create a file to be deleted
        temp_duplicate = os.path.join(self.temp_dir, "to_delete.txt")
        with open(temp_duplicate, 'w') as f:
            f.write("This file should be deleted")
        
        # Handle the duplicate
        result = dedup_manager.handle_duplicate(temp_duplicate, self.test_file_path)
        
        # Check if file was deleted
        self.assertTrue(result)
        self.assertFalse(os.path.exists(temp_duplicate))
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_handle_duplicate_move(self, mock_sqlite3):
        """Test handling duplicates with move strategy"""
        # Set up mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Configure for move strategy
        self.mock_config.dedup_strategy = "move_to_duplicates"
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Create a file to be moved
        temp_duplicate = os.path.join(self.temp_dir, "to_move.txt")
        with open(temp_duplicate, 'w') as f:
            f.write("This file should be moved")
        
        # Handle the duplicate
        result = dedup_manager.handle_duplicate(temp_duplicate, self.test_file_path)
        
        # Check if file was moved
        self.assertTrue(result)
        self.assertFalse(os.path.exists(temp_duplicate))
        self.assertTrue(os.path.exists(os.path.join(self.duplicates_dir, "to_move.txt")))
    
    @patch('magic_folder.deduplication.sqlite3')
    def test_add_file_record(self, mock_sqlite3):
        """Test adding a file record to the database"""
        # Set up mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_sqlite3.connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Create the deduplication manager
        dedup_manager = DeduplicationManager(self.mock_config)
        
        # Add a file record
        dedup_manager.add_file_record("test_hash", "/path/to/file.txt", "test_category")
        
        # Check if record was added
        mock_cursor.execute.assert_called_with(
            "INSERT OR REPLACE INTO files (hash, path, category) VALUES (?, ?, ?)",
            ("test_hash", "/path/to/file.txt", "test_category")
        )
        mock_conn.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main() 