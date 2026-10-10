"""Advanced web scraping service with multiple sources, caching, and optimization"""
import os
import time
import json
import hashlib
import threading
import concurrent.futures
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse, quote_plus
from datetime import datetime, timedelta
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Try to import duckduckgo_search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

# Try to import selenium for advanced scraping
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Try to import image providers
try:
    from src.services.web_scraping.image_providers import ImageProviderManager
    IMAGE_PROVIDERS_AVAILABLE = True
except ImportError:
    IMAGE_PROVIDERS_AVAILABLE = False


class CacheManager:
    """Manages caching for scraped content"""
    
    def __init__(self, cache_dir: str = "scraper_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.cache_ttl = timedelta(hours=24)  # Cache for 24 hours
    
    def _get_cache_key(self, query: str, content_type: str) -> str:
        """Generate cache key from query"""
        key = f"{content_type}_{hashlib.md5(query.encode()).hexdigest()}"
        return key
    
    def get(self, query: str, content_type: str) -> Optional[Dict[str, Any]]:
        """Get cached content"""
        cache_file = self.cache_dir / self._get_cache_key(query, content_type)
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Check if cache is still valid
            cache_time = datetime.fromisoformat(cached.get('timestamp', ''))
            if datetime.now() - cache_time > self.cache_ttl:
                cache_file.unlink()  # Remove expired cache
                return None
            
            return cached.get('data')
        except Exception:
            return None
    
    def set(self, query: str, content_type: str, data: Any):
        """Cache content"""
        cache_file = self.cache_dir / self._get_cache_key(query, content_type)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f, ensure_ascii=False)
        except Exception:
            pass


class AdvancedWebScraper:
    """Advanced web scraper with multiple sources, caching, and optimization"""
    
    def __init__(self, cache_enabled: bool = True, max_workers: int = 5):
        """Initialize advanced web scraper"""
        self.cache = CacheManager() if cache_enabled else None
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Search engines configuration
        self.search_engines = []
        if DDGS_AVAILABLE:
            self.search_engines.append('duckduckgo')
        self.search_engines.append('google_web')  # Web scraping Google
        self.search_engines.append('bing_web')    # Web scraping Bing
        
        # Image provider manager (Pexels, Pixabay, Unsplash)
        if IMAGE_PROVIDERS_AVAILABLE:
            self.image_providers = ImageProviderManager()
        else:
            self.image_providers = None
        
        # Rate limiting
        self.rate_limits = defaultdict(float)
        self.min_delay = 0.5  # Minimum delay between requests
    
    def _rate_limit_check(self, engine: str):
        """Check and enforce rate limits"""
        now = time.time()
        last_request = self.rate_limits[engine]
        
        if now - last_request < self.min_delay:
            time.sleep(self.min_delay - (now - last_request))
        
        self.rate_limits[engine] = time.time()
    
    def _search_duckduckgo_images(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search DuckDuckGo for images with retry"""
        if not DDGS_AVAILABLE:
            return []
        
        images = []
        
        for attempt in range(3):  # Retry up to 3 times
            try:
                self._rate_limit_check('duckduckgo')
                
                with DDGS() as ddgs:
                    results = ddgs.images(
                        keywords=query,
                        max_results=max_results,
                        safesearch='moderate'
                    )
                    
                    for result in results:
                        if len(images) >= max_results:
                            break
                        
                        image_data = {
                            'url': result.get('image', ''),
                            'title': result.get('title', ''),
                            'description': result.get('thumbnail', ''),
                            'width': result.get('width', 0),
                            'height': result.get('height', 0),
                            'source': result.get('url', ''),
                            'engine': 'duckduckgo'
                        }
                        
                        if image_data['url'] and image_data['url'].startswith(('http://', 'https://')):
                            # Validate image dimensions
                            if image_data['width'] >= 200 and image_data['height'] >= 200:
                                images.append(image_data)
                
                if images:
                    break  # Success, exit retry loop
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"DuckDuckGo images error after 3 attempts: {e}")
        
        return images
    
    def _search_google_web_images(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Google Images via web scraping with improved dimension extraction and multiple strategies"""
        images = []
        
        try:
            self._rate_limit_check('google')
            
            # Google Images search URL - try multiple formats
            search_urls = [
                f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch&safe=active",
                f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch&safe=strict",
                f"https://www.google.com/search?q={quote_plus(query)}&tbm=isch"
            ]
            
            for search_url in search_urls:
                try:
                    response = self.session.get(search_url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Strategy 1: Modern Google Images structure (2024)
                    # Look for script tags with image data
                    script_tags = soup.find_all('script', type='application/ld+json')
                    for script in script_tags:
                        try:
                            import json
                            data = json.loads(script.string)
                            if isinstance(data, dict) and 'image' in data:
                                img_url = data.get('image', {}).get('contentUrl', '')
                                if img_url and img_url.startswith(('http://', 'https://')):
                                    images.append({
                                        'url': img_url,
                                        'title': data.get('name', ''),
                                        'description': data.get('description', ''),
                                        'width': 0,
                                        'height': 0,
                                        'source': search_url,
                                        'engine': 'google'
                                    })
                        except:
                            pass
                    
                    # Strategy 2: Find image containers with multiple selectors
                    selectors = [
                        ('div', {'class': ['isv-r', 'PNNCib', 'rg_l', 'rg_meta']}),
                        ('div', {'data-ved': True}),
                        ('img', {'alt': True, 'src': True}),
                        ('img', {'data-src': True}),
                        ('img', {'data-iml': True}),
                    ]
                    
                    for selector, attrs in selectors:
                        containers = soup.find_all(selector, attrs) if attrs else soup.find_all(selector)
                        if not containers:
                            continue
                        
                        for container in containers[:max_results * 3]:
                            try:
                                # Handle different container types
                                if container.name == 'img':
                                    img_tag = container
                                    title = img_tag.get('alt', '') or img_tag.get('title', '')
                                else:
                                    # Try to find img tag inside container
                                    img_tag = container.find('img')
                                    if not img_tag:
                                        # Try to extract from data attributes
                                        img_url = container.get('data-src') or container.get('data-iu')
                                        if not img_url:
                                            continue
                                        # Create a pseudo img_tag for consistency
                                        class PseudoImg:
                                            def __init__(self, url):
                                                self.attrs = {'src': url}
                                            def get(self, key, default=None):
                                                return self.attrs.get(key, default)
                                        img_tag = PseudoImg(img_url)
                                        title = container.get('title', '') or container.get('alt', '')
                                    
                                    if not title:
                                        title_tag = container.find('h3') or container.find('a', {'title': True})
                                        title = title_tag.get_text(strip=True) if title_tag else title_tag.get('title', '') if hasattr(title_tag, 'get') else ''
                                
                                # Extract image URL - try multiple attributes
                                img_url = (img_tag.get('src') or 
                                          img_tag.get('data-src') or 
                                          img_tag.get('data-original') or
                                          img_tag.get('data-lazy-src') or
                                          container.get('data-src') or
                                          container.get('data-iu') or
                                          '')
                                
                                # Clean up Google image URLs (remove redirect parameters)
                                if img_url and 'google.com/imgres?' in img_url:
                                    import urllib.parse
                                    parsed = urllib.parse.urlparse(img_url)
                                    params = urllib.parse.parse_qs(parsed.query)
                                    if 'imgurl' in params:
                                        img_url = params['imgurl'][0]
                                
                                if not img_url or not img_url.startswith(('http://', 'https://')):
                                    continue
                                
                                # Skip base64 encoded images
                                if img_url.startswith('data:image'):
                                    continue
                                
                                # Get dimensions - try multiple methods
                                width = 0
                                height = 0
                                
                                # From img tag attributes
                                width = int(img_tag.get('width', 0) or img_tag.get('data-width', 0) or 0)
                                height = int(img_tag.get('height', 0) or img_tag.get('data-height', 0) or 0)
                                
                                # From container data attributes
                                if width == 0 or height == 0:
                                    width = int(container.get('data-width', 0) or 0)
                                    height = int(container.get('data-height', 0) or 0)
                                
                                # From style attribute
                                if width == 0 or height == 0:
                                    style = img_tag.get('style', '') or container.get('style', '')
                                    if style:
                                        import re
                                        width_match = re.search(r'width[:\s]+(\d+)', style)
                                        height_match = re.search(r'height[:\s]+(\d+)', style)
                                        if width_match:
                                            width = int(width_match.group(1))
                                        if height_match:
                                            height = int(height_match.group(1))
                                
                                # From JSON data in container
                                if width == 0 or height == 0:
                                    container_text = container.get_text()
                                    if container_text:
                                        try:
                                            import json
                                            data = json.loads(container_text)
                                            if isinstance(data, dict):
                                                width = int(data.get('ow', data.get('width', 0)) or 0)
                                                height = int(data.get('oh', data.get('height', 0)) or 0)
                                        except:
                                            pass
                                
                                # If still unknown, try HEAD request for actual image dimensions
                                if width == 0 or height == 0:
                                    try:
                                        head_response = self.session.head(img_url, timeout=5, allow_redirects=True)
                                        content_length = int(head_response.headers.get('Content-Length', 0))
                                        content_type = head_response.headers.get('Content-Type', '')
                                        
                                        if content_length > 0:
                                            # Rough estimate from file size and type
                                            if 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                                                if content_length > 500000:  # > 500KB
                                                    width, height = 1920, 1080
                                                elif content_length > 200000:  # > 200KB
                                                    width, height = 1200, 800
                                                elif content_length > 100000:  # > 100KB
                                                    width, height = 800, 600
                                            elif 'png' in content_type.lower():
                                                if content_length > 1000000:  # > 1MB
                                                    width, height = 1920, 1080
                                                elif content_length > 300000:  # > 300KB
                                                    width, height = 1200, 800
                                    except:
                                        pass
                                
                                # Accept if dimensions are reasonable or unknown
                                if width >= 200 or height >= 200 or (width == 0 and height == 0):
                                    # Check if URL already exists
                                    if any(img['url'] == img_url for img in images):
                                        continue
                                    
                                    images.append({
                                        'url': img_url,
                                        'title': title[:200] if title else '',  # Limit title length
                                        'description': '',
                                        'width': width,
                                        'height': height,
                                        'source': search_url,
                                        'engine': 'google'
                                    })
                                    
                                    if len(images) >= max_results:
                                        break
                                    
                            except Exception as e:
                                continue
                        
                        if images:
                            break  # Found images, exit selector loop
                    
                    if images:
                        break  # Found images, exit URL loop
                        
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Google web images error: {e}")
        
        return images[:max_results]
    
    def _search_bing_web_images(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Bing Images via web scraping with improved dimension extraction"""
        images = []
        
        try:
            self._rate_limit_check('bing')
            
            search_url = f"https://www.bing.com/images/search?q={quote_plus(query)}&safeSearch=strict"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find image results - try multiple selectors
            img_results = soup.find_all('a', {'class': 'iusc'})
            if not img_results:
                # Alternative selector
                img_results = soup.find_all('div', {'class': 'img_cont'})
            
            for result in img_results[:max_results * 2]:  # Get more to filter
                try:
                    # Extract image data from data attributes
                    img_data = result.get('m', '{}')
                    if isinstance(img_data, str):
                        import json
                        try:
                            img_data = json.loads(img_data)
                        except:
                            img_data = {}
                    
                    # Try multiple ways to get image URL
                    img_url = img_data.get('murl', '') or result.get('href', '')
                    
                    # Extract from img tag if available
                    img_tag = result.find('img')
                    if img_tag:
                        if not img_url:
                            img_url = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-original', '')
                        
                        # Try to get dimensions from img tag
                        width = int(img_tag.get('width', 0) or img_data.get('w', 0) or 0)
                        height = int(img_tag.get('height', 0) or img_data.get('h', 0) or 0)
                    else:
                        width = int(img_data.get('w', 0) or 0)
                        height = int(img_data.get('h', 0) or 0)
                    
                    if not img_url or not img_url.startswith(('http://', 'https://')):
                        continue
                    
                    # If dimensions still unknown, try to fetch image head to get dimensions
                    if width == 0 or height == 0:
                        try:
                            head_response = self.session.head(img_url, timeout=5, allow_redirects=True)
                            content_length = int(head_response.headers.get('Content-Length', 0))
                            # Estimate dimensions from file size (rough estimate)
                            if content_length > 100000:  # > 100KB likely a larger image
                                width = 800  # Default estimate
                                height = 600
                        except:
                            pass
                    
                    title = img_data.get('t', '') or (img_tag.get('alt', '') if img_tag else '')
                    
                    if width >= 200 or height >= 200 or (width == 0 and height == 0):
                        images.append({
                            'url': img_url,
                            'title': title,
                            'description': '',
                            'width': width,
                            'height': height,
                            'source': search_url,
                            'engine': 'bing'
                        })
                        
                        if len(images) >= max_results:
                            break
                except Exception as e:
                    continue
        
        except Exception as e:
            print(f"Bing web images error: {e}")
        
        return images
    
    def search_and_scrape_images(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for images using multiple sources concurrently"""
        if max_results is None:
            max_results = 50  # Increased default
        
        # Check cache
        if self.cache:
            cached = self.cache.get(query, 'images')
            if cached:
                return cached[:max_results]
        
        all_images = []
        seen_urls = set()
        
        # Run searches concurrently - web scraping
        max_web_workers = 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_web_workers + 1) as executor:
            futures = []
            
            # DuckDuckGo
            if DDGS_AVAILABLE:
                futures.append(executor.submit(self._search_duckduckgo_images, query, max_results // 4))
            
            # Google
            futures.append(executor.submit(self._search_google_web_images, query, max_results // 4))
            
            # Bing
            futures.append(executor.submit(self._search_bing_web_images, query, max_results // 4))
            
            # API-based providers (Pexels, Pixabay, Unsplash)
            if self.image_providers:
                futures.append(executor.submit(self.image_providers.search_all_providers, query, max_results // 2))
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    images = future.result()
                    for img in images:
                        url = img.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_images.append(img)
                except Exception as e:
                    print(f"Image search future error: {e}")
        
        # Sort by relevance and deduplicate
        all_images = self._deduplicate_images(all_images)
        result = all_images[:max_results]
        
        # Cache result
        if self.cache:
            self.cache.set(query, 'images', result)
        
        return result
    
    def _deduplicate_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate and sort images"""
        seen = set()
        unique = []
        
        for img in images:
            url = img.get('url', '')
            if url and url not in seen:
                seen.add(url)
                unique.append(img)
        
        # Sort by quality (prefer larger images)
        unique.sort(key=lambda x: (x.get('width', 0) * x.get('height', 0)), reverse=True)
        
        return unique
    
    def _search_duckduckgo_text(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search DuckDuckGo for text content"""
        if not DDGS_AVAILABLE:
            return []
        
        scripts = []
        
        for attempt in range(3):
            try:
                self._rate_limit_check('duckduckgo')
                
                with DDGS() as ddgs:
                    results = ddgs.text(
                        keywords=f"{query} script storyline documentary narrative",
                        max_results=max_results * 2,
                        safesearch='moderate'
                    )
                    
                    for result in results:
                        if len(scripts) >= max_results:
                            break
                        
                        url = result.get('href', '')
                        title = result.get('title', '')
                        body = result.get('body', '')
                        
                        # Enhanced filtering
                        relevant_keywords = ['script', 'storyline', 'documentary', 'narrative', 'story', 'plot', 'synopsis', 'treatment']
                        if not any(kw in body.lower() for kw in relevant_keywords):
                            continue
                        
                        script_data = {
                            'url': url,
                            'title': title,
                            'snippet': body,
                            'content': body,  # Will be enriched later
                            'engine': 'duckduckgo'
                        }
                        
                        if script_data['url'] and len(body) > 50:
                            scripts.append(script_data)
                
                if scripts:
                    break
                    
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    print(f"DuckDuckGo text error after 3 attempts: {e}")
        
        return scripts
    
    def _search_google_web_text(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Google for text content (scripts, storylines)"""
        scripts = []
        
        try:
            self._rate_limit_check('google')
            
            search_url = f"https://www.google.com/search?q={quote_plus(query)} script storyline documentary"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find search results
            results = soup.find_all('div', {'class': 'g'}) or soup.find_all('div', {'class': 'tF2Cxc'})
            
            for result in results[:max_results]:
                try:
                    # Extract title and link
                    title_tag = result.find('h3')
                    link_tag = result.find('a')
                    
                    if not link_tag:
                        continue
                    
                    url = link_tag.get('href', '')
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    
                    # Extract snippet
                    snippet_tag = result.find('span', {'class': ['st', 'aCOpRe']})
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
                    
                    # Filter for relevant content
                    relevant_keywords = ['script', 'storyline', 'documentary', 'narrative', 'story', 'plot', 'synopsis', 'treatment']
                    if not any(kw in (title + ' ' + snippet).lower() for kw in relevant_keywords):
                        continue
                    
                    if url and len(snippet) > 50:
                        scripts.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'content': snippet,  # Will be enriched later
                            'engine': 'google'
                        })
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Google web text error: {e}")
        
        return scripts
    
    def _search_bing_web_text(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Bing for text content (scripts, storylines)"""
        scripts = []
        
        try:
            self._rate_limit_check('bing')
            
            search_url = f"https://www.bing.com/search?q={quote_plus(query)} script storyline documentary"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find search results
            results = soup.find_all('li', {'class': 'b_algo'}) or soup.find_all('div', {'class': 'b_algo'})
            
            for result in results[:max_results]:
                try:
                    # Extract title and link
                    title_tag = result.find('h2')
                    link_tag = title_tag.find('a') if title_tag else result.find('a')
                    
                    if not link_tag:
                        continue
                    
                    url = link_tag.get('href', '')
                    title = link_tag.get_text(strip=True) if link_tag else ''
                    
                    # Extract snippet
                    snippet_tag = result.find('p') or result.find('div', {'class': 'b_caption'})
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ''
                    
                    # Filter for relevant content
                    relevant_keywords = ['script', 'storyline', 'documentary', 'narrative', 'story', 'plot', 'synopsis', 'treatment']
                    if not any(kw in (title + ' ' + snippet).lower() for kw in relevant_keywords):
                        continue
                    
                    if url and len(snippet) > 50:
                        scripts.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'content': snippet,  # Will be enriched later
                            'engine': 'bing'
                        })
                except Exception:
                    continue
        
        except Exception as e:
            print(f"Bing web text error: {e}")
        
        return scripts
    
    def _scrape_page_content_advanced(self, url: str) -> Optional[str]:
        """Advanced page content scraping with multiple strategies"""
        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()
            
            # Multiple extraction strategies
            content_selectors = [
                ('article', {}),
                ('main', {}),
                ('div', {'class': ['content', 'post-content', 'entry-content', 'article-content']}),
                ('div', {'id': ['content', 'main', 'article', 'post']}),
                ('section', {'class': ['content', 'main-content']}),
            ]
            
            text_content = None
            for selector, attrs in content_selectors:
                element = soup.find(selector, attrs) if attrs else soup.find(selector)
                if element:
                    text_content = element.get_text(separator='\n', strip=True)
                    if len(text_content) > 500:  # Substantial content
                        break
            
            if not text_content:
                # Fallback: extract from body
                body = soup.find('body')
                if body:
                    text_content = body.get_text(separator='\n', strip=True)
            
            if not text_content:
                return None
            
            # Clean and process text
            lines = [line.strip() for line in text_content.split('\n') if line.strip() and len(line.strip()) > 10]
            text_content = '\n'.join(lines[:200])  # Increased to 200 lines
            
            # Quality check
            if len(text_content) > 500 and text_content.count(' ') > 50:  # Substantial text
                return text_content
            
            return None
        
        except Exception as e:
            print(f"Advanced page scraping error for {url}: {e}")
            return None
    
    def search_and_scrape_scripts(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for scripts with multiple sources and concurrent page scraping"""
        if max_results is None:
            max_results = 20  # Increased default
        
        # Check cache
        if self.cache:
            cached = self.cache.get(query, 'scripts')
            if cached:
                return cached[:max_results]
        
        all_scripts = []
        seen_urls = set()
        
        # Search multiple sources concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            # DuckDuckGo
            if DDGS_AVAILABLE:
                futures.append(executor.submit(self._search_duckduckgo_text, query, max_results // 3))
            
            # Google
            futures.append(executor.submit(self._search_google_web_text, query, max_results // 3))
            
            # Bing
            futures.append(executor.submit(self._search_bing_web_text, query, max_results // 3))
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    scripts = future.result()
                    for script in scripts:
                        url = script.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_scripts.append(script)
                except Exception as e:
                    print(f"Script search future error: {e}")
        
        # Enrich with full page content concurrently
        def enrich_script(script_data):
            url = script_data.get('url', '')
            if url:
                full_content = self._scrape_page_content_advanced(url)
                if full_content:
                    script_data['content'] = full_content
                    script_data['content_length'] = len(full_content)
                elif not script_data.get('content'):
                    script_data['content'] = script_data.get('snippet', '')
                    script_data['content_length'] = len(script_data['content'])
            return script_data
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            enriched_scripts = list(executor.map(enrich_script, all_scripts))
        
        # Filter and sort by content quality
        enriched_scripts = [s for s in enriched_scripts if s.get('content_length', 0) > 200]
        enriched_scripts.sort(key=lambda x: x.get('content_length', 0), reverse=True)
        
        result = enriched_scripts[:max_results]
        
        # Cache result
        if self.cache:
            self.cache.set(query, 'scripts', result)
        
        return result
    
    def search_and_scrape_all(self, query: str) -> Dict[str, Any]:
        """Search for both images and scripts concurrently"""
        # Run both searches concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            images_future = executor.submit(self.search_and_scrape_images, query)
            scripts_future = executor.submit(self.search_and_scrape_scripts, query)
            
            images = images_future.result()
            scripts = scripts_future.result()
        
        return {
            'images': images,
            'scripts': scripts,
            'total_images': len(images),
            'total_scripts': len(scripts),
            'query': query,
            'timestamp': datetime.now().isoformat()
        }

