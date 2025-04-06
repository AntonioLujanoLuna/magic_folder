# Magic Folder

A local AI-powered file organization system that automatically categorizes and renames files based on their content.

## 🎉 New Features

- **Embedding-based Classification**: Enhanced AI analysis using state-of-the-art embedding comparison
- **User Feedback System**: Train the system through corrections for better categorization over time
- **Performance Optimization**: Content and embedding caching to speed up processing
- **Improved Configuration**: Extensive configuration options for fine-tuning
- **Web Interface**: Modern dashboard for file management and visualization
- **Smart Installer**: Dependency checking and guided installation

## Features

- **Smart Categorization**: Uses a lightweight local AI model to categorize files based on their content
- **Content Analysis**: Extracts text from various file types (PDFs, images via OCR, documents, spreadsheets)
- **Automatic Organization**: Moves files to appropriate category folders
- **Descriptive Naming**: Generates meaningful names based on file content
- **Low Resource Usage**: Uses a small LLM model suitable for local execution
- **Content Caching**: Avoids reprocessing similar files for better performance

## Installation

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR (for image processing)

### Easy Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/magic_folder.git
cd magic_folder

# Run the installer script
python install.py
```

The installer will check for dependencies and guide you through the setup process.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/magic_folder.git
cd magic_folder

# Install the package
pip install -e .
```

### Installing Tesseract OCR

#### macOS
```bash
brew install tesseract
```

#### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr
```

#### Windows
Download and install from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

## Usage

### Command-Line Options

```bash
# Start with default configuration
magic-folder

# Use a custom configuration file
magic-folder --config /path/to/your/config.json

# Override base directory
magic-folder --base-dir ~/Documents/my_magic_folder

# Use a different AI model
magic-folder --model distilroberta-base

# Enable or disable feedback system
magic-folder --feedback     # Enable
magic-folder --no-feedback  # Disable

# Enable or disable caching
magic-folder --cache        # Enable
magic-folder --no-cache     # Disable

# Start the web interface
magic-folder --web --port 5000 --host 127.0.0.1
```

### Web Interface

Magic Folder now includes a modern web interface for managing your files:

```bash
# Start Magic Folder with the web interface
magic-folder --web
```

Then open `http://127.0.0.1:5000` in your browser to access the dashboard.

The web interface provides:
- File statistics and visualization
- Easy file uploading and management
- Category management
- File recategorization with feedback
- Daily and weekly reports

## Configuration

Magic Folder can be customized by creating a configuration file. See `config/example_config.json` for a detailed example with comments.

### Default Categories

- taxes
- receipts
- personal_id
- medical
- work
- education
- financial
- legal
- correspondence
- other

### Creating a Custom Configuration

1. Copy the example configuration file:
   ```bash
   cp config/example_config.json ~/my_config.json
   ```

2. Modify the file to suit your needs:
   - Add or remove categories
   - Customize the keywords for each category
   - Change the base directory settings
   - Adjust processing options

3. Run Magic Folder with your custom configuration:
   ```bash
   magic-folder --config ~/my_config.json
   ```

## How It Works

1. Magic Folder watches a designated "drop" folder for new files
2. When a file is detected, it extracts text content using appropriate methods
3. The AI analyzer categorizes the file based on content
4. The file is renamed with a descriptive name and moved to the appropriate category folder

## User Feedback System

Magic Folder now includes a feedback mechanism to improve categorization over time:

1. Processed files are made available in the `feedback/recent` directory
2. To correct a miscategorized file, move it from `recent` to the appropriate category folder under `feedback/`
3. The system will:
   - Move the file to the correct category in your organized folders
   - Learn from your correction to improve future categorizations
   - Update keywords and content patterns for that category

For example, if "invoice.pdf" was incorrectly categorized as "work" but should be "financial":
- Find `work--invoice_20230615_123045.pdf` in `feedback/recent`
- Move it to `feedback/financial/`
- Magic Folder will automatically recategorize it and improve its model

## Performance Optimizations

- **Content Caching**: Magic Folder now caches extracted content to avoid reprocessing similar files
- **Embedding-based Analysis**: Uses advanced embedding comparison for more accurate categorization
- **Adaptive Learning**: Improves categorization accuracy based on your feedback

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.