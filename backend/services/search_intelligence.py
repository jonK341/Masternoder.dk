"""
Search Intelligence System
7 different tech upgrades for search point system
"""
from typing import Dict, Any, List, Optional
import logging
import json

logger = logging.getLogger(__name__)

class SearchIntelligence:
    """Enhanced search system with 7 tech upgrades"""
    
    def __init__(self):
        self.base_search_points = 1
        self.enhanced_search_points = 5  # Base enhanced value
        
        # 7 Tech Upgrades
        self.tech_upgrades = {
            'ai_powered': {
                'name': 'AI-Powered Search',
                'description': 'Machine learning search with intent understanding',
                'multiplier': 1.5,
                'enabled': True
            },
            'semantic': {
                'name': 'Semantic Search',
                'description': 'Understands meaning and context',
                'multiplier': 1.3,
                'enabled': True
            },
            'voice': {
                'name': 'Voice Search',
                'description': 'Voice-activated search capabilities',
                'multiplier': 1.4,
                'enabled': True
            },
            'visual': {
                'name': 'Visual Search',
                'description': 'Image-based search functionality',
                'multiplier': 1.6,
                'enabled': True
            },
            'predictive': {
                'name': 'Predictive Search',
                'description': 'Anticipates user queries',
                'multiplier': 1.2,
                'enabled': True
            },
            'contextual': {
                'name': 'Contextual Search',
                'description': 'Context-aware search results',
                'multiplier': 1.35,
                'enabled': True
            },
            'federated': {
                'name': 'Federated Search',
                'description': 'Multi-source search aggregation',
                'multiplier': 1.45,
                'enabled': True
            }
        }
        
        self.user_search_history = {}  # user_id -> [searches]
        self.search_analytics = {}  # query -> analytics
    
    def perform_search(self, user_id: str, query: str, search_type: str = 'standard', 
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform enhanced search and award points"""
        metadata = metadata or {}
        
        # Calculate base points
        base_points = self.enhanced_search_points
        
        # Apply tech upgrade multipliers
        total_multiplier = 1.0
        active_upgrades = []
        
        for tech_id, tech_data in self.tech_upgrades.items():
            if tech_data['enabled']:
                # Check if this search type uses this tech
                if self._search_uses_tech(search_type, tech_id):
                    total_multiplier *= tech_data['multiplier']
                    active_upgrades.append(tech_id)
        
        # Quality bonus (if results are relevant)
        quality_score = metadata.get('quality_score', 0.5)  # 0-1
        quality_bonus = base_points * quality_score * 0.5  # Up to 50% bonus
        
        # Innovation bonus (for new search types)
        innovation_bonus = 0
        if search_type not in ['standard', 'basic']:
            innovation_bonus = base_points * 1.0  # 100% bonus for innovative searches
        
        # Calculate total points
        total_points = int(
            (base_points * total_multiplier) + 
            quality_bonus + 
            innovation_bonus
        )
        
        # Track search
        if user_id not in self.user_search_history:
            self.user_search_history[user_id] = []
        
        search_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'query': query,
            'search_type': search_type,
            'points_awarded': total_points,
            'tech_upgrades_used': active_upgrades,
            'metadata': metadata
        }
        self.user_search_history[user_id].append(search_entry)
        
        # Update analytics
        self._update_analytics(query, search_type, total_points)
        
        return {
            'success': True,
            'query': query,
            'search_type': search_type,
            'points_awarded': total_points,
            'base_points': base_points,
            'multiplier': total_multiplier,
            'quality_bonus': int(quality_bonus),
            'innovation_bonus': innovation_bonus,
            'active_upgrades': active_upgrades,
            'total_points': total_points
        }
    
    def _search_uses_tech(self, search_type: str, tech_id: str) -> bool:
        """Check if search type uses specific tech"""
        tech_mapping = {
            'ai_powered': ['ai', 'ml', 'machine_learning', 'intelligent'],
            'semantic': ['semantic', 'meaning', 'context'],
            'voice': ['voice', 'audio', 'spoken'],
            'visual': ['visual', 'image', 'picture', 'photo'],
            'predictive': ['predictive', 'suggest', 'autocomplete'],
            'contextual': ['contextual', 'context', 'situational'],
            'federated': ['federated', 'multi_source', 'aggregated']
        }
        
        search_lower = search_type.lower()
        tech_keywords = tech_mapping.get(tech_id, [])
        
        return any(keyword in search_lower for keyword in tech_keywords) or search_type == 'all'
    
    def _update_analytics(self, query: str, search_type: str, points: int):
        """Update search analytics"""
        if query not in self.search_analytics:
            self.search_analytics[query] = {
                'count': 0,
                'total_points': 0,
                'search_types': {},
                'avg_points': 0
            }
        
        analytics = self.search_analytics[query]
        analytics['count'] += 1
        analytics['total_points'] += points
        analytics['search_types'][search_type] = analytics['search_types'].get(search_type, 0) + 1
        analytics['avg_points'] = analytics['total_points'] / analytics['count']
    
    def get_search_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user search statistics"""
        searches = self.user_search_history.get(user_id, [])
        
        if not searches:
            return {
                'total_searches': 0,
                'total_points': 0,
                'avg_points_per_search': 0,
                'most_used_tech': None
            }
        
        total_points = sum(s['points_awarded'] for s in searches)
        tech_usage = {}
        
        for search in searches:
            for tech in search.get('tech_upgrades_used', []):
                tech_usage[tech] = tech_usage.get(tech, 0) + 1
        
        most_used_tech = max(tech_usage.items(), key=lambda x: x[1])[0] if tech_usage else None
        
        return {
            'total_searches': len(searches),
            'total_points': total_points,
            'avg_points_per_search': total_points / len(searches),
            'most_used_tech': most_used_tech,
            'tech_usage': tech_usage,
            'recent_searches': searches[-10:]
        }
    
    def enable_tech_upgrade(self, tech_id: str, enabled: bool = True):
        """Enable or disable a tech upgrade"""
        if tech_id in self.tech_upgrades:
            self.tech_upgrades[tech_id]['enabled'] = enabled
            logger.info(f"Tech upgrade '{tech_id}' {'enabled' if enabled else 'disabled'}")
            return True
        return False
    
    def get_tech_upgrades_status(self) -> Dict[str, Any]:
        """Get status of all tech upgrades"""
        return {
            tech_id: {
                'name': tech_data['name'],
                'description': tech_data['description'],
                'multiplier': tech_data['multiplier'],
                'enabled': tech_data['enabled']
            }
            for tech_id, tech_data in self.tech_upgrades.items()
        }

from datetime import datetime
search_intelligence = SearchIntelligence()
