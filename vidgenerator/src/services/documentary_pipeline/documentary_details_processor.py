"""
Documentary Details Processor
Processes gathered data and integrates with generation pipeline
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.services.data_gathering.documentary_scraper import documentary_scraper
from src.services.data_gathering.api_wrappers import data_gatherer


class DocumentaryDetailsProcessor:
    """Processes documentary details and prepares for generation"""
    
    def __init__(self):
        self.scraper = documentary_scraper
        self.data_gatherer = data_gatherer
    
    def process_documentary_request(self, prompt: str, title: str = None, 
                                   user_id: str = None) -> Dict[str, Any]:
        """
        Process documentary generation request with data gathering
        
        Args:
            prompt: User's prompt
            title: Optional title
            user_id: User identifier
        
        Returns:
            Processed documentary details ready for generation
        """
        # Extract topic from prompt
        topic = self._extract_topic(prompt, title)
        
        # Gather data from all sources
        print(f"[Processor] Gathering data for topic: {topic}")
        gathered_data = self.data_gatherer.gather_all_data(topic, max_results=10)
        
        # Process and structure data
        processed_data = {
            'original_prompt': prompt,
            'title': title or gathered_data.get('summary', {}).get('title', topic),
            'topic': topic,
            'gathered_data': gathered_data,
            'enhanced_prompt': self._enhance_prompt(prompt, gathered_data),
            'images': self._process_images(gathered_data.get('images', [])),
            'text_content': self._process_text_content(gathered_data),
            'metadata': {
                'sources': list(gathered_data.keys()),
                'data_quality': self._assess_data_quality(gathered_data),
                'timestamp': datetime.utcnow().isoformat()
            },
            'generation_hints': self._generate_hints(gathered_data)
        }
        
        return processed_data
    
    def _extract_topic(self, prompt: str, title: str = None) -> str:
        """Extract main topic from prompt"""
        if title:
            return title
        
        # Simple topic extraction (can be enhanced with NLP)
        # Remove common words and take first meaningful phrase
        words = prompt.split()
        stop_words = {'a', 'an', 'the', 'about', 'documentary', 'video', 'create', 'make'}
        meaningful_words = [w for w in words if w.lower() not in stop_words]
        
        if meaningful_words:
            # Take first 3-5 words as topic
            topic = ' '.join(meaningful_words[:5])
            return topic
        
        return prompt[:50]  # Fallback to first 50 chars
    
    def _enhance_prompt(self, original_prompt: str, gathered_data: Dict) -> str:
        """Enhance prompt with gathered data"""
        enhanced = original_prompt
        
        # Add Wikipedia summary if available
        if gathered_data.get('wikipedia'):
            wiki_extract = gathered_data['wikipedia'].get('extract', '')
            if wiki_extract:
                # Add key information from Wikipedia
                summary_snippet = wiki_extract[:200]  # First 200 chars
                enhanced += f". Context: {summary_snippet}"
        
        # Add news context if available
        if gathered_data.get('news'):
            news_count = len(gathered_data['news'])
            if news_count > 0:
                enhanced += f". Recent news coverage available ({news_count} articles)"
        
        return enhanced
    
    def _process_images(self, images: List[Dict]) -> List[Dict[str, Any]]:
        """Process and format images for generation"""
        processed = []
        
        for img in images[:10]:  # Limit to 10 images
            processed.append({
                'url': img.get('url', ''),
                'thumbnail': img.get('thumb', img.get('url', '')),
                'description': img.get('description', ''),
                'width': img.get('width', 1280),
                'height': img.get('height', 768),
                'source': img.get('source', 'unknown')
            })
        
        return processed
    
    def _process_text_content(self, gathered_data: Dict) -> List[Dict[str, Any]]:
        """Process text content for generation"""
        content = []
        
        # Wikipedia content
        if gathered_data.get('wikipedia'):
            wiki = gathered_data['wikipedia']
            content.append({
                'type': 'wikipedia',
                'title': wiki.get('title', ''),
                'text': wiki.get('extract', ''),
                'url': wiki.get('url', ''),
                'source': 'wikipedia'
            })
        
        # News articles
        for article in gathered_data.get('news', [])[:5]:  # Top 5 articles
            content.append({
                'type': 'news',
                'title': article.get('title', ''),
                'text': article.get('description', '') or article.get('content', ''),
                'url': article.get('url', ''),
                'source': article.get('source', ''),
                'date': article.get('published_at', '')
            })
        
        return content
    
    def _assess_data_quality(self, gathered_data: Dict) -> Dict[str, Any]:
        """Assess quality of gathered data"""
        quality_score = 0.0
        factors = {}
        
        # Wikipedia presence
        if gathered_data.get('wikipedia'):
            quality_score += 0.3
            factors['wikipedia'] = True
        
        # Images available
        image_count = len(gathered_data.get('images', []))
        if image_count > 0:
            quality_score += min(0.2, image_count * 0.02)
            factors['images'] = image_count
        
        # News articles
        news_count = len(gathered_data.get('news', []))
        if news_count > 0:
            quality_score += min(0.2, news_count * 0.02)
            factors['news'] = news_count
        
        # Videos
        video_count = len(gathered_data.get('videos', []))
        if video_count > 0:
            quality_score += min(0.1, video_count * 0.01)
            factors['videos'] = video_count
        
        # Text content
        wikipedia = gathered_data.get('wikipedia')
        if wikipedia and isinstance(wikipedia, dict):
            text_count = len(wikipedia.get('extract', ''))
            if text_count > 100:
                quality_score += 0.2
                factors['text_content'] = text_count
        
        return {
            'score': min(1.0, quality_score),
            'factors': factors,
            'rating': 'excellent' if quality_score >= 0.7 else 'good' if quality_score >= 0.4 else 'fair'
        }
    
    def _generate_hints(self, gathered_data: Dict) -> Dict[str, Any]:
        """Generate hints for video generation"""
        hints = {
            'suggested_duration': 300,  # Default 5 min
            'suggested_clip_count': 20,
            'style_suggestions': [],
            'content_suggestions': []
        }
        
        # Adjust based on data availability
        if gathered_data.get('wikipedia'):
            hints['content_suggestions'].append('Include factual information')
        
        if len(gathered_data.get('images', [])) > 5:
            hints['style_suggestions'].append('Rich visual content available')
            hints['suggested_clip_count'] = 25
        
        if len(gathered_data.get('news', [])) > 3:
            hints['content_suggestions'].append('Include recent developments')
            hints['suggested_duration'] = 400  # Longer for news content
        
        return hints


# Global instance
documentary_processor = DocumentaryDetailsProcessor()

