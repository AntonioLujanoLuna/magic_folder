#!/usr/bin/env python3
"""
Test script to verify Tesseract detection in Magic Folder
"""

import sys
import os

# Add the magic_folder module to the path
sys.path.insert(0, '.')

from magic_folder.content_extractor import ContentExtractor
from magic_folder.config import Config

def test_tesseract_detection():
    """Test if Tesseract is properly detected"""
    print("Testing Tesseract detection...")
    
    # Create a default config
    config = Config()
    
    # Initialize ContentExtractor
    extractor = ContentExtractor(config)
    
    # Check if Tesseract was detected
    if extractor.tesseract_available:
        print("✅ SUCCESS: Tesseract OCR detected and ready!")
        print("OCR features are enabled.")
    else:
        print("❌ FAILED: Tesseract OCR not detected.")
        print("OCR features are disabled.")
    
    return extractor.tesseract_available

if __name__ == "__main__":
    success = test_tesseract_detection()
    sys.exit(0 if success else 1) 