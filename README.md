# Magic Folder

A local AI-powered file organization system that automatically categorizes and renames files based on their content.

## Features

- **Smart Categorization**: Uses a lightweight local AI model to categorize files based on their content
- **Content Analysis**: Extracts text from various file types (PDFs, images via OCR, documents, spreadsheets)
- **Automatic Organization**: Moves files to appropriate category folders
- **Descriptive Naming**: Generates meaningful names based on file content
- **Low Resource Usage**: Uses a small LLM model suitable for local execution

## Installation

### Prerequisites

- Python 3.8 or higher
- Tesseract OCR (for image processing)

### Install from source

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

### Basic Usage

```bash
# Start with default configuration
magic-folder
```

### Custom Configuration

```bash
# Use a custom configuration file
magic-folder --config /path/to/your/config.json

# Override base directory
magic-folder --base-dir ~/Documents/my_magic_folder

# Use a different AI model
magic-folder --model distilroberta-base
```

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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.