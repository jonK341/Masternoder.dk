"""
Battle Arena Gear System
Comprehensive gear system with calculator integration and JSON storage
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import json
import os
import random

try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    from backend.services.unified_point_counter import unified_point_counter
except ImportError:
    advanced_intelligent_calculator = None
    unified_point_counter = None


class BattleArenaGearSystem:
    """
    Battle Arena Gear System with:
    - Gear definitions and stats
    - Calculator integration for dynamic stats
    - JSON file storage
    - Division-based gear generation
    """
    
    def __init__(self):
        self.gear_definitions = self._initialize_gear_definitions()
        self.user_gear = defaultdict(dict)  # {user_id: {slot: gear_id}}
        self.user_gear_inventory = defaultdict(dict)  # {user_id: {gear_id: quantity}}
        self.gear_points_file = 'battle_arena_gear_points.json'
        self.user_gear_data_file = 'battle_arena_user_gear.json'
        self._load_gear_data()
    
    def _initialize_gear_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize gear definitions with base stats"""
        return {
            # Head Gear
            'helmet_warrior': {
                'id': 'helmet_warrior',
                'name': 'Warrior Helmet',
                'type': 'head',
                'rarity': 'common',
                'base_defense': 10,
                'base_attack': 0,
                'base_health': 20,
                'icon': '⛑️',
                'description': 'Basic warrior helmet'
            },
            'helmet_elite': {
                'id': 'helmet_elite',
                'name': 'Elite Helmet',
                'type': 'head',
                'rarity': 'rare',
                'base_defense': 25,
                'base_attack': 5,
                'base_health': 50,
                'icon': '🪖',
                'description': 'Elite combat helmet'
            },
            'crown_legendary': {
                'id': 'crown_legendary',
                'name': 'Legendary Crown',
                'type': 'head',
                'rarity': 'legendary',
                'base_defense': 50,
                'base_attack': 20,
                'base_health': 100,
                'icon': '👑',
                'description': 'Legendary battle crown'
            },
            # Weapon Gear
            'sword_basic': {
                'id': 'sword_basic',
                'name': 'Basic Sword',
                'type': 'weapon',
                'rarity': 'common',
                'base_defense': 0,
                'base_attack': 15,
                'base_health': 0,
                'icon': '⚔️',
                'description': 'Basic combat sword'
            },
            'sword_enhanced': {
                'id': 'sword_enhanced',
                'name': 'Enhanced Sword',
                'type': 'weapon',
                'rarity': 'rare',
                'base_defense': 5,
                'base_attack': 35,
                'base_health': 10,
                'icon': '🗡️',
                'description': 'Enhanced battle sword'
            },
            'sword_legendary': {
                'id': 'sword_legendary',
                'name': 'Legendary Blade',
                'type': 'weapon',
                'rarity': 'legendary',
                'base_defense': 15,
                'base_attack': 75,
                'base_health': 30,
                'icon': '⚔️',
                'description': 'Legendary weapon of power'
            },
            # Armor Gear
            'armor_basic': {
                'id': 'armor_basic',
                'name': 'Basic Armor',
                'type': 'armor',
                'rarity': 'common',
                'base_defense': 20,
                'base_attack': 0,
                'base_health': 40,
                'icon': '🛡️',
                'description': 'Basic protective armor'
            },
            'armor_heavy': {
                'id': 'armor_heavy',
                'name': 'Heavy Armor',
                'type': 'armor',
                'rarity': 'rare',
                'base_defense': 50,
                'base_attack': 0,
                'base_health': 100,
                'icon': '🛡️',
                'description': 'Heavy defensive armor'
            },
            'armor_legendary': {
                'id': 'armor_legendary',
                'name': 'Legendary Armor',
                'type': 'armor',
                'rarity': 'legendary',
                'base_defense': 100,
                'base_attack': 10,
                'base_health': 200,
                'icon': '🛡️',
                'description': 'Legendary protective armor'
            },
            # Accessory Gear
            'ring_power': {
                'id': 'ring_power',
                'name': 'Power Ring',
                'type': 'accessory',
                'rarity': 'rare',
                'base_defense': 5,
                'base_attack': 15,
                'base_health': 20,
                'icon': '💍',
                'description': 'Ring of power'
            },
            'amulet_protection': {
                'id': 'amulet_protection',
                'name': 'Protection Amulet',
                'type': 'accessory',
                'rarity': 'epic',
                'base_defense': 20,
                'base_attack': 10,
                'base_health': 50,
                'icon': '🔮',
                'description': 'Amulet of protection'
            },
            # Boots Gear
            'boots_swift': {
                'id': 'boots_swift',
                'name': 'Swift Boots',
                'type': 'boots',
                'rarity': 'common',
                'base_defense': 5,
                'base_attack': 5,
                'base_health': 10,
                'icon': '👢',
                'description': 'Swift movement boots'
            },
            'boots_legendary': {
                'id': 'boots_legendary',
                'name': 'Legendary Boots',
                'type': 'boots',
                'rarity': 'legendary',
                'base_defense': 25,
                'base_attack': 25,
                'base_health': 50,
                'icon': '👢',
                'description': 'Legendary movement boots'
            }
        }
    
    def _load_gear_data(self):
        """Load gear points and user gear data from JSON files"""
        # Load gear points
        if os.path.exists(self.gear_points_file):
            try:
                with open(self.gear_points_file, 'r', encoding='utf-8') as f:
                    self.gear_points = json.load(f)
            except:
                self.gear_points = {}
        else:
            self.gear_points = {}
        
        # Load user gear data
        if os.path.exists(self.user_gear_data_file):
            try:
                with open(self.user_gear_data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.user_gear = defaultdict(dict, loaded_data.get('equipped', {}))
                    self.user_gear_inventory = defaultdict(dict, loaded_data.get('inventory', {}))
            except:
                pass
    
    def _save_gear_data(self):
        """Save gear points and user gear data to JSON files"""
        # Save gear points
        try:
            with open(self.gear_points_file, 'w', encoding='utf-8') as f:
                json.dump(self.gear_points, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving gear points: {e}", flush=True)
        
        # Save user gear data
        try:
            data = {
                'equipped': dict(self.user_gear),
                'inventory': dict(self.user_gear_inventory),
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.user_gear_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving user gear data: {e}", flush=True)
    
    def get_user_divisions(self, user_id: str) -> Dict[str, Any]:
        """
        Get user division data with Identification fields:
        - my Index
        - my egos subconscious preferences
        - My mobil
        - Invalideret Visual brian sector
        """
        divisions = {
            'my_index': 0,
            'egos_subconscious_preferences': {},
            'my_mobil': {},
            'invalideret_visual_brian_sector': {}
        }
        
        try:
            # Try to get from user profile preferences
            from src.db.models import UserProfile, db
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            if profile:
                # Get Index from level or total_xp
                divisions['my_index'] = getattr(profile, 'level', 0) or getattr(profile, 'total_xp', 0) or 0
                
                # Get egos subconscious preferences from preferences JSON
                if hasattr(profile, 'preferences') and profile.preferences:
                    try:
                        prefs = json.loads(profile.preferences) if isinstance(profile.preferences, str) else profile.preferences
                        divisions['egos_subconscious_preferences'] = prefs.get('subconscious', {}) or {}
                    except:
                        pass
                
                # Get mobil data (mobile device info) from settings
                if hasattr(profile, 'settings') and profile.settings:
                    try:
                        settings = json.loads(profile.settings) if isinstance(profile.settings, str) else profile.settings
                        divisions['my_mobil'] = settings.get('mobile', {}) or {}
                    except:
                        pass
                
                # Get Visual brian sector from catch_stats or engagement_stats
                if hasattr(profile, 'catch_stats') and profile.catch_stats:
                    try:
                        catch_stats = json.loads(profile.catch_stats) if isinstance(profile.catch_stats, str) else profile.catch_stats
                        divisions['invalideret_visual_brian_sector'] = catch_stats.get('visual', {}) or {}
                    except:
                        pass
        except Exception as e:
            print(f"Error getting user divisions: {e}", flush=True)
        
        return divisions
    
    def calculate_gear_stats(self, user_id: str, gear_id: str) -> Dict[str, Any]:
        """
        Calculate gear stats using calculator and division data
        """
        gear_def = self.gear_definitions.get(gear_id)
        if not gear_def:
            return {}
        
        # Get user divisions
        divisions = self.get_user_divisions(user_id)
        
        # Get user points from calculator
        point_data = {}
        if unified_point_counter:
            try:
                all_points = unified_point_counter.get_all_points(user_id)
                point_data = all_points or {}
            except:
                pass
        
        # Calculate enhanced stats using calculator
        base_attack = gear_def.get('base_attack', 0)
        base_defense = gear_def.get('base_defense', 0)
        base_health = gear_def.get('base_health', 0)
        
        # Apply multipliers from divisions
        index_multiplier = 1.0 + (divisions.get('my_index', 0) * 0.01)
        
        # Apply preferences multiplier
        prefs = divisions.get('egos_subconscious_preferences', {})
        prefs_multiplier = 1.0 + (len(prefs) * 0.05)
        
        # Apply mobil multiplier
        mobil = divisions.get('my_mobil', {})
        mobil_multiplier = 1.0 + (len(mobil) * 0.03)
        
        # Apply visual brian sector multiplier
        visual = divisions.get('invalideret_visual_brian_sector', {})
        visual_multiplier = 1.0 + (len(visual) * 0.04)
        
        # Calculate final stats
        total_multiplier = index_multiplier * prefs_multiplier * mobil_multiplier * visual_multiplier
        
        # Use calculator if available
        if advanced_intelligent_calculator:
            try:
                calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                    point_data, user_id
                )
                if calc_result and 'final_calculation' in calc_result:
                    # Apply calculator bonus
                    calc_bonus = calc_result.get('final_calculation', {}).get('total', 0) or 0
                    calc_multiplier = 1.0 + (calc_bonus / 10000.0)  # Scale down large numbers
                    total_multiplier *= calc_multiplier
            except:
                pass
        
        # Calculate final stats
        final_attack = int(base_attack * total_multiplier)
        final_defense = int(base_defense * total_multiplier)
        final_health = int(base_health * total_multiplier)
        
        return {
            'gear_id': gear_id,
            'base_stats': {
                'attack': base_attack,
                'defense': base_defense,
                'health': base_health
            },
            'final_stats': {
                'attack': final_attack,
                'defense': final_defense,
                'health': final_health
            },
            'multipliers': {
                'index': index_multiplier,
                'preferences': prefs_multiplier,
                'mobil': mobil_multiplier,
                'visual': visual_multiplier,
                'total': total_multiplier
            },
            'divisions': divisions
        }
    
    def get_gear_definition(self, gear_id: str) -> Optional[Dict[str, Any]]:
        """Get gear definition"""
        return self.gear_definitions.get(gear_id)
    
    def get_user_gear(self, user_id: str) -> Dict[str, Any]:
        """Get user's equipped gear with calculated stats"""
        equipped = self.user_gear.get(user_id, {})
        gear_list = []
        
        for slot, gear_id in equipped.items():
            gear_def = self.get_gear_definition(gear_id)
            if gear_def:
                stats = self.calculate_gear_stats(user_id, gear_id)
                gear_list.append({
                    **gear_def,
                    'slot': slot,
                    'calculated_stats': stats.get('final_stats', {}),
                    'multipliers': stats.get('multipliers', {})
                })
        
        return {
            'equipped': gear_list,
            'total_stats': self._calculate_total_stats(gear_list)
        }
    
    def _calculate_total_stats(self, gear_list: List[Dict]) -> Dict[str, int]:
        """Calculate total stats from all equipped gear"""
        total = {'attack': 0, 'defense': 0, 'health': 0}
        
        for gear in gear_list:
            stats = gear.get('calculated_stats', {})
            total['attack'] += stats.get('attack', 0)
            total['defense'] += stats.get('defense', 0)
            total['health'] += stats.get('health', 0)
        
        return total
    
    def equip_gear(self, user_id: str, gear_id: str) -> Dict[str, Any]:
        """Equip gear to user"""
        gear_def = self.get_gear_definition(gear_id)
        if not gear_def:
            return {'success': False, 'error': 'Gear not found'}
        
        # Check if user has gear in inventory
        if user_id not in self.user_gear_inventory:
            self.user_gear_inventory[user_id] = {}
        
        if gear_id not in self.user_gear_inventory[user_id]:
            return {'success': False, 'error': 'Gear not in inventory'}
        
        # Equip gear
        if user_id not in self.user_gear:
            self.user_gear[user_id] = {}
        
        slot = gear_def.get('type', 'general')
        self.user_gear[user_id][slot] = gear_id
        
        # Save to JSON
        self._save_gear_data()
        
        # Calculate and save gear points
        stats = self.calculate_gear_stats(user_id, gear_id)
        self._save_gear_points(user_id, gear_id, stats)
        
        return {
            'success': True,
            'gear': gear_def,
            'stats': stats.get('final_stats', {}),
            'message': f"Equipped {gear_def['name']}"
        }
    
    def unequip_gear(self, user_id: str, slot: str) -> Dict[str, Any]:
        """Unequip gear from slot"""
        if user_id not in self.user_gear or slot not in self.user_gear[user_id]:
            return {'success': False, 'error': 'No gear equipped in slot'}
        
        gear_id = self.user_gear[user_id][slot]
        del self.user_gear[user_id][slot]
        
        # Save to JSON
        self._save_gear_data()
        
        return {'success': True, 'message': 'Gear unequipped'}
    
    def add_gear_to_inventory(self, user_id: str, gear_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Add gear to user inventory"""
        gear_def = self.get_gear_definition(gear_id)
        if not gear_def:
            return {'success': False, 'error': 'Gear not found'}
        
        if user_id not in self.user_gear_inventory:
            self.user_gear_inventory[user_id] = {}
        
        if gear_id not in self.user_gear_inventory[user_id]:
            self.user_gear_inventory[user_id][gear_id] = 0
        
        self.user_gear_inventory[user_id][gear_id] += quantity
        
        # Save to JSON
        self._save_gear_data()
        
        return {
            'success': True,
            'gear_id': gear_id,
            'quantity': self.user_gear_inventory[user_id][gear_id]
        }
    
    def get_inventory(self, user_id: str) -> Dict[str, Any]:
        """Get user gear inventory"""
        inventory = self.user_gear_inventory.get(user_id, {})
        equipped = self.user_gear.get(user_id, {})
        
        inventory_list = []
        for gear_id, quantity in inventory.items():
            gear_def = self.get_gear_definition(gear_id)
            if gear_def:
                stats = self.calculate_gear_stats(user_id, gear_id)
                inventory_list.append({
                    **gear_def,
                    'quantity': quantity,
                    'equipped': gear_id in equipped.values(),
                    'calculated_stats': stats.get('final_stats', {})
                })
        
        return {
            'inventory': inventory_list,
            'equipped_slots': equipped
        }
    
    def _save_gear_points(self, user_id: str, gear_id: str, stats: Dict[str, Any]):
        """Save gear points to JSON file"""
        if user_id not in self.gear_points:
            self.gear_points[user_id] = {}
        
        self.gear_points[user_id][gear_id] = {
            'stats': stats.get('final_stats', {}),
            'multipliers': stats.get('multipliers', {}),
            'divisions': stats.get('divisions', {}),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self._save_gear_data()
    
    def get_gear_points(self, user_id: str) -> Dict[str, Any]:
        """Get saved gear points for user"""
        return self.gear_points.get(user_id, {})
    
    def generate_gear_from_divisions(self, user_id: str, gear_type: str = None) -> Dict[str, Any]:
        """
        Generate gear based on user divisions using calculator
        """
        divisions = self.get_user_divisions(user_id)
        
        # Get point data
        point_data = {}
        if unified_point_counter:
            try:
                point_data = unified_point_counter.get_all_points(user_id) or {}
            except:
                pass
        
        # Use calculator to generate gear stats
        if advanced_intelligent_calculator:
            try:
                calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                    point_data, user_id
                )
                
                # Generate gear based on calculator results
                final_calc = calc_result.get('final_calculation', {}) if calc_result else {}
                total_points = final_calc.get('total', 0) or 0
                
                # Determine gear rarity based on points
                if total_points > 100000:
                    rarity = 'legendary'
                elif total_points > 50000:
                    rarity = 'epic'
                elif total_points > 10000:
                    rarity = 'rare'
                else:
                    rarity = 'common'
                
                # Filter gear by type and rarity
                available_gear = [
                    gid for gid, gdef in self.gear_definitions.items()
                    if (gear_type is None or gdef.get('type') == gear_type)
                    and gdef.get('rarity') == rarity
                ]
                
                if available_gear:
                    gear_id = random.choice(available_gear)
                    return self.add_gear_to_inventory(user_id, gear_id, 1)
            except Exception as e:
                print(f"Error generating gear from divisions: {e}", flush=True)
        
        return {'success': False, 'error': 'Could not generate gear'}


# Global instance
battle_arena_gear_system = BattleArenaGearSystem()

