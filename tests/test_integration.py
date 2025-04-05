import os
import unittest
import tempfile
import shutil
import time
import json
from unittest.mock import patch
from pathlib import Path

from magic_folder.config import Config
from magic_folder.analyzer import AIAnalyzer
from magic_folder.file_handler import FileHandler
from magic_folder.content_extractor import ContentExtractor

class TestIntegration(unittest.TestCase):
    """Integration tests for Magic Folder"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        
        # Create directory structure
        self.base_dir = os.path.join(self.temp_dir, "magic_folder")
        self.drop_dir = os.path.join(self.base_dir, "incoming")
        self.organized_dir = os.path.join(self.base_dir, "sorted")
        
        # Create test config
        self.test_config = {
            "base_dir": self.base_dir,
            "drop_dir": "incoming",
            "organized_dir": "sorted",
            "log_file": "magic_folder_log.txt",
            "model": {
                "name": "distilbert-base-uncased",
                "sample_length": 1000
            },
            "categories": [
                "invoices",
                "receipts",
                "personal",
                "other"
            ],
            "category_keywords": {
                "invoices": ["invoice", "bill", "payment due"],
                "receipts": ["receipt", "thank you for your purchase", "order confirmation"],
                "personal": ["passport", "license", "identification"],
                "other": []
            },
            "excluded_extensions": [".tmp"],
            "excluded_files": [".DS_Store"],
            "processing": {
                "delay_seconds": 0.1,  # Use low values for testing
                "check_interval": 0.1
            },
            "deduplication": {
                "enabled": True,
                "hash_algorithm": "sha256",
                "strategy": "move_to_duplicates"
            }
        }
        
        # Write configuration to file
        with open(self.config_path, 'w') as f:
            json.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    @patch('magic_folder.analyzer.AutoTokenizer')
    @patch('magic_folder.analyzer.AutoModelForSequenceClassification')
    @patch('magic_folder.analyzer.pipeline')
    def test_full_workflow(self, mock_pipeline, mock_model, mock_tokenizer):
        """Test the full workflow from file drop to categorization"""
        # Load the configuration
        config = Config(self.config_path)
        config.ensure_directories()
        
        # Create analyzer and file handler
        analyzer = AIAnalyzer(config)
        
        # Set up analyzer to consistently categorize as "receipts"
        def mock_analyze_content(content, file_path):
            return "receipts", "test_receipt_20230101_120000.txt"
        
        analyzer.analyze_content = mock_analyze_content
        
        # Create file handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(config, analyzer)
            
            # Create a test file in the drop directory
            test_file_path = os.path.join(self.drop_dir, "test_receipt.txt")
            with open(test_file_path, 'w') as f:
                f.write("Thank you for your purchase\nTotal: $25.99\nDate: 01/01/2023")
            
            # Process the file manually (since we're not using real threads)
            handler._process_file(test_file_path)
            
            # Verify the file was categorized and moved
            receipt_dir = os.path.join(self.organized_dir, "receipts")
            self.assertTrue(os.path.exists(receipt_dir))
            
            # The original file should be gone
            self.assertFalse(os.path.exists(test_file_path))
            
            # There should be a file in the receipts directory
            renamed_files = os.listdir(receipt_dir)
            self.assertEqual(len(renamed_files), 1)
            self.assertEqual(renamed_files[0], "test_receipt_20230101_120000.txt")
    
    @patch('magic_folder.analyzer.AutoTokenizer')
    @patch('magic_folder.analyzer.AutoModelForSequenceClassification')
    @patch('magic_folder.analyzer.pipeline')
    def test_excluded_extension(self, mock_pipeline, mock_model, mock_tokenizer):
        """Test that files with excluded extensions are ignored"""
        # Load the configuration
        config = Config(self.config_path)
        config.ensure_directories()
        
        # Create analyzer and file handler
        analyzer = AIAnalyzer(config)
        
        # Create file handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(config, analyzer)
            
            # Create a test file with excluded extension
            test_file_path = os.path.join(self.drop_dir, "test_file.tmp")
            with open(test_file_path, 'w') as f:
                f.write("This is a temporary file that should be ignored")
            
            # Try to process the file
            handler.on_created(type('obj', (object,), {'is_directory': False, 'src_path': test_file_path}))
            
            # The file should not be in the processing queue
            self.assertEqual(len(handler.processing_queue), 0)
            
            # The file should still be in the drop directory
            self.assertTrue(os.path.exists(test_file_path))
    
    @patch('magic_folder.analyzer.AutoTokenizer')
    @patch('magic_folder.analyzer.AutoModelForSequenceClassification')
    @patch('magic_folder.analyzer.pipeline')
    def test_multiple_files(self, mock_pipeline, mock_model, mock_tokenizer):
        """Test processing multiple files"""
        # Load the configuration
        config = Config(self.config_path)
        config.ensure_directories()
        
        # Create analyzer with deterministic categories based on content
        analyzer = AIAnalyzer(config)
        
        def mock_analyze_content(content, file_path):
            if "invoice" in content.lower():
                return "invoices", "test_invoice_20230101.txt"
            elif "receipt" in content.lower():
                return "receipts", "test_receipt_20230101.txt"
            else:
                return "other", "test_other_20230101.txt"
        
        analyzer.analyze_content = mock_analyze_content
        
        # Create file handler with patched threading
        with patch('magic_folder.file_handler.threading'):
            handler = FileHandler(config, analyzer)
            
            # Create test files in the drop directory
            files = [
                ("invoice.txt", "INVOICE #12345\nAmount Due: $100.00"),
                ("receipt.txt", "RECEIPT\nThank you for your purchase"),
                ("unknown.txt", "Just some random text")
            ]
            
            for filename, content in files:
                file_path = os.path.join(self.drop_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                
                # Process the file
                handler._process_file(file_path)
            
            # Verify the files were categorized correctly
            self.assertTrue(os.path.exists(os.path.join(self.organized_dir, "invoices", "test_invoice_20230101.txt")))
            self.assertTrue(os.path.exists(os.path.join(self.organized_dir, "receipts", "test_receipt_20230101.txt")))
            self.assertTrue(os.path.exists(os.path.join(self.organized_dir, "other", "test_other_20230101.txt")))

if __name__ == '__main__':
    unittest.main() 