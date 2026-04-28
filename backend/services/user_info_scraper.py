"""
User Information Scraper Service
Scrapes and collects information from new users for profile enrichment
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UserInfoScraper:
    """Service for scraping user information"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.data_dir = os.path.join(self.base_dir, 'logs', 'user_scraped_info')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def scrape_browser_info(self, request_data: Dict) -> Dict:
        """Scrape browser information from request"""
        browser_info = {
            'user_agent': request_data.get('user_agent', ''),
            'language': request_data.get('language', ''),
            'languages': request_data.get('languages', []),
            'platform': request_data.get('platform', ''),
            'cookie_enabled': request_data.get('cookie_enabled', False),
            'screen_width': request_data.get('screen_width'),
            'screen_height': request_data.get('screen_height'),
            'color_depth': request_data.get('color_depth'),
            'timezone': request_data.get('timezone'),
            'timezone_offset': request_data.get('timezone_offset'),
            'hardware_concurrency': request_data.get('hardware_concurrency'),
            'device_memory': request_data.get('device_memory'),
            'connection_type': request_data.get('connection_type'),
            'scraped_at': datetime.now().isoformat()
        }
        
        # Generate browser fingerprint
        fingerprint_data = f"{browser_info['user_agent']}{browser_info['platform']}{browser_info['screen_width']}{browser_info['screen_height']}"
        browser_info['fingerprint'] = hashlib.md5(fingerprint_data.encode()).hexdigest()
        
        return browser_info
    
    def scrape_device_info(self, request_data: Dict) -> Dict:
        """Scrape device information"""
        user_agent = request_data.get('user_agent', '').lower()
        
        device_info = {
            'device_type': self._detect_device_type(user_agent),
            'os': self._detect_os(user_agent),
            'browser': self._detect_browser(user_agent),
            'is_mobile': 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent,
            'is_tablet': 'tablet' in user_agent or 'ipad' in user_agent,
            'is_desktop': not ('mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent or 'tablet' in user_agent),
            'touch_support': request_data.get('touch_support', False),
            'scraped_at': datetime.now().isoformat()
        }
        
        return device_info
    
    def scrape_location_info(self, request_data: Dict) -> Dict:
        """Scrape location information (IP-based, privacy-aware)"""
        location_info = {
            'ip_address': request_data.get('ip_address', ''),
            'country': request_data.get('country', ''),
            'region': request_data.get('region', ''),
            'city': request_data.get('city', ''),
            'timezone': request_data.get('timezone', ''),
            'scraped_at': datetime.now().isoformat()
        }
        
        # Anonymize IP (store only first 3 octets)
        if location_info['ip_address']:
            ip_parts = location_info['ip_address'].split('.')
            if len(ip_parts) == 4:
                location_info['ip_anonymized'] = '.'.join(ip_parts[:3]) + '.xxx'
        
        return location_info
    
    def scrape_behavioral_info(self, request_data: Dict) -> Dict:
        """Scrape behavioral information from initial interactions"""
        behavioral_info = {
            'referral_source': request_data.get('referral_source', 'direct'),
            'referral_url': request_data.get('referral_url', ''),
            'landing_page': request_data.get('landing_page', ''),
            'initial_actions': request_data.get('initial_actions', []),
            'pages_visited': request_data.get('pages_visited', []),
            'time_on_site': request_data.get('time_on_site', 0),
            'click_patterns': request_data.get('click_patterns', []),
            'scroll_depth': request_data.get('scroll_depth', 0),
            'interaction_types': request_data.get('interaction_types', []),
            'scraped_at': datetime.now().isoformat()
        }
        
        # Analyze behavior patterns
        behavioral_info['behavior_pattern'] = self._analyze_behavior_pattern(behavioral_info)
        
        return behavioral_info
    
    def scrape_preferences(self, request_data: Dict) -> Dict:
        """Infer user preferences from behavior"""
        preferences = {
            'preferred_language': request_data.get('language', 'en'),
            'theme_preference': request_data.get('theme', 'auto'),
            'content_interests': request_data.get('content_interests', []),
            'feature_usage': request_data.get('feature_usage', {}),
            'interaction_style': request_data.get('interaction_style', 'balanced'),
            'scraped_at': datetime.now().isoformat()
        }
        
        # Infer preferences from behavior
        if request_data.get('pages_visited'):
            pages = request_data.get('pages_visited', [])
            if 'battle' in str(pages).lower():
                preferences['content_interests'].append('battle')
            if 'social' in str(pages).lower():
                preferences['content_interests'].append('social')
            if 'profile' in str(pages).lower():
                preferences['content_interests'].append('profile')
        
        return preferences
    
    def scrape_all_info(self, request_data: Dict) -> Dict:
        """Scrape all available information"""
        scraped_data = {
            'browser': self.scrape_browser_info(request_data),
            'device': self.scrape_device_info(request_data),
            'location': self.scrape_location_info(request_data),
            'behavior': self.scrape_behavioral_info(request_data),
            'preferences': self.scrape_preferences(request_data),
            'scraped_at': datetime.now().isoformat(),
            'scraping_version': '1.0.0'
        }
        
        # Calculate confidence score
        scraped_data['confidence_score'] = self._calculate_confidence(scraped_data)
        
        return scraped_data
    
    def save_scraped_info(self, user_id: str, info_type: str, info_data: Dict) -> bool:
        """Save scraped information to file"""
        try:
            user_dir = os.path.join(self.data_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            file_path = os.path.join(user_dir, f"{info_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            with open(file_path, 'w') as f:
                json.dump({
                    'user_id': user_id,
                    'info_type': info_type,
                    'info_data': info_data,
                    'saved_at': datetime.now().isoformat()
                }, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving scraped info: {e}")
            return False
    
    def get_scraped_info(self, user_id: str, info_type: Optional[str] = None) -> Dict:
        """Get scraped information for a user"""
        user_dir = os.path.join(self.data_dir, user_id)
        
        if not os.path.exists(user_dir):
            return {}
        
        info = {}
        
        if info_type:
            # Get specific info type
            files = [f for f in os.listdir(user_dir) if f.startswith(info_type)]
            if files:
                latest_file = max(files)
                file_path = os.path.join(user_dir, latest_file)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        info = data.get('info_data', {})
                except:
                    pass
        else:
            # Get all info types
            for file in os.listdir(user_dir):
                if file.endswith('.json'):
                    info_type_from_file = file.split('_')[0]
                    file_path = os.path.join(user_dir, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            info[info_type_from_file] = data.get('info_data', {})
                    except:
                        pass
        
        return info
    
    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent"""
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        else:
            return 'desktop'
    
    def _detect_os(self, user_agent: str) -> str:
        """Detect operating system"""
        if 'windows' in user_agent:
            return 'windows'
        elif 'mac' in user_agent or 'macos' in user_agent:
            return 'macos'
        elif 'linux' in user_agent:
            return 'linux'
        elif 'android' in user_agent:
            return 'android'
        elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
            return 'ios'
        else:
            return 'unknown'
    
    def _detect_browser(self, user_agent: str) -> str:
        """Detect browser"""
        if 'chrome' in user_agent and 'edg' not in user_agent:
            return 'chrome'
        elif 'firefox' in user_agent:
            return 'firefox'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            return 'safari'
        elif 'edg' in user_agent:
            return 'edge'
        elif 'opera' in user_agent:
            return 'opera'
        else:
            return 'unknown'
    
    def _analyze_behavior_pattern(self, behavioral_info: Dict) -> str:
        """Analyze behavior pattern"""
        actions = behavioral_info.get('initial_actions', [])
        pages = behavioral_info.get('pages_visited', [])
        
        if not actions and not pages:
            return 'explorer'  # Just exploring
        
        # Check for specific patterns
        action_str = str(actions).lower()
        pages_str = str(pages).lower()
        
        if 'battle' in pages_str or 'fight' in action_str:
            return 'battle_focused'
        elif 'social' in pages_str or 'friend' in action_str:
            return 'social_focused'
        elif 'profile' in pages_str or 'stats' in pages_str:
            return 'analytics_focused'
        elif 'generate' in action_str or 'create' in action_str:
            return 'creator_focused'
        else:
            return 'balanced'
    
    def _calculate_confidence(self, scraped_data: Dict) -> float:
        """Calculate confidence score for scraped data (0.0 to 1.0)"""
        score = 0.0
        max_score = 0.0
        
        # Browser info (30%)
        if scraped_data.get('browser', {}).get('user_agent'):
            score += 0.3
        max_score += 0.3
        
        # Device info (20%)
        if scraped_data.get('device', {}).get('device_type'):
            score += 0.2
        max_score += 0.2
        
        # Location info (20%)
        if scraped_data.get('location', {}).get('timezone'):
            score += 0.2
        max_score += 0.2
        
        # Behavioral info (20%)
        if scraped_data.get('behavior', {}).get('initial_actions'):
            score += 0.2
        max_score += 0.2
        
        # Preferences (10%)
        if scraped_data.get('preferences', {}).get('content_interests'):
            score += 0.1
        max_score += 0.1
        
        return round(score / max_score if max_score > 0 else 0.0, 2)

# Global instance
user_info_scraper = UserInfoScraper()
