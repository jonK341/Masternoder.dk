"""
Documentary Details Scraper
Gathers useful information from various sources for video generation
"""
import requests
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import quote, urlencode
import time


class DocumentaryScraper:
    """Scrapes and gathers documentary-related data from various sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour
    
    def gather_documentary_data(self, topic: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Gather comprehensive documentary data for a topic
        
        Args:
            topic: Topic/subject for documentary
            max_results: Maximum number of results per source
        
        Returns:
            Dictionary with gathered data from all sources
        """
        data = {
            'topic': topic,
            'timestamp': datetime.utcnow().isoformat(),
            'sources': {},
            'images': [],
            'videos': [],
            'text_content': [],
            'facts': [],
            'quotes': [],
            'statistics': [],
            'timeline': [],
            'related_topics': [],
            'metadata': {}
        }
        
        # Gather from multiple sources
        try:
            # Wikipedia data
            wiki_data = self.scrape_wikipedia(topic)
            if wiki_data:
                data['sources']['wikipedia'] = wiki_data
                data['text_content'].extend(wiki_data.get('sections', []))
                data['facts'].extend(wiki_data.get('facts', []))
                data['related_topics'].extend(wiki_data.get('related_topics', []))
            
            # News articles
            news_data = self.scrape_news(topic, max_results)
            if news_data:
                data['sources']['news'] = news_data
                data['text_content'].extend(news_data.get('articles', []))
            
            # Image search
            images = self.search_images(topic, max_results)
            if images:
                data['images'] = images
            
            # Video references
            videos = self.search_videos(topic, max_results)
            if videos:
                data['videos'] = videos
            
            # Statistics and data
            stats = self.gather_statistics(topic)
            if stats:
                data['statistics'] = stats
            
            # Quotes
            quotes = self.gather_quotes(topic)
            if quotes:
                data['quotes'] = quotes
            
        except Exception as e:
            print(f"[Scraper] Error gathering data: {e}")
            data['error'] = str(e)
        
        return data
    
    def scrape_wikipedia(self, topic: str) -> Optional[Dict[str, Any]]:
        """Scrape Wikipedia for topic information"""
        try:
            # Use Wikipedia API
            url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(topic)
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', topic),
                    'extract': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'thumbnail': data.get('thumbnail', {}).get('source', ''),
                    'sections': [data.get('extract', '')],
                    'facts': self._extract_facts(data.get('extract', '')),
                    'related_topics': []
                }
        except Exception as e:
            print(f"[Scraper] Wikipedia error: {e}")
        
        return None
    
    def scrape_news(self, topic: str, max_results: int = 10) -> Optional[Dict[str, Any]]:
        """Scrape news articles about topic"""
        try:
            # Use NewsAPI or similar (placeholder - would need API key)
            # For now, return structured format
            return {
                'articles': [
                    {
                        'title': f'Latest news about {topic}',
                        'summary': f'Recent developments and information about {topic}',
                        'source': 'news_api',
                        'date': datetime.utcnow().isoformat()
                    }
                ],
                'count': 1
            }
        except Exception as e:
            print(f"[Scraper] News error: {e}")
        
        return None
    
    def search_images(self, topic: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for images related to topic"""
        images = []
        
        try:
            # Use Unsplash API (free, no key needed for basic)
            url = f"https://api.unsplash.com/search/photos"
            params = {
                'query': topic,
                'per_page': min(max_results, 10),
                'client_id': 'YOUR_UNSPLASH_KEY'  # Would need actual key
            }
            
            # For now, return placeholder structure
            for i in range(min(max_results, 5)):
                images.append({
                    'url': f'https://source.unsplash.com/1280x768/?{quote(topic)}',
                    'description': f'Image related to {topic}',
                    'source': 'unsplash',
                    'width': 1280,
                    'height': 768
                })
        except Exception as e:
            print(f"[Scraper] Image search error: {e}")
        
        return images
    
    def search_videos(self, topic: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for video references related to topic"""
        videos = []
        
        try:
            # Placeholder for video search (YouTube API would require key)
            videos.append({
                'title': f'Documentary about {topic}',
                'description': f'Video content related to {topic}',
                'source': 'youtube',
                'duration': 0,
                'thumbnail': ''
            })
        except Exception as e:
            print(f"[Scraper] Video search error: {e}")
        
        return videos
    
    def gather_statistics(self, topic: str) -> List[Dict[str, Any]]:
        """Gather statistics and data about topic"""
        stats = []
        
        try:
            # Extract numerical data from gathered content
            # This would be enhanced with actual data sources
            stats.append({
                'label': 'Relevance Score',
                'value': 85,
                'unit': '%',
                'source': 'calculated'
            })
        except Exception as e:
            print(f"[Scraper] Statistics error: {e}")
        
        return stats
    
    def gather_quotes(self, topic: str) -> List[Dict[str, Any]]:
        """Gather relevant quotes about topic"""
        quotes = []
        
        try:
            # Placeholder for quote gathering
            quotes.append({
                'text': f'"{topic}" is an important subject worth exploring.',
                'author': 'Expert',
                'source': 'generated'
            })
        except Exception as e:
            print(f"[Scraper] Quotes error: {e}")
        
        return quotes
    
    def _extract_facts(self, text: str) -> List[str]:
        """Extract facts from text content"""
        facts = []
        
        # Simple fact extraction (can be enhanced with NLP)
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                # Look for factual statements
                if any(word in sentence.lower() for word in ['is', 'was', 'are', 'were', 'has', 'have']):
                    facts.append(sentence)
        
        return facts[:10]  # Return top 10 facts


# Global instance
documentary_scraper = DocumentaryScraper()

