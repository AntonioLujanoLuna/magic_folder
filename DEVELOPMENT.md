# Magic Folder - Development Setup

This guide explains how to set up the Magic Folder development environment.

## Prerequisites

- Python 3.8 or higher
- Git

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/AntonioLujanoLuna/magic_folder.git
cd magic_folder
```

### 2. Create a Virtual Environment

**Windows:**
```powershell
python -m venv magic_folder_env
magic_folder_env\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv magic_folder_env
source magic_folder_env/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -e .
```

This will install the package in development mode along with all required dependencies.

## What Was Fixed

The repository had several critical issues that have been resolved:

### 1. **Package Configuration Issues**
- Fixed `setup.py` to properly include config files and templates
- Updated `MANIFEST.in` to ensure all package data is included
- Moved default config file to the correct location within the package

### 2. **Dependency Management**
- Removed problematic `textract` dependency that had invalid metadata
- Added proper error handling for missing optional dependencies (Tesseract, textract)
- Added Flask and APScheduler to requirements for web interface

### 3. **Web Interface Fixes**
- Fixed missing log file initialization in web interface
- Removed broken feedback route that referenced missing template
- Created missing `categories.html` template
- Improved file move functionality with proper error handling

### 4. **Error Handling Improvements**
- Added comprehensive error handling for missing Tesseract OCR
- Added fallback mechanisms when AI models fail to download
- Improved cross-platform compatibility
- Added proper handling for network connection issues

### 5. **Import Fixes**
- Fixed deprecated `pkg_resources` usage with modern `importlib.resources`
- Added proper optional dependency checking for transformers and sentence-transformers

## Usage

### Command Line Interface

```bash
# Basic usage
magic-folder

# With custom config
magic-folder --config path/to/config.json

# Start web interface
magic-folder --web --host 0.0.0.0 --port 5000

# View help
magic-folder --help
```

### Web Interface

To start the web interface:

```bash
magic-folder --web
```

Then open http://localhost:5000 in your browser.

## Configuration

The default configuration is located at `magic_folder/config/default_config.json`. You can:

1. Copy it to create a custom configuration
2. Modify settings through the web interface
3. Pass a custom config file via `--config` parameter

## Development Notes

- The package is installed in development mode (`-e .`) so changes to code are immediately reflected
- Virtual environment isolates dependencies from system Python
- All critical issues identified in the repository have been addressed
- The application now gracefully handles missing optional dependencies

## Testing

To test the fixed functionality:

1. Install the package as described above
2. Run `magic-folder --help` to verify CLI works
3. Start the web interface with `magic-folder --web`
4. Drop some test files to verify file processing works

## Architecture

- `magic_folder/analyzer.py` - AI-powered file categorization
- `magic_folder/content_extractor.py` - Text extraction from various file types
- `magic_folder/web_interface.py` - Flask-based web interface
- `magic_folder/config.py` - Configuration management
- `magic_folder/file_handler.py` - File system monitoring and processing

The application is now stable and ready for development or deployment. 