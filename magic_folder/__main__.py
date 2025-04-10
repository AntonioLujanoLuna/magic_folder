"""
Main entry point for the Magic Folder application
"""

import os
import time
import argparse
import threading
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
    parser.add_argument(
        "--feedback",
        action="store_true",
        default=None,
        help="Enable user feedback system"
    )
    parser.add_argument(
        "--no-feedback",
        action="store_true",
        default=None,
        help="Disable user feedback system"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        default=None,
        help="Enable content and embedding caching"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=None,
        help="Disable content and embedding caching"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start the web interface"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for the web interface (default: 5000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host for the web interface (default: 127.0.0.1)"
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
    
    # Handle feedback system settings
    if args.feedback:
        config.enable_feedback_system = True
    elif args.no_feedback:
        config.enable_feedback_system = False
    
    # Handle caching settings
    if args.cache:
        config.enable_content_cache = True
        config.enable_embedding_cache = True
    elif args.no_cache:
        config.enable_content_cache = False
        config.enable_embedding_cache = False
    
    # Ensure all directories exist
    config.ensure_directories()
    
    # Initialize AI Analyzer
    analyzer = AIAnalyzer(config)
    
    # Set up file system watcher
    event_handler = FileHandler(config, analyzer)
    observer = Observer()
    observer.schedule(event_handler, config.drop_dir, recursive=False)
    observer.start()
    
    print(f"\n========================== Magic Folder =========================")
    print(f"Watching: {config.drop_dir}")
    print(f"Organized files: {config.organized_dir}")
    
    # Print active features
    print(f"\nActive Features:")
    print(f"- AI Model: {config.model_name}")
    print(f"- Deduplication: {'Enabled' if config.dedup_enabled else 'Disabled'}")
    print(f"- Content Caching: {'Enabled' if config.enable_content_cache else 'Disabled'}")
    print(f"- User Feedback System: {'Enabled' if config.enable_feedback_system else 'Disabled'}")
    
    if config.enable_feedback_system:
        print(f"  Feedback directory: {config.feedback_dir}")
    
    print(f"\nSupported Categories:")
    for category in config.categories:
        print(f"- {category}")
    
    print(f"\nDrop files into the watch folder to process them.")
    
    # Start web interface if requested
    if args.web:
        try:
            # Import the web interface module
            from magic_folder.web_interface import run_web_interface
            
            # Start the web interface in a separate thread
            print(f"\nStarting web interface on http://{args.host}:{args.port}")
            print(f"Open a browser to this address to access the Magic Folder dashboard")
            
            web_thread = threading.Thread(
                target=run_web_interface,
                args=(config_path,),
                kwargs={'host': args.host, 'port': args.port, 'debug': False}
            )
            web_thread.daemon = True
            web_thread.start()
        except ImportError:
            print("\nWeb interface dependencies not installed.")
            print("Install with: pip install flask")
    
    print(f"Press Ctrl+C to exit.")
    print(f"================================================================\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()
    print("Magic Folder stopped.")

if __name__ == "__main__":
    main()