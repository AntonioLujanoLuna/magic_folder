import os
import unittest
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import magic
import PyPDF2
from PIL import Image

from magic_folder.content_extractor import ContentExtractor

class TestContentExtractor(unittest.TestCase):
    """Tests for the ContentExtractor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_config = MagicMock()
        self.mock_config.sample_length = 1000
        self.mock_config.ocr_languages = ['eng']
        self.mock_config.enable_audio_analysis = False
        self.mock_config.enable_video_analysis = False
        self.mock_config.enable_archive_inspection = True
        
        self.extractor = ContentExtractor(self.mock_config)
    
    @patch('magic.Magic')
    @patch('builtins.open', new_callable=mock_open, read_data="This is a test text file")
    def test_extract_from_text_file(self, mock_file, mock_magic):
        """Test extracting content from a text file"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'text/plain'
        mock_magic.return_value = mock_magic_instance
        
        result = self.extractor.extract_text('test.txt')
        
        self.assertEqual(result, "This is a test text file")
        mock_file.assert_called_once_with('test.txt', 'r', encoding='utf-8', errors='ignore')
    
    @patch('magic.Magic')
    @patch('PyPDF2.PdfReader')
    def test_extract_from_pdf(self, mock_pdf_reader, mock_magic):
        """Test extracting content from a PDF file"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'application/pdf'
        mock_magic.return_value = mock_magic_instance
        
        # Configure PDF mock
        mock_pdf = MagicMock()
        mock_pdf.metadata = {'Author': 'Test Author', 'Title': 'Test Document'}
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "This is PDF text content"
        mock_pdf.pages = [mock_page]
        mock_pdf_reader.return_value = mock_pdf
        
        with patch('builtins.open', mock_open()):
            result = self.extractor.extract_text('test.pdf')
        
        self.assertIn("PDF Metadata:", result)
        self.assertIn("Author: Test Author", result)
        self.assertIn("Title: Test Document", result)
        self.assertIn("This is PDF text content", result)
    
    @patch('magic.Magic')
    @patch('pytesseract.image_to_string')
    def test_extract_from_image(self, mock_ocr, mock_magic):
        """Test extracting content from an image using OCR"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'image/jpeg'
        mock_magic.return_value = mock_magic_instance
        
        # Configure OCR mock
        mock_ocr.return_value = "Extracted text from image"
        
        # Create a temporary image file for testing
        with tempfile.NamedTemporaryFile(suffix='.jpg') as temp_file:
            with patch('PIL.Image.open') as mock_pil:
                mock_img = MagicMock()
                mock_pil.return_value = mock_img
                
                result = self.extractor.extract_text(temp_file.name)
                
                self.assertEqual(result, "Extracted text from image")
                mock_ocr.assert_called_once()
    
    @patch('magic.Magic')
    @patch('magic_folder.content_extractor.textract')
    def test_extract_from_docx(self, mock_textract, mock_magic):
        """Test extracting content from a Word document"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        mock_magic.return_value = mock_magic_instance
        
        # Configure textract mock
        mock_textract.process.return_value = b"This is a Word document"
        
        result = self.extractor.extract_text('test.docx')
        
        self.assertIn("This is a Word document", result)
        mock_textract.process.assert_called_once_with('test.docx')
    
    @patch('magic.Magic')
    def test_extract_from_json(self, mock_magic):
        """Test extracting content from a JSON file"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'application/json'
        mock_magic.return_value = mock_magic_instance
        
        json_content = '{"name": "Test", "description": "This is a test JSON file"}'
        
        with patch('builtins.open', mock_open(read_data=json_content)):
            result = self.extractor.extract_text('test.json')
        
        self.assertIn("Test", result)
        self.assertIn("This is a test JSON file", result)
    
    @patch('magic.Magic')
    def test_extract_handle_error(self, mock_magic):
        """Test handling errors during extraction"""
        # Configure magic mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'text/plain'
        mock_magic.return_value = mock_magic_instance
        
        # Simulate an error when opening the file
        with patch('builtins.open', side_effect=Exception("Test error")):
            result = self.extractor.extract_text('test.txt')
        
        self.assertIn("Error extracting content", result)

if __name__ == '__main__':
    unittest.main() 