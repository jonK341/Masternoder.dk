"""
API Wrappers for Data Gathering
Wraps various APIs for gathering documentary data
"""
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import os


class WikipediaWrapper:
    """Wrapper for Wikipedia API"""
    
    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1"
        self.session = requests.Session()
    
    def get_summary(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get Wikipedia summary for topic"""
        try:
            url = f"{self.base_url}/page/summary/{topic.replace(' ', '_')}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'title': data.get('title', ''),
                    'extract': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'thumbnail': data.get('thumbnail', {}).get('source', ''),
                    'timestamp': datetime.utcnow().isoformat()
                }
        except Exception as e:
            print(f"[Wikipedia] Error: {e}")
        
        return None
    
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search Wikipedia"""
        try:
            url = f"{self.base_url}/page/search/{query}"
            params = {'limit': limit}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('pages', [])
        except Exception as e:
            print(f"[Wikipedia] Search error: {e}")
        
        return []


class UnsplashWrapper:
    """Wrapper for Unsplash API (images)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('UNSPLASH_API_KEY', '')
        self.base_url = "https://api.unsplash.com"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'Authorization': f'Client-ID {self.api_key}'})
    
    def search_photos(self, query: str, per_page: int = 10) -> List[Dict[str, Any]]:
        """Search for photos"""
        try:
            url = f"{self.base_url}/search/photos"
            params = {'query': query, 'per_page': per_page}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for photo in data.get('results', []):
                    results.append({
                        'id': photo.get('id', ''),
                        'url': photo.get('urls', {}).get('regular', ''),
                        'thumb': photo.get('urls', {}).get('thumb', ''),
                        'description': photo.get('description', ''),
                        'width': photo.get('width', 0),
                        'height': photo.get('height', 0),
                        'author': photo.get('user', {}).get('name', ''),
                        'source': 'unsplash'
                    })
                return results
        except Exception as e:
            print(f"[Unsplash] Error: {e}")
        
        return []


class NewsAPIWrapper:
    """Wrapper for News API"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('NEWS_API_KEY', '')
        self.base_url = "https://newsapi.org/v2"
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({'X-Api-Key': self.api_key})
    
    def search_articles(self, query: str, language: str = 'en', page_size: int = 10) -> List[Dict[str, Any]]:
        """Search for news articles"""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/everything"
            params = {
                'q': query,
                'language': language,
                'pageSize': page_size,
                'sortBy': 'relevancy'
            }
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = []
                for article in data.get('articles', []):
                    articles.append({
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', ''),
                        'published_at': article.get('publishedAt', ''),
                        'image': article.get('urlToImage', ''),
                        'content': article.get('content', '')
                    })
                return articles
        except Exception as e:
            print(f"[NewsAPI] Error: {e}")
        
        return []


class YouTubeWrapper:
    """Wrapper for YouTube API (video references)"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY', '')
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.session = requests.Session()
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for videos"""
        if not self.api_key:
            return []
        
        try:
            url = f"{self.base_url}/search"
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': max_results,
                'key': self.api_key
            }
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                videos = []
                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    videos.append({
                        'id': item.get('id', {}).get('videoId', ''),
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                        'channel': snippet.get('channelTitle', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'source': 'youtube'
                    })
                return videos
        except Exception as e:
            print(f"[YouTube] Error: {e}")
        
        return []


class DataGatheringOrchestrator:
    """Orchestrates data gathering from multiple sources"""
    
    def __init__(self):
        self.wikipedia = WikipediaWrapper()
        self.unsplash = UnsplashWrapper()
        self.news = NewsAPIWrapper()
        self.youtube = YouTubeWrapper()
    
    def gather_all_data(self, topic: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Gather data from all available sources
        
        Args:
            topic: Topic to gather data about
            max_results: Maximum results per source
        
        Returns:
            Comprehensive data dictionary
        """
        data = {
            'topic': topic,
            'timestamp': datetime.utcnow().isoformat(),
            'wikipedia': None,
            'images': [],
            'news': [],
            'videos': [],
            'summary': {}
        }
        
        # Gather from Wikipedia
        wiki_data = self.wikipedia.get_summary(topic)
        if wiki_data:
            data['wikipedia'] = wiki_data
            data['summary']['text'] = wiki_data.get('extract', '')
            data['summary']['title'] = wiki_data.get('title', topic)
        
        # Gather images
        images = self.unsplash.search_photos(topic, max_results)
        if images:
            data['images'] = images
        
        # Gather news
        news = self.news.search_articles(topic, page_size=max_results)
        if news:
            data['news'] = news
        
        # Gather video references
        videos = self.youtube.search_videos(topic, max_results)
        if videos:
            data['videos'] = videos
        
        return data


# Global instance
data_gatherer = DataGatheringOrchestrator()

