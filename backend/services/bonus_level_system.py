"""
Bonus Level System - Toons and Pegasus
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from enum import Enum


class ToonType(Enum):
    """Toon (cartoon character) types"""
    HERO = "hero"
    VILLAIN = "villain"
    COMEDIAN = "comedian"
    MAGE = "mage"
    WARRIOR = "warrior"
    ANIMAL = "animal"


class PegasusType(Enum):
    """Pegasus types"""
    CLASSIC = "classic"
    FIRE = "fire"
    ICE = "ice"
    LIGHTNING = "lightning"
    SHADOW = "shadow"
    RAINBOW = "rainbow"
    LEGENDARY = "legendary"


class Toon:
    """Represents a cartoon character"""
    
    def __init__(self, toon_id: str, name: str, toon_type: ToonType, 
                 health: int, attack: int, defense: int):
        self.id = toon_id
        self.name = name
        self.type = toon_type
        self.health = health
        self.max_health = health
        self.attack = attack
        self.defense = defense
        self.level = 1
        self.experience = 0
        self.abilities = []
        self.description = ""
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'health': self.health,
            'max_health': self.max_health,
            'attack': self.attack,
            'defense': self.defense,
            'level': self.level,
            'experience': self.experience,
            'abilities': self.abilities,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }


class Pegasus:
    """Represents a Pegasus creature"""
    
    def __init__(self, pegasus_id: str, name: str, pegasus_type: PegasusType,
                 health: int, speed: int, magic: int):
        self.id = pegasus_id
        self.name = name
        self.type = pegasus_type
        self.health = health
        self.max_health = health
        self.speed = speed
        self.magic = magic
        self.level = 1
        self.experience = 0
        self.abilities = []
        self.description = ""
        self.created_at = datetime.utcnow()
        self.can_fly = True
        self.wing_span = 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type.value,
            'health': self.health,
            'max_health': self.max_health,
            'speed': self.speed,
            'magic': self.magic,
            'level': self.level,
            'experience': self.experience,
            'abilities': self.abilities,
            'description': self.description,
            'can_fly': self.can_fly,
            'wing_span': self.wing_span,
            'created_at': self.created_at.isoformat()
        }


class BonusLevel:
    """Represents a bonus level"""
    
    def __init__(self, level_id: str, name: str, difficulty: str,
                 toons: List[str], pegasus_list: List[str]):
        self.id = level_id
        self.name = name
        self.difficulty = difficulty  # easy, normal, hard, extreme
        self.toons = toons  # List of toon IDs
        self.pegasus_list = pegasus_list  # List of pegasus IDs
        self.created_at = datetime.utcnow()
        self.completed_by = []
        self.rewards = {}
        self.description = ""
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'difficulty': self.difficulty,
            'toons': self.toons,
            'pegasus_list': self.pegasus_list,
            'completed_by': self.completed_by,
            'rewards': self.rewards,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }


class BonusLevelSystem:
    """Manages bonus levels with Toons and Pegasus"""
    
    def __init__(self):
        self.toons = {}  # {toon_id: Toon}
        self.pegasus_creatures = {}  # {pegasus_id: Pegasus}
        self.bonus_levels = {}  # {level_id: BonusLevel}
        self.user_progress = defaultdict(dict)  # {user_id: {level_id: progress}}
        self._initialize_toons()
        self._initialize_pegasus()
        self._initialize_bonus_levels()
    
    def _initialize_toons(self):
        """Initialize cartoon characters"""
        toons = [
            # Heroes
            Toon('toon_hero_brave', 'Brave Hero', ToonType.HERO, 150, 30, 20),
            Toon('toon_hero_wise', 'Wise Hero', ToonType.HERO, 120, 25, 25),
            Toon('toon_hero_swift', 'Swift Hero', ToonType.HERO, 100, 35, 15),
            
            # Villains
            Toon('toon_villain_dark', 'Dark Villain', ToonType.VILLAIN, 180, 40, 18),
            Toon('toon_villain_sneaky', 'Sneaky Villain', ToonType.VILLAIN, 130, 30, 20),
            
            # Comedians
            Toon('toon_comedian_joker', 'Joker Comedian', ToonType.COMEDIAN, 90, 20, 15),
            Toon('toon_comedian_clown', 'Clown Comedian', ToonType.COMEDIAN, 80, 15, 10),
            
            # Mages
            Toon('toon_mage_wizard', 'Wizard Mage', ToonType.MAGE, 100, 50, 10),
            Toon('toon_mage_sorcerer', 'Sorcerer Mage', ToonType.MAGE, 110, 45, 12),
            
            # Warriors
            Toon('toon_warrior_knight', 'Knight Warrior', ToonType.WARRIOR, 200, 35, 30),
            Toon('toon_warrior_barbarian', 'Barbarian Warrior', ToonType.WARRIOR, 180, 40, 25),
            
            # Animals
            Toon('toon_animal_bear', 'Bear Animal', ToonType.ANIMAL, 160, 30, 20),
            Toon('toon_animal_wolf', 'Wolf Animal', ToonType.ANIMAL, 120, 35, 15),
        ]
        
        for toon in toons:
            toon.description = f"A {toon.type.value} toon: {toon.name}"
            toon.abilities = self._get_toon_abilities(toon.type)
            self.toons[toon.id] = toon
    
    def _get_toon_abilities(self, toon_type: ToonType) -> List[str]:
        """Get abilities for toon type"""
        abilities_map = {
            ToonType.HERO: ['Heroic Strike', 'Brave Charge', 'Protect Ally'],
            ToonType.VILLAIN: ['Dark Strike', 'Sneak Attack', 'Intimidate'],
            ToonType.COMEDIAN: ['Joke Attack', 'Confuse Enemy', 'Laugh'],
            ToonType.MAGE: ['Magic Missile', 'Fireball', 'Shield'],
            ToonType.WARRIOR: ['Power Strike', 'Charge', 'Defend'],
            ToonType.ANIMAL: ['Claw Attack', 'Roar', 'Fury']
        }
        return abilities_map.get(toon_type, [])
    
    def _initialize_pegasus(self):
        """Initialize Pegasus creatures"""
        pegasus_list = [
            # Classic Pegasus
            Pegasus('pegasus_classic_white', 'White Classic Pegasus', PegasusType.CLASSIC, 200, 80, 30),
            Pegasus('pegasus_classic_golden', 'Golden Classic Pegasus', PegasusType.CLASSIC, 220, 85, 35),
            
            # Fire Pegasus
            Pegasus('pegasus_fire_flame', 'Flame Fire Pegasus', PegasusType.FIRE, 180, 90, 50),
            Pegasus('pegasus_fire_inferno', 'Inferno Fire Pegasus', PegasusType.FIRE, 200, 95, 60),
            
            # Ice Pegasus
            Pegasus('pegasus_ice_frost', 'Frost Ice Pegasus', PegasusType.ICE, 190, 75, 45),
            Pegasus('pegasus_ice_glacier', 'Glacier Ice Pegasus', PegasusType.ICE, 210, 80, 55),
            
            # Lightning Pegasus
            Pegasus('pegasus_lightning_storm', 'Storm Lightning Pegasus', PegasusType.LIGHTNING, 170, 100, 70),
            Pegasus('pegasus_lightning_thunder', 'Thunder Lightning Pegasus', PegasusType.LIGHTNING, 190, 105, 80),
            
            # Shadow Pegasus
            Pegasus('pegasus_shadow_dark', 'Dark Shadow Pegasus', PegasusType.SHADOW, 160, 85, 40),
            Pegasus('pegasus_shadow_void', 'Void Shadow Pegasus', PegasusType.SHADOW, 180, 90, 50),
            
            # Rainbow Pegasus
            Pegasus('pegasus_rainbow_prism', 'Prism Rainbow Pegasus', PegasusType.RAINBOW, 250, 100, 80),
            Pegasus('pegasus_rainbow_aurora', 'Aurora Rainbow Pegasus', PegasusType.RAINBOW, 280, 110, 90),
            
            # Legendary Pegasus
            Pegasus('pegasus_legendary_divine', 'Divine Legendary Pegasus', PegasusType.LEGENDARY, 500, 150, 150),
            Pegasus('pegasus_legendary_celestial', 'Celestial Legendary Pegasus', PegasusType.LEGENDARY, 600, 180, 200),
        ]
        
        for pegasus in pegasus_list:
            pegasus.description = f"A {pegasus.type.value} pegasus: {pegasus.name}"
            pegasus.abilities = self._get_pegasus_abilities(pegasus.type)
            pegasus.wing_span = 10 + (pegasus.level * 2)
            self.pegasus_creatures[pegasus.id] = pegasus
    
    def _get_pegasus_abilities(self, pegasus_type: PegasusType) -> List[str]:
        """Get abilities for pegasus type"""
        abilities_map = {
            PegasusType.CLASSIC: ['Wing Strike', 'Flight', 'Heal'],
            PegasusType.FIRE: ['Fire Breath', 'Wing Strike', 'Fire Flight'],
            PegasusType.ICE: ['Ice Breath', 'Wing Strike', 'Ice Flight'],
            PegasusType.LIGHTNING: ['Lightning Strike', 'Wing Strike', 'Lightning Flight'],
            PegasusType.SHADOW: ['Shadow Strike', 'Wing Strike', 'Shadow Flight'],
            PegasusType.RAINBOW: ['Rainbow Beam', 'Wing Strike', 'Rainbow Flight'],
            PegasusType.LEGENDARY: ['Divine Strike', 'Wing Strike', 'Divine Flight', 'Ultimate Power']
        }
        return abilities_map.get(pegasus_type, ['Wing Strike', 'Flight'])
    
    def _initialize_bonus_levels(self):
        """Initialize bonus levels"""
        bonus_levels = [
            BonusLevel('bonus_level_1', 'Toon Adventure', 'easy',
                      ['toon_hero_brave', 'toon_hero_wise'],
                      ['pegasus_classic_white']),
            BonusLevel('bonus_level_2', 'Pegasus Flight', 'normal',
                      ['toon_hero_swift'],
                      ['pegasus_classic_golden', 'pegasus_fire_flame']),
            BonusLevel('bonus_level_3', 'Toon vs Villain', 'normal',
                      ['toon_hero_brave', 'toon_warrior_knight'],
                      ['pegasus_ice_frost']),
            BonusLevel('bonus_level_4', 'Elemental Pegasus', 'hard',
                      ['toon_mage_wizard', 'toon_warrior_knight'],
                      ['pegasus_fire_inferno', 'pegasus_ice_glacier', 'pegasus_lightning_storm']),
            BonusLevel('bonus_level_5', 'Rainbow Adventure', 'hard',
                      ['toon_hero_wise', 'toon_mage_sorcerer'],
                      ['pegasus_rainbow_prism']),
            BonusLevel('bonus_level_6', 'Legendary Challenge', 'extreme',
                      ['toon_hero_brave', 'toon_warrior_knight', 'toon_mage_wizard'],
                      ['pegasus_legendary_divine', 'pegasus_legendary_celestial']),
        ]
        
        for level in bonus_levels:
            level.description = f"Bonus level: {level.name}"
            level.rewards = {
                'experience': 100 * (['easy', 'normal', 'hard', 'extreme'].index(level.difficulty) + 1),
                'gold': 50 * (['easy', 'normal', 'hard', 'extreme'].index(level.difficulty) + 1),
                'items': []
            }
            self.bonus_levels[level.id] = level
    
    def get_toon(self, toon_id: str) -> Optional[Dict]:
        """Get a toon"""
        toon = self.toons.get(toon_id)
        return toon.to_dict() if toon else None
    
    def get_all_toons(self, toon_type: Optional[ToonType] = None) -> List[Dict]:
        """Get all toons"""
        toons = list(self.toons.values())
        if toon_type:
            toons = [t for t in toons if t.type == toon_type]
        return [t.to_dict() for t in toons]
    
    def get_pegasus(self, pegasus_id: str) -> Optional[Dict]:
        """Get a pegasus"""
        pegasus = self.pegasus_creatures.get(pegasus_id)
        return pegasus.to_dict() if pegasus else None
    
    def get_all_pegasus(self, pegasus_type: Optional[PegasusType] = None) -> List[Dict]:
        """Get all pegasus creatures"""
        pegasus_list = list(self.pegasus_creatures.values())
        if pegasus_type:
            pegasus_list = [p for p in pegasus_list if p.type == pegasus_type]
        return [p.to_dict() for p in pegasus_list]
    
    def get_bonus_level(self, level_id: str) -> Optional[Dict]:
        """Get a bonus level"""
        level = self.bonus_levels.get(level_id)
        if not level:
            return None
        
        # Enrich with toon and pegasus details
        enriched = level.to_dict()
        enriched['toon_details'] = [self.get_toon(tid) for tid in level.toons if self.get_toon(tid)]
        enriched['pegasus_details'] = [self.get_pegasus(pid) for pid in level.pegasus_list if self.get_pegasus(pid)]
        
        return enriched
    
    def get_all_bonus_levels(self) -> List[Dict]:
        """Get all bonus levels"""
        return [self.get_bonus_level(lid) for lid in self.bonus_levels.keys()]
    
    def start_bonus_level(self, user_id: str, level_id: str) -> Dict[str, Any]:
        """Start a bonus level"""
        level = self.bonus_levels.get(level_id)
        if not level:
            return {'success': False, 'error': 'Bonus level not found'}
        
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {}
        
        if level_id not in self.user_progress[user_id]:
            self.user_progress[user_id][level_id] = {
                'started_at': datetime.utcnow().isoformat(),
                'status': 'in_progress',
                'progress': 0
            }
        
        return {
            'success': True,
            'level': self.get_bonus_level(level_id),
            'message': f'Started bonus level: {level.name}'
        }
    
    def complete_bonus_level(self, user_id: str, level_id: str) -> Dict[str, Any]:
        """Complete a bonus level"""
        level = self.bonus_levels.get(level_id)
        if not level:
            return {'success': False, 'error': 'Bonus level not found'}
        
        if user_id not in self.user_progress or level_id not in self.user_progress[user_id]:
            return {'success': False, 'error': 'Level not started'}
        
        self.user_progress[user_id][level_id]['status'] = 'completed'
        self.user_progress[user_id][level_id]['completed_at'] = datetime.utcnow().isoformat()
        self.user_progress[user_id][level_id]['progress'] = 100
        
        if user_id not in level.completed_by:
            level.completed_by.append(user_id)
        
        return {
            'success': True,
            'level': self.get_bonus_level(level_id),
            'rewards': level.rewards,
            'message': f'Completed bonus level: {level.name}'
        }
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user's bonus level progress"""
        progress = self.user_progress.get(user_id, {})
        return {
            'success': True,
            'user_id': user_id,
            'progress': progress,
            'completed_levels': len([p for p in progress.values() if p.get('status') == 'completed']),
            'total_levels': len(self.bonus_levels)
        }


# Global instance
bonus_level_system = BonusLevelSystem()

