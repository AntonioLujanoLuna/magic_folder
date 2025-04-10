"""
AI analysis module for categorizing and naming files
"""

import os
import re
import pickle
from datetime import datetime
import numpy as np
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
from magic_folder.utils import log_activity

class AIAnalyzer:
    """Uses embeddings to analyze file content and determine categories and naming"""
    
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
        self.embedding_model = None
        self.category_embeddings = {}
        self.cache_file = os.path.join(config.base_dir, "embeddings_cache.pkl")
        self.content_cache = {}
        self.initialize_model()
        
    def initialize_model(self):
        """Initialize the embedding model"""
        try:
            # Try to use sentence-transformers for better embeddings
            try:
                self.embedding_model = SentenceTransformer(self.model_name)
                log_activity("Using SentenceTransformer model for embeddings")
            except:
                # Fallback to regular transformer model
                self.embedding_model = AutoModel.from_pretrained(self.model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                log_activity("Using AutoModel for embeddings")
            
            # Load cached embeddings if available
            self._load_cached_embeddings()
            
            # Generate category embeddings
            self._generate_category_embeddings()
            
            log_activity("AI model initialized successfully")
        except Exception as e:
            log_activity(f"Error initializing AI model: {e}")
            self.embedding_model = None
            
    def _load_cached_embeddings(self):
        """Load cached embeddings from disk"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.category_embeddings = cache_data.get('category_embeddings', {})
                    self.content_cache = cache_data.get('content_cache', {})
                    log_activity(f"Loaded {len(self.content_cache)} cached embeddings")
            except Exception as e:
                log_activity(f"Error loading embeddings cache: {e}")
                
    def _save_cached_embeddings(self):
        """Save cached embeddings to disk"""
        try:
            # Limit cache size to configured value
            if len(self.content_cache) > self.config.embedding_cache_size:
                # Keep only the most recent items
                keys = list(self.content_cache.keys())
                for key in keys[:-self.config.embedding_cache_size]:
                    del self.content_cache[key]
                    
            cache_data = {
                'category_embeddings': self.category_embeddings,
                'content_cache': self.content_cache
            }
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            log_activity(f"Error saving embeddings cache: {e}")
    
    def _generate_category_embeddings(self):
        """Generate embeddings for each category based on keywords"""
        if self.embedding_model is None:
            return
            
        # Only generate if we don't have them cached
        if not self.category_embeddings or len(self.category_embeddings) != len(self.categories):
            log_activity("Generating category embeddings")
            
            # Get the category keywords from configuration
            if not self.category_keywords:
                # If not in config, set up defaults
                self._setup_default_keywords()
                
            # Generate embeddings for each category
            for category in self.categories:
                if category in self.category_keywords:
                    keywords = self.category_keywords[category]
                    # Only generate if needed
                    if category not in self.category_embeddings and keywords:
                        # Create a descriptive text for the category
                        category_text = f"{category}: " + ", ".join(keywords)
                        
                        # Generate embedding
                        try:
                            if hasattr(self.embedding_model, 'encode'):
                                # SentenceTransformer approach
                                embedding = self.embedding_model.encode(category_text)
                            else:
                                # Manual approach with AutoModel
                                inputs = self.tokenizer(category_text, return_tensors="pt", padding=True, truncation=True)
                                outputs = self.embedding_model(**inputs)
                                embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()[0]
                                
                            self.category_embeddings[category] = embedding
                        except Exception as e:
                            log_activity(f"Error generating embedding for {category}: {e}")
            
            # Save the generated embeddings
            self._save_cached_embeddings()
        
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
        
        # Check if we already have this content analyzed in cache
        content_hash = hash(content[:1000])  # Use first 1000 chars to create a hash
        if content_hash in self.content_cache:
            return self.content_cache[content_hash]
            
        # First attempt with embedding model if available
        best_category = "other"
        
        if self.embedding_model is not None and self.category_embeddings:
            try:
                # Create embedding for content
                if hasattr(self.embedding_model, 'encode'):
                    content_embedding = self.embedding_model.encode(content[:5000])  # Limit to first 5000 chars
                else:
                    # Manual approach with AutoModel
                    inputs = self.tokenizer(content[:5000], return_tensors="pt", padding=True, truncation=True)
                    outputs = self.embedding_model(**inputs)
                    content_embedding = outputs.last_hidden_state.mean(dim=1).detach().numpy()[0]
                
                # Calculate similarity to each category
                similarities = {}
                for category, category_embedding in self.category_embeddings.items():
                    similarity = np.dot(content_embedding, category_embedding) / (
                        np.linalg.norm(content_embedding) * np.linalg.norm(category_embedding)
                    )
                    similarities[category] = similarity
                
                # Find the best matching category
                best_category, highest_similarity = max(similarities.items(), key=lambda x: x[1])
                
                # If similarity is too low, fallback to keyword approach
                if highest_similarity < self.config.embedding_similarity_threshold:
                    log_activity(f"Low similarity ({highest_similarity:.2f}), falling back to keyword matching")
                    best_category = self._keyword_matching(content)
            except Exception as e:
                log_activity(f"Error using embeddings for classification: {e}")
                best_category = self._keyword_matching(content)
        else:
            # Fallback to keyword matching
            best_category = self._keyword_matching(content)
            
        # Generate a descriptive name based on content
        clean_title = self._extract_title_from_content(content)
        
        if not clean_title:
            # If still no good title, use category and date
            date_str = datetime.now().strftime('%Y%m%d')
            clean_title = f"{best_category}_{date_str}"
        
        # Add date for uniqueness
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(file_path)
        extension = os.path.splitext(filename)[1].lower()
        new_name = f"{clean_title[:30]}_{timestamp}{extension}"
        
        # Save result to cache
        result = (best_category, new_name)
        self.content_cache[content_hash] = result
        self._save_cached_embeddings()
        
        return result
    
    def _keyword_matching(self, content):
        """
        Perform keyword matching to find the best category
        
        Args:
            content (str): The text content
            
        Returns:
            str: The best matching category
        """
        content_lower = content.lower()
        
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
                    if keyword.lower() in content_lower:
                        category_matches[category] += 1
        
        # Determine the best category
        best_category = max(category_matches.items(), key=lambda x: x[1])
        
        # If no matches found, use "other" category
        if best_category[1] == 0:
            best_category = ("other", 0)
            
        return best_category[0]
    
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
            "taxes": ["tax", "taxes", "irs", "return", "w-2", "w2", "1099", "deduction", "income tax", "tax form", "tax return"],
            "receipts": ["receipt", "purchase", "order", "transaction", "payment", "invoice", "paid", "amount", "total", "subtotal"],
            "personal_id": ["passport", "license", "id", "identification", "birth", "certificate", "ssn", "social security", "driver license"],
            "medical": ["medical", "health", "doctor", "prescription", "hospital", "insurance", "patient", "diagnosis", "treatment", "healthcare"],
            "work": ["work", "job", "employment", "resume", "cv", "career", "position", "salary", "employer", "employee", "contract"],
            "education": ["education", "school", "university", "college", "degree", "transcript", "diploma", "course", "student", "grade", "academic"],
            "financial": ["bank", "statement", "account", "finance", "investment", "stock", "dividend", "saving", "financial", "credit card", "transaction"],
            "legal": ["legal", "contract", "agreement", "law", "attorney", "court", "case", "will", "estate", "lawsuit", "plaintiff", "defendant"],
            "correspondence": ["letter", "email", "correspondence", "memo", "communication", "sincerely", "regards", "dear", "hello", "greetings"],
            "other": []  # Fallback category
        }