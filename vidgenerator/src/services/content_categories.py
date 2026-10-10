"""
Content Category Service
Manages content categories: underholdning (entertainment), porn, rettigheder (rights)
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from src.db.models import db

# Import models - try to import at module level
ContentCategory = None
CategoryStats = None

try:
    from src.db.models_content_categories import ContentCategory, CategoryStats
except ImportError:
    # Models may not be imported in app context yet
    pass


class ContentCategoryService:
    """Service for managing content categories"""
    
    # Default categories
    DEFAULT_CATEGORIES = {
        'underholdning': {
            'name': 'entertainment',
            'name_da': 'Underholdning',
            'description': 'Entertainment content including movies, music, comedy, and fun videos',
            'description_da': 'Underholdningsindhold inkluderer film, musik, komedie og sjove videoer',
            'sort_order': 1
        },
        'porn': {
            'name': 'porn',
            'name_da': 'Porno',
            'description': 'Adult content',
            'description_da': 'Voksenindhold',
            'sort_order': 2
        },
        'rettigheder': {
            'name': 'rights',
            'name_da': 'Rettigheder',
            'description': 'Content about rights, legal issues, and social justice',
            'description_da': 'Indhold om rettigheder, juridiske spørgsmål og social retfærdighed',
            'sort_order': 3
        }
    }
    
    def __init__(self):
        """Initialize category service"""
        self._ensure_default_categories()
    
    def _ensure_default_categories(self):
        """Ensure default categories exist in database"""
        if not ContentCategory:
            return  # Models not available
        
        try:
            for category_key, category_data in self.DEFAULT_CATEGORIES.items():
                existing = ContentCategory.query.filter_by(name=category_data['name']).first()
                if not existing:
                    category = ContentCategory(
                        id=str(uuid.uuid4()),
                        name=category_data['name'],
                        name_da=category_data['name_da'],
                        description=category_data['description'],
                        description_da=category_data['description_da'],
                        sort_order=category_data['sort_order'],
                        is_active=True
                    )
                    db.session.add(category)
            
            db.session.commit()
        except Exception as e:
            print(f"[ContentCategoryService] Error ensuring default categories: {e}")
            db.session.rollback()
    
    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Get all active categories"""
        if not ContentCategory:
            # Return default categories if models not available
            return [{'id': k, **v} for k, v in self.DEFAULT_CATEGORIES.items()]
        
        try:
            categories = ContentCategory.query.filter_by(is_active=True).order_by(ContentCategory.sort_order).all()
            return [cat.to_dict() for cat in categories]
        except Exception as e:
            print(f"[ContentCategoryService] Error getting categories: {e}")
            return [{'id': k, **v} for k, v in self.DEFAULT_CATEGORIES.items()]
    
    def get_category_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get category by name (supports both English and Danish names)"""
        if not ContentCategory:
            # Return from defaults
            for key, data in self.DEFAULT_CATEGORIES.items():
                if data['name'] == name or data['name_da'] == name:
                    return {'id': key, **data}
            return None
        
        try:
            category = ContentCategory.query.filter(
                (ContentCategory.name == name) | (ContentCategory.name_da == name)
            ).first()
            return category.to_dict() if category else None
        except Exception as e:
            print(f"[ContentCategoryService] Error getting category: {e}")
            return None
    
    def get_category_stats(self, category_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a category"""
        if not CategoryStats:
            return {}
        
        try:
            query = CategoryStats.query.filter_by(category_id=category_id, period_type='all')
            if user_id:
                query = query.filter_by(user_id=user_id)
            else:
                query = query.filter_by(user_id=None)  # Global stats
            
            stats = query.first()
            if stats:
                return stats.to_dict()
            else:
                # Return empty stats
                return {
                    'category_id': category_id,
                    'documentaries_created': 0,
                    'documentaries_completed': 0,
                    'total_views': 0,
                    'average_quality': 0.0
                }
        except Exception as e:
            print(f"[ContentCategoryService] Error getting category stats: {e}")
            return {}
    
    def update_category_stats(self, category_id: str, stats_data: Dict[str, Any], user_id: Optional[str] = None):
        """Update statistics for a category"""
        if not CategoryStats:
            return
        
        try:
            stats = CategoryStats.query.filter_by(
                category_id=category_id,
                user_id=user_id,
                period_type='all'
            ).first()
            
            if not stats:
                stats = CategoryStats(
                    id=str(uuid.uuid4()),
                    category_id=category_id,
                    user_id=user_id,
                    period_type='all'
                )
                db.session.add(stats)
            
            # Update stats
            for key, value in stats_data.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            
            stats.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            print(f"[ContentCategoryService] Error updating category stats: {e}")
            db.session.rollback()
    
    def increment_category_stat(self, category_id: str, stat_name: str, amount: int = 1, user_id: Optional[str] = None):
        """Increment a statistic for a category"""
        if not CategoryStats:
            return
        
        try:
            stats = CategoryStats.query.filter_by(
                category_id=category_id,
                user_id=user_id,
                period_type='all'
            ).first()
            
            if not stats:
                stats = CategoryStats(
                    id=str(uuid.uuid4()),
                    category_id=category_id,
                    user_id=user_id,
                    period_type='all'
                )
                db.session.add(stats)
            
            # Increment stat
            current_value = getattr(stats, stat_name, 0) or 0
            setattr(stats, stat_name, current_value + amount)
            
            stats.updated_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            print(f"[ContentCategoryService] Error incrementing category stat: {e}")
            db.session.rollback()


# Global instance
content_category_service = ContentCategoryService()

