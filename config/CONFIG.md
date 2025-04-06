# Magic Folder Configuration Guide

This document explains all the configuration options available in Magic Folder's configuration files. 

## Basic Configuration

| Option | Type | Description |
|--------|------|-------------|
| `base_dir` | String | Base directory where all Magic Folder data will be stored |
| `drop_dir` | String | Directory name where files are dropped for processing |
| `organized_dir` | String | Directory name where organized files will be placed |
| `log_file` | String | Name of the log file |

## Model Configuration

| Option | Type | Description |
|--------|------|-------------|
| `model.name` | String | Name of the Hugging Face model to use for text analysis |
| `model.sample_length` | Integer | Maximum text sample length to analyze (characters) |

## Categories

The `categories` array defines the categories used for organizing files. You can customize this list to match your organizational needs. Each category will become a folder in your organized directory.

## Category Keywords

The `category_keywords` object maps each category to an array of keywords that help identify files belonging to that category. For example:

```json
"category_keywords": {
    "invoices": ["invoice", "bill", "payment due", "net 30", "order number"],
    "receipts": ["receipt", "purchase", "order confirmation"]
}
```

Files containing these keywords will be more likely to be categorized accordingly.

## File Exclusion

| Option | Type | Description |
|--------|------|-------------|
| `excluded_extensions` | Array | File extensions to ignore |
| `excluded_files` | Array | Specific filenames to ignore |

## Processing Settings

| Option | Type | Description |
|--------|------|-------------|
| `processing.delay_seconds` | Number | Time to wait after a file appears before processing it |
| `processing.check_interval` | Number | Interval (seconds) for checking the processing queue |

## Deduplication

| Option | Type | Description |
|--------|------|-------------|
| `deduplication.enabled` | Boolean | Enable file deduplication detection |
| `deduplication.hash_method` | String | Hash algorithm: "md5", "sha1", or "sha256" |
| `deduplication.action` | String | Action for duplicates: "skip", "move", or "process" |

## Advanced File Type Settings

| Option | Type | Description |
|--------|------|-------------|
| `advanced_file_types.enable_audio_analysis` | Boolean | Extract metadata from audio files |
| `advanced_file_types.enable_video_analysis` | Boolean | Extract metadata from video files |
| `advanced_file_types.enable_archive_inspection` | Boolean | Look inside archives (zip, tar, etc.) |
| `advanced_file_types.ocr_languages` | Array | Languages for OCR (Tesseract language codes) |

## Performance Optimization

| Option | Type | Description |
|--------|------|-------------|
| `performance.enable_content_cache` | Boolean | Cache extracted content to avoid reprocessing |
| `performance.content_cache_size` | Integer | Maximum number of items in content cache |
| `performance.enable_embedding_cache` | Boolean | Cache embeddings for faster categorization |
| `performance.embedding_cache_size` | Integer | Maximum number of items in embedding cache |

## User Feedback System

| Option | Type | Description |
|--------|------|-------------|
| `feedback.enable_feedback_system` | Boolean | Enable the user feedback system |
| `feedback.feedback_dir_name` | String | Directory name for feedback files |
| `feedback.embedding_similarity_threshold` | Number | Threshold for similarity matching (0.0-1.0) |

## Example Configuration

See `example_config.json` for a complete example configuration file. 