import os
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import json

from magic_folder.analyzer import AIAnalyzer
from magic_folder.config import Config

class TestAIAnalyzer(unittest.TestCase):
    """Tests for the AIAnalyzer class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock config
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.model_name = "distilbert-base-uncased"
        self.mock_config.categories = ["taxes", "receipts", "personal_id", "other"]
        self.mock_config.category_keywords = {
            "taxes": ["tax", "taxes", "irs", "return", "w-2", "w2", "1099", "deduction"],
            "receipts": ["receipt", "purchase", "order", "transaction", "payment"],
            "personal_id": ["passport", "license", "id", "identification", "birth", "certificate", "ssn"],
            "other": []
        }
        
        # Mock the AI model components for testing
        with patch('magic_folder.analyzer.AutoTokenizer'), \
             patch('magic_folder.analyzer.AutoModelForSequenceClassification'), \
             patch('magic_folder.analyzer.pipeline'):
            self.analyzer = AIAnalyzer(self.mock_config)
    
    def test_analyze_content_tax_document(self):
        """Test analyzing a tax document"""
        content = """
        FORM W-2 Wage and Tax Statement 2023
        Employer: Acme Corporation
        Employee: John Doe
        SSN: XXX-XX-1234
        Federal income tax withheld: $5,000.00
        """
        
        file_path = "/path/to/document.pdf"
        category, new_name = self.analyzer.analyze_content(content, file_path)
        
        self.assertEqual(category, "taxes")
        self.assertTrue(new_name.startswith("FORM_W-2_Wage_and_Tax_Statement"))
        self.assertTrue(new_name.endswith(".pdf"))
    
    def test_analyze_content_receipt(self):
        """Test analyzing a receipt"""
        content = """
        RECEIPT
        Store: Grocery Mart
        Date: 01/15/2023
        Items:
        - Milk $2.99
        - Bread $1.99
        Total payment: $4.98
        Thank you for your purchase!
        """
        
        file_path = "/path/to/receipt.jpg"
        category, new_name = self.analyzer.analyze_content(content, file_path)
        
        self.assertEqual(category, "receipts")
        self.assertTrue(new_name.startswith("RECEIPT"))
        self.assertTrue(new_name.endswith(".jpg"))
    
    def test_analyze_content_no_match(self):
        """Test analyzing content with no category match"""
        content = """
        Random text that doesn't match any category.
        Lorem ipsum dolor sit amet.
        """
        
        file_path = "/path/to/document.txt"
        category, new_name = self.analyzer.analyze_content(content, file_path)
        
        self.assertEqual(category, "other")
        self.assertTrue(new_name.endswith(".txt"))
    
    def test_analyze_content_empty(self):
        """Test analyzing empty content"""
        content = ""
        file_path = "/path/to/document.txt"
        
        category, new_name = self.analyzer.analyze_content(content, file_path)
        
        self.assertEqual(category, "other")
        self.assertTrue("unprocessed_" in new_name)
        self.assertTrue(new_name.endswith(".txt"))

    def test_extract_title_from_content(self):
        """Test title extraction from content"""
        content = """
        This is the first line and should be the title
        Second line with less importance
        Third line with even less importance
        """
        
        title = self.analyzer._extract_title_from_content(content)
        self.assertEqual(title, "This_is_the_first_line_and_should_be")
    
    def test_extract_title_from_content_short_first_line(self):
        """Test title extraction when first line is too short"""
        content = """
        Hi
        This is a better title for the document
        Other content follows
        """
        
        title = self.analyzer._extract_title_from_content(content)
        self.assertEqual(title, "This_is_a_better_title_for_the_docu")

if __name__ == '__main__':
    unittest.main()
