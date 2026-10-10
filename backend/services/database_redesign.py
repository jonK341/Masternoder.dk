"""
Database Redesign - Enhanced content structure with valuable items
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from enum import Enum


class ContentType(Enum):
    """Content types"""
    VIDEO = "video"
    DOCUMENTARY = "documentary"
    BATTLE_REPLAY = "battle_replay"
    TUTORIAL = "tutorial"
    ARTWORK = "artwork"
    MUSIC = "music"
    COLLECTIBLE = "collectible"
    ACHIEVEMENT = "achievement"
    TROPHY = "trophy"
    ITEM = "item"


class ContentRarity(Enum):
    """Content rarity levels"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class ValuableContent:
    """Represents valuable content item"""
    
    def __init__(self, content_id: str, title: str, content_type: ContentType, 
                 rarity: ContentRarity, value: int, description: str = ''):
        self.id = content_id
        self.title = title
        self.type = content_type
        self.rarity = rarity
        self.value = value
        self.description = description
        self.created_at = datetime.utcnow()
        self.views = 0
        self.likes = 0
        self.shares = 0
        self.owner_id = None
        self.metadata = {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type.value,
            'rarity': self.rarity.value,
            'value': self.value,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'views': self.views,
            'likes': self.likes,
            'shares': self.shares,
            'owner_id': self.owner_id,
            'metadata': self.metadata
        }


class DatabaseRedesign:
    """Redesigned database with valuable content structure"""
    
    def __init__(self):
        self.content = {}  # {content_id: ValuableContent}
        self.user_content = defaultdict(list)  # {user_id: [content_ids]}
        self.content_index = {}  # {content_type: [content_ids]}
        self._initialize_valuable_content()
    
    def _initialize_valuable_content(self):
        """Initialize valuable content items"""
        valuable_items = [
            ValuableContent('doc_epic_battle', 'Epic Battle Documentary', ContentType.DOCUMENTARY, 
                          ContentRarity.LEGENDARY, 5000, 'Complete battle documentary with high production value'),
            ValuableContent('video_tutorial_master', 'Master Tutorial Series', ContentType.TUTORIAL,
                          ContentRarity.EPIC, 3000, 'Comprehensive tutorial series'),
            ValuableContent('artwork_legendary', 'Legendary Artwork Collection', ContentType.ARTWORK,
                          ContentRarity.MYTHIC, 10000, 'Rare artwork collection'),
            ValuableContent('music_epic_score', 'Epic Battle Score', ContentType.MUSIC,
                          ContentRarity.EPIC, 2500, 'Original battle music score'),
            ValuableContent('collectible_rare_card', 'Rare Collectible Card', ContentType.COLLECTIBLE,
                          ContentRarity.RARE, 1500, 'Limited edition collectible'),
            ValuableContent('achievement_master', 'Master Achievement', ContentType.ACHIEVEMENT,
                          ContentRarity.LEGENDARY, 5000, 'Ultimate achievement unlock'),
            ValuableContent('trophy_champion', 'Champion Trophy', ContentType.TROPHY,
                          ContentRarity.MYTHIC, 10000, 'Championship trophy'),
            ValuableContent('item_legendary_weapon', 'Legendary Weapon', ContentType.ITEM,
                          ContentRarity.LEGENDARY, 7500, 'Powerful legendary weapon'),
        ]
        
        for item in valuable_items:
            self.content[item.id] = item
            if item.type.value not in self.content_index:
                self.content_index[item.type.value] = []
            self.content_index[item.type.value].append(item.id)
    
    def create_content(self, title: str, content_type: ContentType, rarity: ContentRarity,
                      value: int, description: str = '', owner_id: str = None) -> Dict[str, Any]:
        """Create new valuable content"""
        content_id = str(uuid.uuid4())
        content = ValuableContent(content_id, title, content_type, rarity, value, description)
        content.owner_id = owner_id
        
        self.content[content_id] = content
        
        if owner_id:
            self.user_content[owner_id].append(content_id)
        
        if content_type.value not in self.content_index:
            self.content_index[content_type.value] = []
        self.content_index[content_type.value].append(content_id)
        
        return {
            'success': True,
            'content_id': content_id,
            'content': content.to_dict()
        }
    
    def get_content_by_type(self, content_type: str) -> List[Dict]:
        """Get content by type"""
        content_ids = self.content_index.get(content_type, [])
        return [self.content.get(cid).to_dict() for cid in content_ids if cid in self.content]
    
    def get_content_by_rarity(self, rarity: str) -> List[Dict]:
        """Get content by rarity"""
        return [c.to_dict() for c in self.content.values() if c.rarity.value == rarity]
    
    def get_user_content(self, user_id: str) -> List[Dict]:
        """Get user's content"""
        content_ids = self.user_content.get(user_id, [])
        return [self.content.get(cid).to_dict() for cid in content_ids if cid in self.content]
    
    def get_valuable_content(self, min_value: int = 1000) -> List[Dict]:
        """Get valuable content above minimum value"""
        return [c.to_dict() for c in self.content.values() if c.value >= min_value]
    
    def update_content_stats(self, content_id: str, views: int = 0, likes: int = 0, shares: int = 0) -> Dict[str, Any]:
        """Update content statistics"""
        content = self.content.get(content_id)
        if not content:
            return {'success': False, 'error': 'Content not found'}
        
        content.views += views
        content.likes += likes
        content.shares += shares
        
        return {
            'success': True,
            'content': content.to_dict()
        }


# Global instance
database_redesign = DatabaseRedesign()

