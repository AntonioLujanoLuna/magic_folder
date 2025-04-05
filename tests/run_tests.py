#!/usr/bin/env python
"""
Test runner script for Magic Folder project

This script discovers and runs all tests in the test suite.
"""

import unittest
import sys
import os

def run_tests():
    """Discover and run all tests in the test suite"""
    # Ensure the parent directory is in the Python path for imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Discover tests in the current directory
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_tests()) 