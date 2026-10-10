"""
Keyword Integration System
Integrates translated keywords into Stats, Service Worker, and AI systems
"""

from .keyword_foundation import (
    PROCESSED_KEYWORDS,
    translate_keyword,
    get_keyword_category,
    get_keyword_power_level,
    KEYWORD_CATEGORIES
)

class KeywordStatsIntegrator:
    """Integrate keywords into stats system"""
    
    def __init__(self):
        self.keywords = PROCESSED_KEYWORDS
        self.stats_mapping = {
            'power': 'power_stat',
            'conflict': 'conflict_stat',
            'knowledge': 'knowledge_stat',
            'negative': 'negative_stat',
            'social': 'social_stat',
            'financial': 'financial_stat',
            'health': 'health_stat',
            'legal': 'legal_stat',
            'game_mechanics': 'game_mechanics_stat',
            'temporal': 'temporal_stat',
            'spatial': 'spatial_stat',
        }
    
    def update_stats_from_keywords(self, stats_counter, keywords_used):
        """Update stats based on keywords used"""
        category_counts = {}
        total_power = 0
        
        for keyword_data in keywords_used:
            category = keyword_data['category']
            power_level = keyword_data['power_level']
            
            # Count by category
            category_counts[category] = category_counts.get(category, 0) + 1
            total_power += power_level
        
        # Update stats
        for category, count in category_counts.items():
            stat_name = self.stats_mapping.get(category, 'unknown_stat')
            if hasattr(stats_counter, stat_name):
                current_value = getattr(stats_counter, stat_name, 0)
                setattr(stats_counter, stat_name, current_value + count)
        
        # Update total power
        if hasattr(stats_counter, 'total_power'):
            stats_counter.total_power = getattr(stats_counter, 'total_power', 0) + total_power
        
        return {
            'categories_updated': category_counts,
            'total_power_added': total_power
        }

class KeywordServiceWorkerIntegrator:
    """Integrate keywords into service worker intelligence"""
    
    def __init__(self):
        self.keywords = PROCESSED_KEYWORDS
        self.active_keywords = []
    
    def activate_keyword(self, keyword_english):
        """Activate a keyword for use in service worker"""
        for kw in self.keywords:
            if kw['english'] == keyword_english:
                kw['active'] = True
                if kw not in self.active_keywords:
                    self.active_keywords.append(kw)
                return kw
        return None
    
    def get_active_keywords_for_context(self, context):
        """Get relevant active keywords for a given context"""
        relevant = []
        for kw in self.active_keywords:
            if kw['category'] in context.get('categories', []):
                relevant.append(kw)
        return relevant
    
    def enhance_intelligence_with_keywords(self, intelligence_data):
        """Enhance service worker intelligence with keyword context"""
        enhanced = intelligence_data.copy()
        
        # Add keyword context
        enhanced['keyword_context'] = {
            'active_count': len(self.active_keywords),
            'categories': list(set(kw['category'] for kw in self.active_keywords)),
            'total_power': sum(kw['power_level'] for kw in self.active_keywords),
            'keywords': [kw['english'] for kw in self.active_keywords]
        }
        
        return enhanced

class KeywordAIIntegrator:
    """Integrate keywords into AI generation system"""
    
    def __init__(self):
        self.keywords = PROCESSED_KEYWORDS
    
    def build_ai_prompt_with_keywords(self, base_prompt, active_keywords):
        """Build AI prompt enhanced with keyword context"""
        keyword_context = []
        
        for kw in active_keywords:
            if kw['active']:
                keyword_context.append(f"{kw['english']} (power: {kw['power_level']}, category: {kw['category']})")
        
        if keyword_context:
            enhanced_prompt = f"{base_prompt}\n\nKeyword Context:\n" + "\n".join(keyword_context)
        else:
            enhanced_prompt = base_prompt
        
        return enhanced_prompt
    
    def extract_keywords_from_content(self, content):
        """Extract relevant keywords from generated content"""
        found_keywords = []
        content_lower = content.lower()
        
        for kw in self.keywords:
            if kw['english'].lower() in content_lower:
                found_keywords.append(kw)
        
        return found_keywords
    
    def calculate_content_power_score(self, content, active_keywords):
        """Calculate power score for generated content based on keywords"""
        found_keywords = self.extract_keywords_from_content(content)
        power_score = sum(kw['power_level'] for kw in found_keywords)
        
        # Bonus for active keywords
        active_found = [kw for kw in found_keywords if kw in active_keywords]
        if active_found:
            power_score += len(active_found) * 2
        
        return power_score

# Global instances
keyword_stats_integrator = KeywordStatsIntegrator()
keyword_worker_integrator = KeywordServiceWorkerIntegrator()
keyword_ai_integrator = KeywordAIIntegrator()

