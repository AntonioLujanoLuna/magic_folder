"""
Main entry point for the Magic Folder application
"""

import os
import time
import argparse
from pathlib import Path
import pkg_resources
from watchdog.observers import Observer

from magic_folder.config import Config
from magic_folder.analyzer import AIAnalyzer
from magic_folder.file_handler import FileHandler
from magic_folder.utils import log_activity

def get_default_config_path():
    """Get the path to the default configuration file"""
    return pkg_resources.resource_filename('magic_folder', 'config/default_config.json')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Magic Folder - AI-powered file organization")
    parser.add_argument(
        "--config", 
        type=str, 
        default=None,
        help="Path to custom configuration file"
    )
    parser.add_argument(
        "--base-dir", 
        type=str, 
        default=None,
        help="Base directory for Magic Folder (overrides config setting)"
    )
    parser.add_argument(
        "--model", 
        type=str, 
        default=None,
        help="AI model to use (overrides config setting)"
    )
    return parser.parse_args()

def main():
    """Main function to run the magic folder"""
    print("Starting Magic Folder...")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Determine config file path
    config_path = args.config if args.config else get_default_config_path()
    
    # Create directories and load config
    config = Config(config_path)
    
    # Override config with command line arguments if provided
    if args.base_dir:
        config.base_dir = os.path.expanduser(args.base_dir)
        config.update_paths()
    
    if args.model:
        config.model_name = args.model
    
    # Ensure all directories exist
    config.ensure_directories()
    
    # Initialize AI Analyzer
    analyzer = AIAnalyzer(config)
    
    # Set up file system watcher
    event_handler = FileHandler(config, analyzer)
    observer = Observer()
    observer.schedule(event_handler, config.drop_dir, recursive=False)
    observer.start()
    
    print(f"Magic Folder is watching: {config.drop_dir}")
    print(f"Organized files will be placed in: {config.organized_dir}")
    print("Drop files into the watch folder to process them.")
    print("Press Ctrl+C to exit.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
    print("Magic Folder stopped.")

if __name__ == "__main__":
    main()