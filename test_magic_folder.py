#!/usr/bin/env python3
"""
Test script for Magic Folder
Verifies that all components are working correctly
"""

import os
import sys
import tempfile
import requests
import time
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    try:
        import magic_folder
        from magic_folder.config import Config
        from magic_folder.analyzer import AIAnalyzer
        from magic_folder.content_extractor import ContentExtractor
        from magic_folder.web_interface import setup_app
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("Testing configuration...")
    try:
        from magic_folder.config import Config
        config = Config()
        print(f"✅ Config loaded with {len(config.categories)} categories")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_ai_analyzer():
    """Test AI analyzer initialization"""
    print("Testing AI analyzer...")
    try:
        from magic_folder.config import Config
        from magic_folder.analyzer import AIAnalyzer
        
        config = Config()
        analyzer = AIAnalyzer(config)
        
        # Test content analysis
        test_content = "This is a tax document for the year 2023"
        category, filename = analyzer.analyze_content(test_content, "test.txt")
        print(f"✅ AI analyzer working - categorized as: {category}")
        return True
    except Exception as e:
        print(f"❌ AI analyzer error: {e}")
        return False

def test_content_extractor():
    """Test content extraction"""
    print("Testing content extractor...")
    try:
        from magic_folder.config import Config
        from magic_folder.content_extractor import ContentExtractor
        
        config = Config()
        extractor = ContentExtractor(config)
        
        # Create a test text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a test document about taxes and receipts.")
            test_file = f.name
        
        try:
            content = extractor.extract_text(test_file)
            print(f"✅ Content extractor working - extracted {len(content)} characters")
            return True
        finally:
            os.unlink(test_file)
            
    except Exception as e:
        print(f"❌ Content extractor error: {e}")
        return False

def test_web_interface():
    """Test web interface"""
    print("Testing web interface...")
    try:
        # Try to connect to the web interface
        response = requests.get('http://127.0.0.1:5002', timeout=5)
        if response.status_code == 200:
            print("✅ Web interface is responding")
            return True
        else:
            print(f"❌ Web interface returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Web interface error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Magic Folder Installation")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_config,
        test_ai_analyzer,
        test_content_extractor,
        test_web_interface
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Magic Folder is working correctly.")
        print("\n🚀 You can now:")
        print("  1. Drop files into ~/magic_folder/drop to test file processing")
        print("  2. Visit http://127.0.0.1:5002 to use the web interface")
        print("  3. Run 'magic-folder --help' for more options")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 