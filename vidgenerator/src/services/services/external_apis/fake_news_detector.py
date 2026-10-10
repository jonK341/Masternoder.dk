"""
Fake News Detector - Open Source Model Integration
Uses BERT-based models for fake news detection
"""

import os
from typing import Dict, Optional
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class FakeNewsDetector:
    """Service for detecting fake news using open source models"""
    
    def __init__(self, model_name: str = "mrm8488/bert-small-finetuned-news-fake-detection"):
        """
        Initialize Fake News Detector
        
        Args:
            model_name: HuggingFace model name for fake news detection
        """
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.initialized = False
        
        if TRANSFORMERS_AVAILABLE:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the fake news detection model"""
        if not TRANSFORMERS_AVAILABLE:
            print("⚠️ Transformers library not installed. Run: pip install transformers torch")
            return
        
        try:
            print(f"Loading fake news detection model: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.pipeline = pipeline(
                "text-classification",
                model=self.model,
                tokenizer=self.tokenizer
            )
            self.initialized = True
            print("✓ Fake news detection model loaded")
        except Exception as e:
            print(f"⚠️ Failed to load model: {e}")
            print("  Using fallback method")
    
    def detect(self, text: str) -> Dict:
        """
        Detect if text is fake news
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with detection results:
            {
                'is_fake': bool,
                'confidence': float,
                'label': str
            }
        """
        if not self.initialized:
            return {
                'is_fake': False,
                'confidence': 0.0,
                'label': 'unknown',
                'error': 'Model not initialized'
            }
        
        try:
            result = self.pipeline(text)
            
            # Parse result
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            label = result.get('label', 'UNKNOWN').lower()
            score = result.get('score', 0.0)
            
            is_fake = 'fake' in label or 'false' in label
            
            return {
                'is_fake': is_fake,
                'confidence': score,
                'label': label,
                'raw_result': result
            }
        except Exception as e:
            return {
                'is_fake': False,
                'confidence': 0.0,
                'label': 'error',
                'error': str(e)
            }
    
    def batch_detect(self, texts: list) -> list:
        """Detect fake news for multiple texts"""
        return [self.detect(text) for text in texts]

