"""Web scraping service for gathering images and scripts"""
import os
import requests
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Try to import duckduckgo_search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False

# Import advanced scraper if available
try:
    from src.services.web_scraping.advanced_scraper import AdvancedWebScraper
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False

import time

class WebScraper:
    """Web scraping service for gathering content for documentaries"""
    
    def __init__(self, use_advanced: bool = True):
        """Initialize web scraper"""
        # Use advanced scraper if available, otherwise fallback to basic
        if use_advanced and ADVANCED_AVAILABLE:
            self._advanced_scraper = AdvancedWebScraper(cache_enabled=True, max_workers=5)
            self.use_advanced = True
        else:
            self.use_advanced = False
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            })
        
        self.max_images = 50  # Increased maximum
        self.max_scripts = 20  # Increased maximum
    
    def search_and_scrape_images(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for and scrape images from web using advanced multi-source scraping
        
        Args:
            query: Search query for images
            max_results: Maximum number of images to return (default: self.max_images)
        
        Returns:
            List of image dictionaries with url, title, description
        """
        if max_results is None:
            max_results = self.max_images
        
        # Use advanced scraper if available
        if self.use_advanced:
            return self._advanced_scraper.search_and_scrape_images(query, max_results)
        
        # Fallback to basic scraping
        images = []
        
        try:
            if not DDGS_AVAILABLE:
                return images
            
            # Use DuckDuckGo to search for images with retry
            for attempt in range(3):
                try:
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
                                'source': result.get('url', '')
                            }
                            
                            # Validate image URL and dimensions
                            if image_data['url'] and image_data['url'].startswith(('http://', 'https://')):
                                if image_data['width'] >= 200 or image_data['height'] >= 200 or (image_data['width'] == 0 and image_data['height'] == 0):
                                    images.append(image_data)
                        
                        if images:
                            break  # Success
                        
                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        print(f"Error searching images after 3 attempts: {e}")
        
        except Exception as e:
            print(f"Error searching images: {e}")
        
        return images[:max_results]
    
    def search_and_scrape_scripts(self, query: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for and scrape scripts/storylines from web using advanced scraping
        
        Args:
            query: Search query for scripts
            max_results: Maximum number of scripts to return (default: self.max_scripts)
        
        Returns:
            List of script dictionaries with url, title, content
        """
        if max_results is None:
            max_results = self.max_scripts
        
        # Use advanced scraper if available
        if self.use_advanced:
            return self._advanced_scraper.search_and_scrape_scripts(query, max_results)
        
        # Fallback to basic scraping
        scripts = []
        
        try:
            if not DDGS_AVAILABLE:
                return scripts
            
            # Use DuckDuckGo to search for text content with retry
            for attempt in range(3):
                try:
                    with DDGS() as ddgs:
                        results = ddgs.text(
                            keywords=f"{query} script storyline documentary narrative",
                            max_results=max_results * 2,  # Get more to filter
                            safesearch='moderate'
                        )
                        
                        for result in results:
                            if len(scripts) >= max_results:
                                break
                            
                            url = result.get('href', '')
                            title = result.get('title', '')
                            body = result.get('body', '')
                            
                            # Enhanced filtering for relevant content
                            relevant_keywords = ['script', 'storyline', 'documentary', 'narrative', 'story', 'plot', 'synopsis']
                            if not any(keyword in body.lower() for keyword in relevant_keywords):
                                continue
                            
                            # Try to scrape full content from URL
                            content = self._scrape_page_content(url)
                            if not content:
                                content = body  # Fallback to snippet
                            
                            script_data = {
                                'url': url,
                                'title': title,
                                'content': content,
                                'snippet': body
                            }
                            
                            if script_data['url'] and len(script_data['content']) > 100:
                                scripts.append(script_data)
                        
                        if scripts:
                            break  # Success
                        
                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    else:
                        print(f"Error searching scripts after 3 attempts: {e}")
        
        except Exception as e:
            print(f"Error searching scripts: {e}")
        
        return scripts[:max_results]
    
    def _scrape_page_content(self, url: str) -> Optional[str]:
        """
        Scrape text content from a web page
        
        Args:
            url: URL to scrape
        
        Returns:
            Extracted text content or None
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract main content
            # Try to find main content area
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            
            if main_content:
                text = main_content.get_text(separator='\n', strip=True)
            else:
                text = soup.get_text(separator='\n', strip=True)
            
            # Clean up text
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines[:100])  # Limit to first 100 lines
            
            return text if len(text) > 100 else None  # Only return if substantial content
        
        except Exception as e:
            print(f"Error scraping page {url}: {e}")
            return None
    
    def search_and_scrape_all(self, query: str, additional_queries: Optional[List[str]] = None, include_matrix_search: bool = True) -> Dict[str, Any]:
        """
        Search for both images and scripts concurrently using advanced scraping
        Includes Matrix-themed search terms automatically if query is Matrix-related
        
        Args:
            query: Search query
            additional_queries: Optional list of additional search queries
            include_matrix_search: Whether to include Matrix-related search terms
        
        Returns:
            Dictionary with 'images', 'scripts', totals, and metadata
        """
        # Import Matrix data enrichment for automatic Matrix search
        if include_matrix_search:
            try:
                import sys
                import os
                # Add project root to path if needed
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                
                from matrix_data_enrichment import get_matrix_search_terms, MATRIX_KEYWORDS
                
                # Check if query is Matrix-related
                query_lower = query.lower()
                is_matrix_related = any(keyword in query_lower for keyword in MATRIX_KEYWORDS)
                
                # Add Matrix search terms if query is Matrix-related
                if is_matrix_related:
                    matrix_terms = get_matrix_search_terms(query)
                    if additional_queries:
                        additional_queries.extend(matrix_terms[1:])  # Skip first (original query)
                    else:
                        additional_queries = matrix_terms[1:]
                    print(f"[Matrix] Added {len(matrix_terms)-1} Matrix-related search terms")
            except ImportError as e:
                print(f"[Matrix] Could not import matrix_data_enrichment: {e}")
            except Exception as e:
                print(f"[Matrix] Error adding Matrix search terms: {e}")
        
        # Use advanced scraper if available (handles concurrency internally)
        if self.use_advanced:
            # Combine queries for advanced scraper
            all_queries = [query]
            if additional_queries:
                all_queries.extend(additional_queries)
            return self._advanced_scraper.search_and_scrape_all(query, additional_queries=all_queries[1:] if len(all_queries) > 1 else None)
        
        # Fallback: run sequentially
        images = self.search_and_scrape_images(query)
        scripts = self.search_and_scrape_scripts(query)
        
        # Search with additional queries if provided
        if additional_queries:
            for additional_query in additional_queries:
                additional_images = self.search_and_scrape_images(additional_query, max_results=5)
                additional_scripts = self.search_and_scrape_scripts(additional_query, max_results=3)
                images.extend(additional_images)
                scripts.extend(additional_scripts)
        
        return {
            'images': images,
            'scripts': scripts,
            'total_images': len(images),
            'total_scripts': len(scripts),
            'query': query
        }

