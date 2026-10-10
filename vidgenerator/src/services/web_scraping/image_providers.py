"""Image provider integrations for Pexels, Pixabay, Unsplash"""
import os
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus

# Try to import API clients if available
try:
    from pexels_api import API as PexelsAPI
    PEXELS_AVAILABLE = True
except ImportError:
    PEXELS_AVAILABLE = False

try:
    import pixabay
    PIXABAY_AVAILABLE = True
except ImportError:
    PIXABAY_AVAILABLE = False


class ImageProviderManager:
    """Manages multiple image providers with fallback"""
    
    def __init__(self):
        """Initialize image provider manager"""
        # API Keys from environment
        self.pexels_api_key = os.getenv('PEXELS_API_KEY', '')
        self.pixabay_api_key = os.getenv('PIXABAY_API_KEY', '')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY', '')
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_pexels(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Pexels for images"""
        images = []
        
        if not self.pexels_api_key:
            return images
        
        try:
            if PEXELS_AVAILABLE:
                # Use Pexels API library if available
                api = PexelsAPI(self.pexels_api_key)
                search_results = api.search(query, results_per_page=min(max_results, 80))
                
                for photo in search_results.get('photos', [])[:max_results]:
                    images.append({
                        'url': photo.get('src', {}).get('large', photo.get('src', {}).get('medium', '')),
                        'title': photo.get('photographer', ''),
                        'description': photo.get('alt', ''),
                        'width': photo.get('width', 0),
                        'height': photo.get('height', 0),
                        'source': photo.get('url', ''),
                        'engine': 'pexels',
                        'license': 'Free to use'
                    })
            else:
                # Fallback: Direct API call
                url = f"https://api.pexels.com/v1/search?query={quote_plus(query)}&per_page={min(max_results, 80)}"
                headers = {'Authorization': self.pexels_api_key}
                
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for photo in data.get('photos', [])[:max_results]:
                    images.append({
                        'url': photo.get('src', {}).get('large', photo.get('src', {}).get('medium', '')),
                        'title': photo.get('photographer', ''),
                        'description': photo.get('alt', ''),
                        'width': photo.get('width', 0),
                        'height': photo.get('height', 0),
                        'source': photo.get('url', ''),
                        'engine': 'pexels',
                        'license': 'Free to use'
                    })
        except Exception as e:
            print(f"Pexels API error: {e}")
        
        return images
    
    def search_pixabay(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Pixabay for images"""
        images = []
        
        if not self.pixabay_api_key:
            return images
        
        try:
            if PIXABAY_AVAILABLE:
                # Use Pixabay library if available
                px = pixabay.Image(self.pixabay_api_key)
                search_results = px.search(q=query, per_page=min(max_results, 200))
                
                for hit in search_results.get('hits', [])[:max_results]:
                    images.append({
                        'url': hit.get('largeImageURL', hit.get('webformatURL', '')),
                        'title': hit.get('tags', ''),
                        'description': hit.get('tags', ''),
                        'width': hit.get('imageWidth', 0),
                        'height': hit.get('imageHeight', 0),
                        'source': hit.get('pageURL', ''),
                        'engine': 'pixabay',
                        'license': 'Free to use'
                    })
            else:
                # Fallback: Direct API call
                url = f"https://pixabay.com/api/?key={self.pixabay_api_key}&q={quote_plus(query)}&image_type=photo&per_page={min(max_results, 200)}"
                
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for hit in data.get('hits', [])[:max_results]:
                    images.append({
                        'url': hit.get('largeImageURL', hit.get('webformatURL', '')),
                        'title': hit.get('tags', ''),
                        'description': hit.get('tags', ''),
                        'width': hit.get('imageWidth', 0),
                        'height': hit.get('imageHeight', 0),
                        'source': hit.get('pageURL', ''),
                        'engine': 'pixabay',
                        'license': 'Free to use'
                    })
        except Exception as e:
            print(f"Pixabay API error: {e}")
        
        return images
    
    def search_unsplash(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search Unsplash for images"""
        images = []
        
        if not self.unsplash_access_key:
            return images
        
        try:
            # Unsplash API
            url = f"https://api.unsplash.com/search/photos?query={quote_plus(query)}&per_page={min(max_results, 30)}"
            headers = {
                'Authorization': f'Client-ID {self.unsplash_access_key}',
                'Accept-Version': 'v1'
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for photo in data.get('results', [])[:max_results]:
                urls = photo.get('urls', {})
                images.append({
                    'url': urls.get('regular', urls.get('small', '')),
                    'title': photo.get('description', photo.get('alt_description', '')),
                    'description': photo.get('description', ''),
                    'width': photo.get('width', 0),
                    'height': photo.get('height', 0),
                    'source': photo.get('links', {}).get('html', ''),
                    'engine': 'unsplash',
                    'license': 'Free to use'
                })
        except Exception as e:
            print(f"Unsplash API error: {e}")
        
        return images
    
    def search_all_providers(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search all available providers and combine results"""
        all_images = []
        seen_urls = set()
        
        # Search all providers
        providers = [
            ('pexels', self.search_pexels),
            ('pixabay', self.search_pixabay),
            ('unsplash', self.search_unsplash),
        ]
        
        for provider_name, search_func in providers:
            try:
                images = search_func(query, max_results // len(providers))
                for img in images:
                    url = img.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_images.append(img)
            except Exception as e:
                print(f"Error searching {provider_name}: {e}")
        
        # Sort by quality (prefer larger images)
        all_images.sort(key=lambda x: (x.get('width', 0) * x.get('height', 0)), reverse=True)
        
        return all_images[:max_results]

