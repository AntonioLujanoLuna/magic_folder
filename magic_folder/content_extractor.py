"""
Enhanced content extraction from various file types
"""

import os
import io
import re
import platform
import magic
import pickle
import hashlib
import PyPDF2
import docx
import csv
import json
import zipfile
import tarfile
import tempfile
import subprocess
import pandas as pd
from PIL import Image
from xml.etree import ElementTree
from magic_folder.utils import log_activity

# Check for optional dependencies
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None

try:
    import textract
    TEXTRACT_AVAILABLE = True
except ImportError:
    TEXTRACT_AVAILABLE = False
    textract = None

class ContentExtractor:
    """Extracts content from various file types"""
    
    def __init__(self, config):
        """
        Initialize the content extractor
        
        Args:
            config (Config): The application configuration
        """
        self.config = config
        self.sample_length = config.sample_length
        self.ocr_languages = "+".join(config.ocr_languages)
        self.enable_audio = config.enable_audio_analysis
        self.enable_video = config.enable_video_analysis
        self.enable_archives = config.enable_archive_inspection
        
        # Check Tesseract availability
        self.tesseract_available = False
        if TESSERACT_AVAILABLE:
            # Set Tesseract executable path for Windows
            if platform.system() == 'Windows':
                possible_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        log_activity(f"Set Tesseract path to: {path}")
                        break
            
            try:
                # Test if Tesseract is actually executable
                pytesseract.get_tesseract_version()
                self.tesseract_available = True
                log_activity("Tesseract OCR detected and ready")
            except Exception as e:
                log_activity(f"Tesseract OCR not found - OCR features disabled. Error: {e}")
        
        # Initialize content cache
        self.cache_file = os.path.join(config.base_dir, "content_cache.pkl")
        self.content_cache = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load the content extraction cache from disk"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    self.content_cache = pickle.load(f)
                log_activity(f"Loaded content cache with {len(self.content_cache)} entries")
            except Exception as e:
                log_activity(f"Error loading content cache: {e}")
                self.content_cache = {}
    
    def _save_cache(self):
        """Save the content extraction cache to disk"""
        try:
            # Limit cache size to the configured value
            if len(self.content_cache) > self.config.content_cache_size:
                # Remove oldest entries
                keys = list(self.content_cache.keys())
                for k in keys[:-self.config.content_cache_size]:
                    del self.content_cache[k]
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.content_cache, f)
        except Exception as e:
            log_activity(f"Error saving content cache: {e}")
    
    def _calculate_file_hash(self, file_path, chunk_size=8192):
        """
        Calculate a hash of the file for caching purposes
        
        Args:
            file_path (str): Path to the file
            chunk_size (int): Size of chunks to read
            
        Returns:
            str: Hex digest of the file hash
        """
        file_hash = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                # If file is large, only hash beginning and end
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024 * 10:  # 10MB
                    # Read first 1MB
                    data = f.read(1024 * 1024)
                    file_hash.update(data)
                    
                    # Read last 1MB
                    f.seek(-1024 * 1024, os.SEEK_END)
                    data = f.read(1024 * 1024)
                    file_hash.update(data)
                else:
                    # Hash the entire file for smaller files
                    for chunk in iter(lambda: f.read(chunk_size), b""):
                        file_hash.update(chunk)
                        
            return file_hash.hexdigest()
        except Exception as e:
            log_activity(f"Error calculating file hash: {e}")
            return None
    
    def extract_text(self, file_path):
        """
        Extract text content from a file based on its type
        
        Args:
            file_path (str): Path to the file to extract content from
            
        Returns:
            str: Extracted text content
        """
        # Check cache first
        file_hash = self._calculate_file_hash(file_path)
        if file_hash and file_hash in self.content_cache:
            log_activity(f"Using cached content for {os.path.basename(file_path)}")
            return self.content_cache[file_hash]
        
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            content = ""
            # Text files
            if 'text/' in file_type or file_extension in ['.txt', '.md', '.log', '.csv', '.json', '.xml', '.html', '.css', '.js']:
                content = self._extract_from_text(file_path, file_type)
            
            # PDF files
            elif file_type == 'application/pdf' or file_extension == '.pdf':
                content = self._extract_from_pdf(file_path)
            
            # Microsoft Office documents
            elif any(typ in file_type for typ in ['officedocument', 'msword', 'vnd.ms-']) or file_extension in ['.docx', '.doc', '.pptx', '.ppt', '.xlsx', '.xls']:
                content = self._extract_from_office(file_path, file_extension)
            
            # Image files - use OCR
            elif 'image/' in file_type or file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                content = self._extract_from_image(file_path)
            
            # Audio files
            elif ('audio/' in file_type or file_extension in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']) and self.enable_audio:
                content = self._extract_from_audio(file_path)
            
            # Video files
            elif ('video/' in file_type or file_extension in ['.mp4', '.avi', '.mov', '.mkv', '.webm']) and self.enable_video:
                content = self._extract_from_video(file_path)
            
            # Archive files
            elif (('application/zip' in file_type or 'application/x-tar' in file_type or 'application/x-gzip' in file_type) or 
                  file_extension in ['.zip', '.tar', '.gz', '.tgz', '.rar', '.7z']) and self.enable_archives:
                content = self._extract_from_archive(file_path, file_extension)
            
            # eBook formats
            elif file_extension in ['.epub', '.mobi', '.azw', '.azw3']:
                content = self._extract_from_ebook(file_path, file_extension)
            
            # Fallback to textract for other file types
            else:
                if TEXTRACT_AVAILABLE:
                    try:
                        text = textract.process(file_path).decode('utf-8')
                        content = text[:self.sample_length]
                    except Exception as e:
                        log_activity(f"Textract extraction failed: {e}")
                        content = f"Unable to extract content from {os.path.basename(file_path)}. File type: {file_type}"
                else:
                    content = f"Unable to extract content from {os.path.basename(file_path)}. File type: {file_type} (textract not available)"
            
            # Cache the result if we have a valid hash
            if file_hash and content:
                self.content_cache[file_hash] = content
                self._save_cache()
                
            return content
                
        except Exception as e:
            log_activity(f"Error extracting content from {file_path}: {e}")
            error_msg = f"Error extracting content: {str(e)[:100]}..."
            
            # Cache error message too to avoid repeated extraction attempts
            if file_hash:
                self.content_cache[file_hash] = error_msg
                self._save_cache()
                
            return error_msg
    
    def _extract_from_text(self, file_path, file_type):
        """
        Extract from various text-based formats
        
        Args:
            file_path (str): Path to the text file
            file_type (str): MIME type of the file
            
        Returns:
            str: Extracted text content
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        try:
            # JSON files
            if extension == '.json' or 'application/json' in file_type:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    data = json.load(f)
                return json.dumps(data, indent=2)[:self.sample_length]
            
            # XML/HTML files
            elif extension in ['.xml', '.html', '.htm'] or 'xml' in file_type or 'html' in file_type:
                try:
                    tree = ElementTree.parse(file_path)
                    # Get text content (simplified approach)
                    text = ElementTree.tostring(tree.getroot(), encoding='unicode', method='text')
                    return text[:self.sample_length]
                except (ElementTree.ParseError, OSError, UnicodeDecodeError) as e:
                    # Fallback to regular text extraction if parsing fails
                    log_activity(f"XML/HTML parsing failed for {file_path}: {e}")
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read(self.sample_length)
            
            # CSV files
            elif extension == '.csv' or 'text/csv' in file_type:
                return self._extract_from_spreadsheet(file_path)
            
            # Regular text files
            else:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read(self.sample_length)
                    
        except Exception as e:
            log_activity(f"Text extraction error: {e}")
            # Fallback to binary read if text read fails
            try:
                with open(file_path, 'rb') as f:
                    binary_data = f.read(self.sample_length * 2)  # Read more to account for encoding
                    # Try different encodings
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'ascii']:
                        try:
                            return binary_data.decode(encoding)[:self.sample_length]
                        except (UnicodeDecodeError, UnicodeError):
                            continue
                    
                    # If all encodings fail, return hexdump as last resort
                    return f"Binary data: {binary_data.hex()[:100]}..."
            except Exception as e:
                log_activity(f"Binary data extraction error: {e}")
                return ""
    
    def _extract_from_pdf(self, file_path):
        """
        Extract text from PDF files
        
        Args:
            file_path (str): Path to the PDF file
            
        Returns:
            str: Extracted text content
        """
        text = ""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Extract metadata
                info = pdf_reader.metadata
                if info:
                    text += "PDF Metadata:\n"
                    for key in info:
                        if info[key]:
                            text += f"{key}: {info[key]}\n"
                    text += "\n"
                
                # Extract first few pages
                text += "Content:\n"
                for page_num in range(min(5, len(pdf_reader.pages))):  # First 5 pages only
                    page = pdf_reader.pages[page_num]
                    text += f"--- Page {page_num + 1} ---\n"
                    text += page.extract_text() + "\n"
                    if len(text) > self.sample_length:
                        break
            
            # If very little text was extracted, PDF might be scanned
            if len(text.strip()) < 100:
                try:
                    # Try OCR if pdf has few text but has images
                    log_activity(f"PDF may be scanned, attempting OCR")
                    
                    # Convert first page to image using external tools if available
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_image:
                        temp_path = temp_image.name
                    
                    # Try using pdftoppm (from poppler) if available
                    try:
                        subprocess.run(['pdftoppm', '-png', '-singlefile', '-f', '1', '-l', '1', 
                                      file_path, temp_path[:-4]], 
                                      capture_output=True, timeout=30)
                        
                        # Now OCR the resulting image
                        ocr_text = pytesseract.image_to_string(
                            Image.open(f"{temp_path[:-4]}.png"), 
                            lang=self.ocr_languages
                        )
                        text += "\nOCR Results:\n" + ocr_text
                    except Exception as e:
                        log_activity(f"OCR on PDF failed or pdftoppm not available: {e}")
                    
                    # Clean up
                    try:
                        os.unlink(temp_path)
                        os.unlink(f"{temp_path[:-4]}.png")
                    except Exception as e:
                        log_activity(f"Cleanup error: {e}")
                        
                except Exception as e:
                    log_activity(f"PDF OCR error: {e}")
            
            return text[:self.sample_length]
        except Exception as e:
            log_activity(f"PDF extraction error: {e}")
            return ""
    
    def _extract_from_office(self, file_path, extension):
        """
        Extract text from Microsoft Office documents
        
        Args:
            file_path (str): Path to the Office file
            extension (str): File extension
            
        Returns:
            str: Extracted text content
        """
        try:
            # Word documents
            if extension in ['.docx', '.doc']:
                if extension == '.docx':
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    return text[:self.sample_length]
                else:  # .doc format
                    if TEXTRACT_AVAILABLE:
                        try:
                            return textract.process(file_path).decode('utf-8')[:self.sample_length]
                        except Exception as e:
                            log_activity(f"Textract extraction for .doc failed: {e}")
                            return f"DOC file: {os.path.basename(file_path)} (textract extraction failed)"
                    else:
                        return f"DOC file: {os.path.basename(file_path)} (textract not available for .doc files)"
                    
            # Excel files
            elif extension in ['.xlsx', '.xls', '.csv']:
                return self._extract_from_spreadsheet(file_path)
                
            # PowerPoint
            elif extension in ['.pptx', '.ppt']:
                if TEXTRACT_AVAILABLE:
                    try:
                        text = textract.process(file_path).decode('utf-8')
                        return text[:self.sample_length]
                    except Exception as e:
                        log_activity(f"Textract extraction for PowerPoint failed: {e}")
                        return f"PowerPoint file: {os.path.basename(file_path)} (textract extraction failed)"
                else:
                    return f"PowerPoint file: {os.path.basename(file_path)} (textract not available)"
                
            # Other Office formats
            else:
                if TEXTRACT_AVAILABLE:
                    try:
                        text = textract.process(file_path).decode('utf-8')
                        return text[:self.sample_length]
                    except Exception as e:
                        log_activity(f"Textract extraction failed: {e}")
                        return f"Office file: {os.path.basename(file_path)} (textract extraction failed)"
                else:
                    return f"Office file: {os.path.basename(file_path)} (textract not available)"
                
        except Exception as e:
            log_activity(f"Office document extraction error: {e}")
            return ""
    
    def _extract_from_spreadsheet(self, file_path):
        """
        Extract content from spreadsheet files
        
        Args:
            file_path (str): Path to the spreadsheet file
            
        Returns:
            str: Extracted text content
        """
        extension = os.path.splitext(file_path)[1].lower()
        try:
            if extension == '.csv':
                with open(file_path, 'r', newline='', errors='ignore') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    headers = rows[0] if rows else []
                    # Sample the first 10 data rows
                    sample_rows = rows[1:min(11, len(rows))]
                    
                    text = "Headers: " + ", ".join(headers) + "\n"
                    text += "Data Sample:\n"
                    for row in sample_rows:
                        text += " | ".join(row) + "\n"
                    
                    return text[:self.sample_length]
            else:  # Excel files
                # Try to extract sheet names and a sample from each
                text = "Excel File Summary:\n"
                xl = pd.ExcelFile(file_path)
                
                # Get sheet names
                text += f"Sheets: {', '.join(xl.sheet_names)}\n\n"
                
                # Sample from each sheet (up to first 3 sheets)
                for sheet in xl.sheet_names[:3]:
                    text += f"Sheet: {sheet}\n"
                    df = pd.read_excel(file_path, sheet_name=sheet, nrows=5)
                    text += str(df.head()) + "\n\n"
                    
                    if len(text) > self.sample_length:
                        break
                        
                return text[:self.sample_length]
        except Exception as e:
            log_activity(f"Spreadsheet extraction error: {e}")
            return ""
    
    def _extract_from_image(self, file_path):
        """
        Extract text from images using OCR
        
        Args:
            file_path (str): Path to the image file
            
        Returns:
            str: Extracted text content
        """
        try:
            image = Image.open(file_path)
            
            # Get image metadata
            metadata = f"Image Info:\n"
            metadata += f"Format: {image.format}\n"
            metadata += f"Size: {image.width}x{image.height}\n"
            metadata += f"Mode: {image.mode}\n\n"
            
            # Only attempt OCR if Tesseract is available
            if self.tesseract_available:
                try:
                    text = pytesseract.image_to_string(image, lang=self.ocr_languages)
                    return metadata + "OCR Text:\n" + text[:self.sample_length]
                except Exception as e:
                    log_activity(f"OCR failed for {os.path.basename(file_path)}: {str(e)[:50]}")
                    return metadata + "OCR Text: [OCR failed - check logs]"
            else:
                # Don't make it sound like an error - just note the limitation
                return metadata + "[Image content - install Tesseract for text extraction]"
                    
        except Exception as e:
            log_activity(f"Image processing error: {e}")
            return f"Image file: {os.path.basename(file_path)}"
    
    def _extract_from_audio(self, file_path):
        """
        Extract metadata from audio files
        
        Args:
            file_path (str): Path to the audio file
            
        Returns:
            str: Extracted metadata
        """
        try:
            # We'll just extract metadata for audio files since speech-to-text
            # would require additional dependencies
            metadata = f"Audio File: {os.path.basename(file_path)}\n"
            
            # Try to get metadata with ffprobe if available
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                if result.stdout:
                    info = json.loads(result.stdout)
                    
                    # Extract format info
                    if 'format' in info:
                        fmt = info['format']
                        metadata += f"Format: {fmt.get('format_name', 'Unknown')}\n"
                        metadata += f"Duration: {fmt.get('duration', 'Unknown')} seconds\n"
                        metadata += f"Size: {fmt.get('size', 'Unknown')} bytes\n"
                        
                        # Extract tags if present
                        if 'tags' in fmt:
                            tags = fmt['tags']
                            metadata += "\nMetadata Tags:\n"
                            for key, value in tags.items():
                                metadata += f"{key}: {value}\n"
            except:
                # If ffprobe fails, provide basic info
                file_size = os.path.getsize(file_path)
                metadata += f"File size: {file_size} bytes\n"
                metadata += "Audio content could not be transcribed automatically.\n"
            
            return metadata
        except Exception as e:
            log_activity(f"Audio extraction error: {e}")
            return f"Audio file: {os.path.basename(file_path)}"
    
    def _extract_from_video(self, file_path):
        """
        Extract metadata from video files
        
        Args:
            file_path (str): Path to the video file
            
        Returns:
            str: Extracted metadata
        """
        try:
            # Similar to audio, we'll extract metadata for video files
            metadata = f"Video File: {os.path.basename(file_path)}\n"
            
            # Try to get metadata with ffprobe if available
            try:
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                
                if result.stdout:
                    info = json.loads(result.stdout)
                    
                    # Extract format info
                    if 'format' in info:
                        fmt = info['format']
                        metadata += f"Format: {fmt.get('format_name', 'Unknown')}\n"
                        metadata += f"Duration: {fmt.get('duration', 'Unknown')} seconds\n"
                        metadata += f"Size: {fmt.get('size', 'Unknown')} bytes\n"
                    
                    # Extract video stream info
                    if 'streams' in info:
                        for stream in info['streams']:
                            if stream.get('codec_type') == 'video':
                                metadata += f"\nVideo Stream:\n"
                                metadata += f"Codec: {stream.get('codec_name', 'Unknown')}\n"
                                metadata += f"Resolution: {stream.get('width', '?')}x{stream.get('height', '?')}\n"
                                metadata += f"Frame rate: {stream.get('r_frame_rate', 'Unknown')}\n"
                                break
                        
                        # Extract audio stream info
                        for stream in info['streams']:
                            if stream.get('codec_type') == 'audio':
                                metadata += f"\nAudio Stream:\n"
                                metadata += f"Codec: {stream.get('codec_name', 'Unknown')}\n"
                                metadata += f"Channels: {stream.get('channels', 'Unknown')}\n"
                                metadata += f"Sample rate: {stream.get('sample_rate', 'Unknown')} Hz\n"
                                break
                    
                    # Extract tags if present
                    if 'tags' in fmt:
                        tags = fmt['tags']
                        metadata += "\nMetadata Tags:\n"
                        for key, value in tags.items():
                            metadata += f"{key}: {value}\n"
            except Exception as e:
                # If ffprobe fails, provide basic info
                log_activity(f"ffprobe failed for {file_path}: {e}")
                file_size = os.path.getsize(file_path)
                metadata += f"File size: {file_size} bytes\n"
            
            return metadata
        except Exception as e:
            log_activity(f"Video extraction error: {e}")
            return f"Video file: {os.path.basename(file_path)}"
    
    def _extract_from_archive(self, file_path, extension):
        """
        Extract file list and sample content from archive files
        
        Args:
            file_path (str): Path to the archive file
            extension (str): File extension
            
        Returns:
            str: Extracted content
        """
        try:
            result = f"Archive: {os.path.basename(file_path)}\n\n"
            
            # Handle ZIP files
            if extension == '.zip' or zipfile.is_zipfile(file_path):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()
                    
                    # Add file list
                    result += "Files in archive:\n"
                    for i, filename in enumerate(sorted(file_list)[:20]):  # Limit to first 20 files
                        result += f"- {filename}\n"
                    
                    if len(file_list) > 20:
                        result += f"... and {len(file_list) - 20} more files\n"
                    
                    # Try to extract content from a few text files
                    text_files = [f for f in file_list if f.endswith(('.txt', '.md', '.csv', '.json'))][:3]
                    
                    if text_files:
                        result += "\nSample content:\n"
                        for text_file in text_files:
                            result += f"\n--- {text_file} ---\n"
                            with zip_ref.open(text_file) as f:
                                try:
                                    content = f.read(1024).decode('utf-8', errors='ignore')
                                    result += content[:200] + "...\n"
                                except Exception as e:
                                    log_activity(f"Error reading archive file {text_file}: {e}")
                                    result += "[Binary content]\n"
            
            # Handle TAR files (including .tar.gz)
            elif extension in ['.tar', '.tgz', '.gz'] and (tarfile.is_tarfile(file_path) or extension == '.gz'):
                mode = 'r:gz' if extension in ['.tgz', '.gz'] else 'r'
                
                try:
                    with tarfile.open(file_path, mode) as tar:
                        file_list = tar.getnames()
                        
                        # Add file list
                        result += "Files in archive:\n"
                        for i, filename in enumerate(sorted(file_list)[:20]):  # Limit to first 20 files
                            result += f"- {filename}\n"
                        
                        if len(file_list) > 20:
                            result += f"... and {len(file_list) - 20} more files\n"
                        
                        # Try to extract content from a few text files
                        text_files = [f for f in file_list if f.endswith(('.txt', '.md', '.csv', '.json'))][:3]
                        
                        if text_files:
                            result += "\nSample content:\n"
                            for text_file in text_files:
                                result += f"\n--- {text_file} ---\n"
                                try:
                                    with tar.extractfile(text_file) as f:
                                        if f:  # Some tar files have directories listed
                                            content = f.read(1024).decode('utf-8', errors='ignore')
                                            result += content[:200] + "...\n"
                                except Exception as e:
                                    log_activity(f"Error extracting from tar file {text_file}: {e}")
                                    result += "[Could not extract content]\n"
                except Exception as e:
                    log_activity(f"Could not open tar archive {file_path}: {e}")
                    result += "Could not open as tar archive. May be corrupted or unsupported format.\n"
            
            # Handle other archive types (basic info only)
            else:
                result += f"Archive type: {extension}\n"
                result += f"Size: {os.path.getsize(file_path)} bytes\n"
                result += "Content extraction not supported for this archive type.\n"
            
            return result[:self.sample_length]
        except Exception as e:
            log_activity(f"Archive extraction error: {e}")
            return f"Archive file: {os.path.basename(file_path)}"
    
    def _extract_from_ebook(self, file_path, extension):
        """
        Extract content from ebook files
        
        Args:
            file_path (str): Path to the ebook file
            extension (str): File extension
            
        Returns:
            str: Extracted text content
        """
        try:
            # Try to use textract for EPUB files
            if extension == '.epub':
                if TEXTRACT_AVAILABLE:
                    try:
                        text = textract.process(file_path).decode('utf-8')
                        
                        # Extract a reasonable sample
                        if len(text) > 1000:
                            # Get the first ~1000 chars and another sample from the middle
                            beginning = text[:1000]
                            middle = text[len(text)//2:len(text)//2 + 1000]
                            return f"EPUB Content (beginning):\n{beginning}\n\nEPUB Content (middle sample):\n{middle}"
                        else:
                            return text
                    except Exception as e:
                        log_activity(f"Textract extraction for EPUB failed: {e}")
                        return f"EPUB file: {os.path.basename(file_path)} (textract extraction failed)"
                else:
                    return f"EPUB file: {os.path.basename(file_path)} (textract not available)"
            
            # For other ebook formats, try common extraction tools or fallback to basic info
            else:
                if TEXTRACT_AVAILABLE:
                    try:
                        text = textract.process(file_path).decode('utf-8')
                        return text[:self.sample_length]
                    except Exception as e:
                        log_activity(f"Textract extraction for ebook failed: {e}")
                        return f"Ebook file: {os.path.basename(file_path)} (Format: {extension})\nContent extraction not fully supported for this format."
                else:
                    return f"Ebook file: {os.path.basename(file_path)} (Format: {extension})\nTextract not available for ebook extraction."
        except Exception as e:
            log_activity(f"Ebook extraction error: {e}")
            return f"Ebook file: {os.path.basename(file_path)}"