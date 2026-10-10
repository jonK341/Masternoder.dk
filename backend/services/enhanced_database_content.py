"""
Enhanced Database Content System - Valuable Content Management
Removes test items and manages valuable content
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class ContentType:
    """Content types"""
    VIDEO = "video"
    DOCUMENTARY = "documentary"
    BATTLE_REPLAY = "battle_replay"
    TUTORIAL = "tutorial"
    ARTWORK = "artwork"
    MUSIC = "music"
    COLLECTIBLE = "collectible"
    ACHIEVEMENT = "achievement"


class ContentQuality:
    """Content quality levels"""
    TEST = "test"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    LEGENDARY = "legendary"


class EnhancedContent:
    """Represents enhanced valuable content"""
    
    def __init__(self, content_id: str, title: str, content_type: str, quality: str):
        self.id = content_id
        self.title = title
        self.type = content_type
        self.quality = quality
        self.created_at = datetime.utcnow()
        self.value_score = 0
        self.metadata = {}
        self.tags = []
        self.is_test = False
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type,
            'quality': self.quality,
            'value_score': self.value_score,
            'metadata': self.metadata,
            'tags': self.tags,
            'is_test': self.is_test,
            'created_at': self.created_at.isoformat()
        }


class EnhancedDatabaseContent:
    """Manages valuable content in database"""
    
    def __init__(self):
        self.content = {}  # {content_id: EnhancedContent}
        self.user_content = defaultdict(list)  # {user_id: [content_ids]}
        self.content_index = {}  # {tag: [content_ids]}
        self.test_items = set()  # Set of test item IDs
    
    def add_content(self, title: str, content_type: str, quality: str, 
                   user_id: str = None, metadata: Dict = None, tags: List = None) -> Dict[str, Any]:
        """Add valuable content"""
        content_id = str(uuid.uuid4())
        content = EnhancedContent(content_id, title, content_type, quality)
        content.metadata = metadata or {}
        content.tags = tags or []
        content.is_test = quality == ContentQuality.TEST
        
        # Calculate value score
        quality_scores = {
            ContentQuality.TEST: 0,
            ContentQuality.BASIC: 10,
            ContentQuality.STANDARD: 50,
            ContentQuality.PREMIUM: 100,
            ContentQuality.LEGENDARY: 500
        }
        content.value_score = quality_scores.get(quality, 0)
        
        self.content[content_id] = content
        
        if user_id:
            self.user_content[user_id].append(content_id)
        
        # Index by tags
        for tag in content.tags:
            if tag not in self.content_index:
                self.content_index[tag] = []
            self.content_index[tag].append(content_id)
        
        if content.is_test:
            self.test_items.add(content_id)
        
        return {
            'success': True,
            'content_id': content_id,
            'content': content.to_dict()
        }
    
    def remove_test_items(self) -> Dict[str, Any]:
        """Remove all test items"""
        removed_count = 0
        
        for test_id in list(self.test_items):
            if test_id in self.content:
                # Remove from user content
                for user_id, content_ids in self.user_content.items():
                    if test_id in content_ids:
                        content_ids.remove(test_id)
                
                # Remove from index
                content = self.content[test_id]
                for tag in content.tags:
                    if tag in self.content_index and test_id in self.content_index[tag]:
                        self.content_index[tag].remove(test_id)
                
                # Remove content
                del self.content[test_id]
                removed_count += 1
        
        self.test_items.clear()
        
        return {
            'success': True,
            'removed_count': removed_count,
            'message': f'Removed {removed_count} test items'
        }
    
    def get_valuable_content(self, min_value_score: int = 10, limit: int = 100) -> List[Dict]:
        """Get valuable content (excluding test items)"""
        valuable = [
            c.to_dict() for c in self.content.values()
            if not c.is_test and c.value_score >= min_value_score
        ]
        valuable.sort(key=lambda x: x['value_score'], reverse=True)
        return valuable[:limit]
    
    def get_user_valuable_content(self, user_id: str) -> List[Dict]:
        """Get user's valuable content"""
        content_ids = self.user_content.get(user_id, [])
        valuable = [
            self.content[cid].to_dict() for cid in content_ids
            if cid in self.content and not self.content[cid].is_test
        ]
        valuable.sort(key=lambda x: x['value_score'], reverse=True)
        return valuable
    
    def search_content(self, query: str, content_type: str = None) -> List[Dict]:
        """Search content by query"""
        results = []
        query_lower = query.lower()
        
        for content in self.content.values():
            if content.is_test:
                continue
            
            if content_type and content.type != content_type:
                continue
            
            # Search in title and tags
            if (query_lower in content.title.lower() or
                any(query_lower in tag.lower() for tag in content.tags)):
                results.append(content.to_dict())
        
        results.sort(key=lambda x: x['value_score'], reverse=True)
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get content statistics"""
        total = len(self.content)
        test_count = len(self.test_items)
        valuable_count = total - test_count
        
        quality_counts = defaultdict(int)
        type_counts = defaultdict(int)
        
        for content in self.content.values():
            if not content.is_test:
                quality_counts[content.quality] += 1
                type_counts[content.type] += 1
        
        return {
            'total_content': total,
            'test_items': test_count,
            'valuable_content': valuable_count,
            'quality_distribution': dict(quality_counts),
            'type_distribution': dict(type_counts)
        }


# Global instance
enhanced_database_content = EnhancedDatabaseContent()

