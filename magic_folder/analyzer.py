"""
AI analysis module for categorizing and naming files
"""

import os
import re
from datetime import datetime
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from magic_folder.utils import log_activity

class AIAnalyzer:
    """Uses local LLM to analyze file content and determine categories and naming"""
    
    def __init__(self, config):
        """
        Initialize the AI analyzer
        
        Args:
            config (Config): The application configuration
        """
        self.config = config
        self.model_name = config.model_name
        self.categories = config.categories
        self.category_keywords = config.category_keywords
        self.tokenizer = None
        self.model = None
        self.nlp = None
        self.initialize_model()
        
    def initialize_model(self):
        """Initialize the text classification pipeline"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            # Fine-tuning or zero-shot would be ideal, but for simplicity we're using a text classification approach
            self.nlp = pipeline("text-classification", model=self.model, tokenizer=self.tokenizer)
            log_activity("AI model initialized successfully")
        except Exception as e:
            log_activity(f"Error initializing AI model: {e}")
            
    def analyze_content(self, content, file_path):
        """
        Analyze file content to determine category and suitable name
        
        Args:
            content (str): The extracted text content from the file
            file_path (str): Path to the original file
            
        Returns:
            tuple: (category, new_name) for the file
        """
        if not content:
            # If no content could be extracted, use filename and extension as fallback
            filename = os.path.basename(file_path)
            extension = os.path.splitext(filename)[1].lower()
            return "other", f"unprocessed_{datetime.now().strftime('%Y%m%d_%H%M%S')}{extension}"
        
        # This is where a custom fine-tuned model would be better
        # For now, we'll implement a rule-based system with some NLP assistance
        
        content_lower = content.lower()
        filename = os.path.basename(file_path)
        extension = os.path.splitext(filename)[1].lower()
        
        # Simple keyword matching for categories
        category_matches = {category: 0 for category in self.categories}
        
        # Get the category keywords from configuration
        if not self.category_keywords:
            # If not in config, set up defaults
            self._setup_default_keywords()
        
        # Count keyword matches
        for category, keywords in self.category_keywords.items():
            if category in self.categories:  # Only match categories we're using
                for keyword in keywords:
                    if keyword in content_lower:
                        category_matches[category] += 1
        
        # Determine the best category
        best_category = max(category_matches.items(), key=lambda x: x[1])
        
        # If no matches found, use "other" category
        if best_category[1] == 0:
            best_category = ("other", 0)
            
        # Generate a descriptive name based on content
        # Extract potential title from first line or significant text
        clean_title = self._extract_title_from_content(content)
        
        if not clean_title:
            # If still no good title, use category and date
            date_str = datetime.now().strftime('%Y%m%d')
            clean_title = f"{best_category[0]}_{date_str}"
        
        # Add date for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_name = f"{clean_title[:30]}_{timestamp}{extension}"
        
        return best_category[0], new_name
    
    def _extract_title_from_content(self, content):
        """
        Extract a potential title from content
        
        Args:
            content (str): The text content
            
        Returns:
            str: A cleaned potential title
        """
        lines = content.split('\n')
        potential_title = lines[0] if lines else ""
        
        if len(potential_title) < 5 or len(potential_title) > 50:
            # Look for a better title candidate in the first few lines
            for line in lines[1:5]:
                if 5 <= len(line) <= 50 and not line.startswith('http'):
                    potential_title = line
                    break
        
        # Clean up the title
        clean_title = re.sub(r'[^\w\s-]', '', potential_title).strip()
        clean_title = re.sub(r'\s+', '_', clean_title)
        
        return clean_title
    
    def _setup_default_keywords(self):
        """Set up default keywords for categories if not provided in config"""
        self.category_keywords = {
            "taxes": ["tax", "taxes", "irs", "return", "w-2", "w2", "1099", "deduction"],
            "receipts": ["receipt", "purchase", "order", "transaction", "payment"],
            "personal_id": ["passport", "license", "id", "identification", "birth", "certificate", "ssn"],
            "medical": ["medical", "health", "doctor", "prescription", "hospital", "insurance"],
            "work": ["work", "job", "employment", "resume", "cv", "career", "position", "salary"],
            "education": ["education", "school", "university", "college", "degree", "transcript", "diploma"],
            "financial": ["bank", "statement", "account", "finance", "investment", "stock", "dividend", "saving"],
            "legal": ["legal", "contract", "agreement", "law", "attorney", "court", "case", "will", "estate"],
            "correspondence": ["letter", "email", "correspondence", "memo", "communication"],
            "other": []  # Fallback category
        }