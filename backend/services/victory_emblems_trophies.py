"""
Victory Emblems and Trophies System
Tracks victories against overpowered goliaths and undermined EGOs
Creates victory emblems and trophies for war victories
Integrates with fantasy monsters, spells, and rulebook systems
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json
import os

logger = logging.getLogger(__name__)

class VictoryEmblem:
    """Represents a victory emblem"""
    
    def __init__(self, emblem_id: str, name: str, description: str,
                 victory_type: str, rarity: str = 'common',
                 icon: str = '🏆', power_level: float = 1.0):
        self.id = emblem_id
        self.name = name
        self.description = description
        self.victory_type = victory_type  # goliath, ego, war, strategic
        self.rarity = rarity  # common, rare, epic, legendary, mythic
        self.icon = icon
        self.power_level = power_level
        self.created_at = datetime.utcnow()
        self.earned_at = None
        self.affection_level = 0.0  # 0.0 to 1.0
        self.shadow_intensity = 0.0  # Shadow from Giga Heaven
        self.cloud_size = 0.0  # Cloud from Giga Heaven
        self.viking_blood_frenzy = 0.0  # 0.0 to 1.33 (133%)
        self.trigger_charges = 0  # Number of times triggered
        self.switch_statement = ""  # The "switching on them" statement
        self.energy_stacked = 0.0  # Energy that stacked over time
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'victory_type': self.victory_type,
            'rarity': self.rarity,
            'icon': self.icon,
            'power_level': self.power_level,
            'created_at': self.created_at.isoformat(),
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'affection_level': self.affection_level,
            'shadow_intensity': self.shadow_intensity,
            'cloud_size': self.cloud_size,
            'viking_blood_frenzy': self.viking_blood_frenzy,
            'trigger_charges': self.trigger_charges,
            'switch_statement': self.switch_statement,
            'energy_stacked': self.energy_stacked
        }


class VictoryTrophy:
    """Represents a victory trophy"""
    
    def __init__(self, trophy_id: str, name: str, description: str,
                 war_id: str, opponent_type: str, victory_method: str,
                 museum_category: str = 'war_victories'):
        self.id = trophy_id
        self.name = name
        self.description = description
        self.war_id = war_id
        self.opponent_type = opponent_type  # goliath, ego, group, criminal
        self.victory_method = victory_method  # strategic, switch_trigger, viking_frenzy, etc.
        self.museum_category = museum_category
        self.created_at = datetime.utcnow()
        self.earned_at = None
        self.war_duration_years = 0
        self.opponent_ignorance_level = 0.0  # 0.0 to 1.0
        self.criminal_mentality_cuts = 0  # Number of rights cut off
        self.final_statement = ""  # The winning statement
        self.overlooked_correct_statement = ""  # Statement that was overlooked
        self.special_forces_attention = False
        self.trigger_timing_seconds = 0  # Seconds before final hit
        self.victory_turned = False  # Whether victory was turned around
        self.jyske_lov_applied = False  # Whether Jyske Lov was applied
        self.fantasy_monster_hunters = []  # List of fantasy monsters hunting for answers
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'war_id': self.war_id,
            'opponent_type': self.opponent_type,
            'victory_method': self.victory_method,
            'museum_category': self.museum_category,
            'created_at': self.created_at.isoformat(),
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'war_duration_years': self.war_duration_years,
            'opponent_ignorance_level': self.opponent_ignorance_level,
            'criminal_mentality_cuts': self.criminal_mentality_cuts,
            'final_statement': self.final_statement,
            'overlooked_correct_statement': self.overlooked_correct_statement,
            'special_forces_attention': self.special_forces_attention,
            'trigger_timing_seconds': self.trigger_timing_seconds,
            'victory_turned': self.victory_turned,
            'jyske_lov_applied': self.jyske_lov_applied,
            'fantasy_monster_hunters': self.fantasy_monster_hunters
        }


class VictoryEmblemsTrophiesSystem:
    """
    Victory Emblems and Trophies System
    Tracks victories, creates emblems and trophies
    Integrates with compass_hourglass_system for fantasy monsters and spells
    """
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # ONE JSON FILE - Rule #1 compliance
        self.data_file = os.path.join(data_dir, 'victory_emblems_trophies.json')
        
        self.victory_emblems = {}  # {user_id: List[VictoryEmblem]}
        self.victory_trophies = {}  # {user_id: List[VictoryTrophy]}
        self.war_history = {}  # {war_id: Dict[str, Any]}
        self.museum_collections = {}  # {user_id: Dict[str, List[Dict]]}
        self.victory_stats = {}  # {user_id: Dict[str, Any]}
        self.goliath_defeats = {}  # {user_id: List[Dict]}
        self.ego_defeats = {}  # {user_id: List[Dict]}
        self.switch_statements = {}  # {user_id: List[Dict]} - "They are switching on them" statements
        self.viking_frenzy_events = {}  # {user_id: List[Dict]}
        self.jyske_lov_records = {}  # {user_id: List[Dict]} - Jyske Lov applications
        
        # Load existing data
        self._load_data()
    
    def create_victory_emblem(self, user_id: str, name: str, description: str,
                             victory_type: str, rarity: str = 'common',
                             icon: str = '🏆', power_level: float = 1.0,
                             switch_statement: str = "",
                             affection_level: float = 0.0,
                             shadow_intensity: float = 0.0,
                             cloud_size: float = 0.0) -> Dict[str, Any]:
        """
        Create a victory emblem
        """
        emblem_id = f"emblem_{user_id}_{datetime.utcnow().timestamp()}"
        
        emblem = VictoryEmblem(
            emblem_id, name, description, victory_type, rarity,
            icon, power_level
        )
        emblem.switch_statement = switch_statement
        emblem.affection_level = affection_level
        emblem.shadow_intensity = shadow_intensity
        emblem.cloud_size = cloud_size
        
        if user_id not in self.victory_emblems:
            self.victory_emblems[user_id] = []
        
        self.victory_emblems[user_id].append(emblem)
        
        # Save to file
        self._save_data()
        
        return {'success': True, 'emblem': emblem.to_dict()}
    
    def create_victory_trophy(self, user_id: str, name: str, description: str,
                             war_id: str, opponent_type: str,
                             victory_method: str,
                             war_duration_years: int = 0,
                             final_statement: str = "",
                             overlooked_statement: str = "",
                             trigger_timing_seconds: int = 0,
                             criminal_mentality_cuts: int = 0) -> Dict[str, Any]:
        """
        Create a victory trophy for a war won
        """
        trophy_id = f"trophy_{user_id}_{datetime.utcnow().timestamp()}"
        
        trophy = VictoryTrophy(
            trophy_id, name, description, war_id, opponent_type,
            victory_method
        )
        trophy.earned_at = datetime.utcnow()
        trophy.war_duration_years = war_duration_years
        trophy.final_statement = final_statement
        trophy.overlooked_correct_statement = overlooked_statement
        trophy.trigger_timing_seconds = trigger_timing_seconds
        trophy.criminal_mentality_cuts = criminal_mentality_cuts
        
        if user_id not in self.victory_trophies:
            self.victory_trophies[user_id] = []
        
        self.victory_trophies[user_id].append(trophy)
        
        # Add to museum collection
        self._add_to_museum(user_id, trophy)
        
        # Save to file
        self._save_data()
        
        return {'success': True, 'trophy': trophy.to_dict()}
    
    def record_goliath_defeat(self, user_id: str, goliath_name: str,
                             goliath_power: float, defeat_method: str,
                             years_of_war: int = 0,
                             switch_statement: str = "They are switching on them now",
                             affection_gained: float = 0.0,
                             shadow_from_giga: float = 0.0,
                             cloud_from_giga: float = 0.0) -> Dict[str, Any]:
        """
        Record a victory against an overpowered goliath
        """
        war_id = f"war_goliath_{user_id}_{datetime.utcnow().timestamp()}"
        
        defeat_record = {
            'war_id': war_id,
            'goliath_name': goliath_name,
            'goliath_power': goliath_power,
            'defeat_method': defeat_method,
            'years_of_war': years_of_war,
            'switch_statement': switch_statement,
            'affection_gained': affection_gained,
            'shadow_from_giga': shadow_from_giga,
            'cloud_from_giga': cloud_from_giga,
            'defeated_at': datetime.utcnow().isoformat(),
            'victory_turned': False,
            'viking_blood_frenzy_triggered': False
        }
        
        if user_id not in self.goliath_defeats:
            self.goliath_defeats[user_id] = []
        
        self.goliath_defeats[user_id].append(defeat_record)
        
        # Save to file
        self._save_data()
        
        # Create emblem
        emblem_name = f"Goliath Slayer: {goliath_name}"
        emblem_desc = f"Victory against {goliath_name} after {years_of_war} years of war"
        rarity = 'legendary' if goliath_power > 0.8 else 'epic' if goliath_power > 0.5 else 'rare'
        
        emblem_result = self.create_victory_emblem(
            user_id, emblem_name, emblem_desc, 'goliath', rarity,
            '⚔️', goliath_power, switch_statement, affection_gained,
            shadow_from_giga, cloud_from_giga
        )
        
        # Create trophy
        trophy_name = f"Trophy: {goliath_name} Defeated"
        trophy_desc = f"Victory trophy from defeating {goliath_name}"
        
        trophy_result = self.create_victory_trophy(
            user_id, trophy_name, trophy_desc, war_id, 'goliath',
            defeat_method, years_of_war, switch_statement,
            "The one and only correct and tested statement",
            trigger_timing_seconds=4  # 4 seconds before final hit
        )
        
        return {
            'success': True,
            'defeat_record': defeat_record,
            'emblem': emblem_result.get('emblem'),
            'trophy': trophy_result.get('trophy')
        }
    
    def record_ego_defeat(self, user_id: str, ego_name: str,
                         ego_arrogance_level: float,
                         defeat_method: str,
                         years_of_war: int = 0,
                         winner_mentality_tripped: bool = True,
                         criminal_mentality_cuts: int = 0) -> Dict[str, Any]:
        """
        Record a victory against an undermined EGO
        """
        war_id = f"war_ego_{user_id}_{datetime.utcnow().timestamp()}"
        
        defeat_record = {
            'war_id': war_id,
            'ego_name': ego_name,
            'ego_arrogance_level': ego_arrogance_level,
            'defeat_method': defeat_method,
            'years_of_war': years_of_war,
            'winner_mentality_tripped': winner_mentality_tripped,
            'criminal_mentality_cuts': criminal_mentality_cuts,
            'defeated_at': datetime.utcnow().isoformat(),
            'ignorance_cause': True  # Cause of war was ignorance, not hunger
        }
        
        if user_id not in self.ego_defeats:
            self.ego_defeats[user_id] = []
        
        self.ego_defeats[user_id].append(defeat_record)
        
        # Save to file
        self._save_data()
        
        # Create emblem
        emblem_name = f"EGO Breaker: {ego_name}"
        emblem_desc = f"Victory against {ego_name}'s winner mentality"
        rarity = 'mythic' if ego_arrogance_level > 0.9 else 'legendary'
        
        emblem_result = self.create_victory_emblem(
            user_id, emblem_name, emblem_desc, 'ego', rarity,
            '👑', ego_arrogance_level
        )
        
        # Create trophy
        trophy_name = f"Trophy: {ego_name} EGO Shattered"
        trophy_desc = f"Victory trophy from undermining {ego_name}'s EGO"
        
        trophy_result = self.create_victory_trophy(
            user_id, trophy_name, trophy_desc, war_id, 'ego',
            defeat_method, years_of_war, "We are switching on them",
            "The overlooked correct statement", 0, criminal_mentality_cuts
        )
        
        return {
            'success': True,
            'defeat_record': defeat_record,
            'emblem': emblem_result.get('emblem'),
            'trophy': trophy_result.get('trophy')
        }
    
    def trigger_viking_blood_frenzy(self, user_id: str, emblem_id: str,
                                    trigger_intensity: float = 1.33) -> Dict[str, Any]:
        """
        Trigger Viking Blood Frenzy (0-133% instant)
        """
        # Find emblem
        emblem = None
        if user_id in self.victory_emblems:
            for e in self.victory_emblems[user_id]:
                if e.id == emblem_id:
                    emblem = e
                    break
        
        if not emblem:
            return {'success': False, 'error': 'Emblem not found'}
        
        # Trigger frenzy
        emblem.viking_blood_frenzy = min(1.33, trigger_intensity)
        emblem.trigger_charges += 1
        emblem.energy_stacked = min(1.0, emblem.energy_stacked + 0.1)
        
        # Record frenzy event
        if user_id not in self.viking_frenzy_events:
            self.viking_frenzy_events[user_id] = []
        
        self.viking_frenzy_events[user_id].append({
            'emblem_id': emblem_id,
            'intensity': emblem.viking_blood_frenzy,
            'triggered_at': datetime.utcnow().isoformat(),
            'energy_before': emblem.energy_stacked - 0.1,
            'energy_after': emblem.energy_stacked
        })
        
        # Save to file
        self._save_data()
        
        return {
            'success': True,
            'emblem': emblem.to_dict(),
            'frenzy_intensity': emblem.viking_blood_frenzy,
            'message': f'Viking Blood Frenzy triggered at {emblem.viking_blood_frenzy * 100:.1f}%'
        }
    
    def apply_jyske_lov(self, user_id: str, target_id: str,
                       violation_type: str = 'alarm_ignored') -> Dict[str, Any]:
        """
        Apply Jyske Lov (Jutlandic Law)
        "Every time you feel good you must smile back to the world to respond signals,
         if you ignore an alarm you will die by the little dots in the last page on the last word"
        """
        if user_id not in self.jyske_lov_records:
            self.jyske_lov_records[user_id] = []
        
        record = {
            'target_id': target_id,
            'violation_type': violation_type,
            'applied_at': datetime.utcnow().isoformat(),
            'law_text': 'Every time you feel good you must smile back to the world to respond signals',
            'punishment': 'Die by the little dots in the last page on the last word',
            'city_encephalitis': True  # Must undergo city encephalitis
        }
        
        self.jyske_lov_records[user_id].append(record)
        
        # Save to file
        self._save_data()
        
        # Update trophy if exists
        if user_id in self.victory_trophies:
            for trophy in self.victory_trophies[user_id]:
                if trophy.war_id == target_id or target_id in trophy.fantasy_monster_hunters:
                    trophy.jyske_lov_applied = True
        
        return {
            'success': True,
            'jyske_lov_applied': record,
            'message': 'Jyske Lov applied - City encephalitis required'
        }
    
    def add_fantasy_monster_hunter(self, user_id: str, trophy_id: str,
                                   monster_name: str, hunting_reason: str) -> Dict[str, Any]:
        """
        Add a fantasy monster that is hunting for answers about the victory curse
        """
        if user_id not in self.victory_trophies:
            return {'success': False, 'error': 'No trophies found for user'}
        
        trophy = None
        for t in self.victory_trophies[user_id]:
            if t.id == trophy_id:
                trophy = t
                break
        
        if not trophy:
            return {'success': False, 'error': 'Trophy not found'}
        
        hunter = {
            'monster_name': monster_name,
            'hunting_reason': hunting_reason,
            'added_at': datetime.utcnow().isoformat(),
            'seeking_answers': True
        }
        
        trophy.fantasy_monster_hunters.append(hunter)
        
        # Save to file
        self._save_data()
        
        return {
            'success': True,
            'trophy': trophy.to_dict(),
            'hunter': hunter
        }
    
    def get_user_emblems(self, user_id: str) -> Dict[str, Any]:
        """Get all emblems for a user"""
        emblems = self.victory_emblems.get(user_id, [])
        return {
            'success': True,
            'emblems': [e.to_dict() for e in emblems],
            'count': len(emblems),
            'total_power': sum(e.power_level for e in emblems),
            'total_frenzy': sum(e.viking_blood_frenzy for e in emblems)
        }
    
    def get_user_trophies(self, user_id: str, museum_category: str = None) -> Dict[str, Any]:
        """Get all trophies for a user"""
        trophies = self.victory_trophies.get(user_id, [])
        
        if museum_category:
            trophies = [t for t in trophies if t.museum_category == museum_category]
        
        return {
            'success': True,
            'trophies': [t.to_dict() for t in trophies],
            'count': len(trophies),
            'total_wars': len(set(t.war_id for t in trophies)),
            'goliath_defeats': len([t for t in trophies if t.opponent_type == 'goliath']),
            'ego_defeats': len([t for t in trophies if t.opponent_type == 'ego'])
        }
    
    def get_museum_collection(self, user_id: str) -> Dict[str, Any]:
        """Get museum collection organized by category"""
        if user_id not in self.museum_collections:
            self.museum_collections[user_id] = {}
        
        collection = self.museum_collections[user_id]
        
        return {
            'success': True,
            'museum': collection,
            'total_items': sum(len(items) for items in collection.values()),
            'categories': list(collection.keys())
        }
    
    def get_victory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive victory statistics"""
        emblems = self.victory_emblems.get(user_id, [])
        trophies = self.victory_trophies.get(user_id, [])
        goliaths = self.goliath_defeats.get(user_id, [])
        egos = self.ego_defeats.get(user_id, [])
        frenzies = self.viking_frenzy_events.get(user_id, [])
        jyske_lov = self.jyske_lov_records.get(user_id, [])
        
        total_war_years = sum(t.war_duration_years for t in trophies)
        
        stats = {
            'total_emblems': len(emblems),
            'total_trophies': len(trophies),
            'goliath_defeats': len(goliaths),
            'ego_defeats': len(egos),
            'total_war_years': total_war_years,
            'viking_frenzy_triggers': len(frenzies),
            'jyske_lov_applications': len(jyske_lov),
            'total_criminal_mentality_cuts': sum(t.criminal_mentality_cuts for t in trophies),
            'switch_statements_used': len([e for e in emblems if e.switch_statement]),
            'fantasy_monster_hunters': sum(len(t.fantasy_monster_hunters) for t in trophies),
            'total_affection': sum(e.affection_level for e in emblems),
            'total_energy_stacked': sum(e.energy_stacked for e in emblems),
            'max_viking_frenzy': max([e.viking_blood_frenzy for e in emblems], default=0.0)
        }
        
        if user_id not in self.victory_stats:
            self.victory_stats[user_id] = {}
        
        self.victory_stats[user_id] = stats
        
        return {
            'success': True,
            'stats': stats
        }
    
    def _load_data(self):
        """Load data from file - ONE JSON FILE (Rule #1)"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Load emblems
                    for user_id, emblems_data in data.get('victory_emblems', {}).items():
                        self.victory_emblems[user_id] = []
                        for e_data in emblems_data:
                            emblem = VictoryEmblem(
                                e_data['id'], e_data['name'], e_data['description'],
                                e_data['victory_type'], e_data['rarity'], e_data['icon'],
                                e_data['power_level']
                            )
                            emblem.earned_at = datetime.fromisoformat(e_data['earned_at']) if e_data.get('earned_at') else None
                            emblem.affection_level = e_data.get('affection_level', 0.0)
                            emblem.shadow_intensity = e_data.get('shadow_intensity', 0.0)
                            emblem.cloud_size = e_data.get('cloud_size', 0.0)
                            emblem.viking_blood_frenzy = e_data.get('viking_blood_frenzy', 0.0)
                            emblem.trigger_charges = e_data.get('trigger_charges', 0)
                            emblem.switch_statement = e_data.get('switch_statement', '')
                            emblem.energy_stacked = e_data.get('energy_stacked', 0.0)
                            self.victory_emblems[user_id].append(emblem)
                    
                    # Load trophies
                    for user_id, trophies_data in data.get('victory_trophies', {}).items():
                        self.victory_trophies[user_id] = []
                        for t_data in trophies_data:
                            trophy = VictoryTrophy(
                                t_data['id'], t_data['name'], t_data['description'],
                                t_data['war_id'], t_data['opponent_type'], t_data['victory_method']
                            )
                            trophy.earned_at = datetime.fromisoformat(t_data['earned_at']) if t_data.get('earned_at') else None
                            trophy.war_duration_years = t_data.get('war_duration_years', 0)
                            trophy.opponent_ignorance_level = t_data.get('opponent_ignorance_level', 0.0)
                            trophy.criminal_mentality_cuts = t_data.get('criminal_mentality_cuts', 0)
                            trophy.final_statement = t_data.get('final_statement', '')
                            trophy.overlooked_correct_statement = t_data.get('overlooked_correct_statement', '')
                            trophy.special_forces_attention = t_data.get('special_forces_attention', False)
                            trophy.trigger_timing_seconds = t_data.get('trigger_timing_seconds', 0)
                            trophy.victory_turned = t_data.get('victory_turned', False)
                            trophy.jyske_lov_applied = t_data.get('jyske_lov_applied', False)
                            trophy.fantasy_monster_hunters = t_data.get('fantasy_monster_hunters', [])
                            self.victory_trophies[user_id].append(trophy)
                    
                    # Load other data
                    self.war_history = data.get('war_history', {})
                    self.museum_collections = data.get('museum_collections', {})
                    self.goliath_defeats = data.get('goliath_defeats', {})
                    self.ego_defeats = data.get('ego_defeats', {})
                    self.switch_statements = data.get('switch_statements', {})
                    self.viking_frenzy_events = data.get('viking_frenzy_events', {})
                    self.jyske_lov_records = data.get('jyske_lov_records', {})
                    
                    logger.info(f"Loaded victory data from {self.data_file}")
        except Exception as e:
            logger.error(f"Error loading victory data: {e}")
    
    def _save_data(self):
        """Save data to file - ONE JSON FILE (Rule #1)"""
        try:
            data = {
                'victory_emblems': {},
                'victory_trophies': {},
                'war_history': self.war_history,
                'museum_collections': self.museum_collections,
                'goliath_defeats': self.goliath_defeats,
                'ego_defeats': self.ego_defeats,
                'switch_statements': self.switch_statements,
                'viking_frenzy_events': self.viking_frenzy_events,
                'jyske_lov_records': self.jyske_lov_records,
                'last_saved': datetime.utcnow().isoformat()
            }
            
            # Convert emblems to dict
            for user_id, emblems in self.victory_emblems.items():
                data['victory_emblems'][user_id] = [e.to_dict() for e in emblems]
            
            # Convert trophies to dict
            for user_id, trophies in self.victory_trophies.items():
                data['victory_trophies'][user_id] = [t.to_dict() for t in trophies]
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Saved victory data to {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving victory data: {e}")
            return False
    
    def _add_to_museum(self, user_id: str, trophy: VictoryTrophy):
        """Add trophy to museum collection"""
        if user_id not in self.museum_collections:
            self.museum_collections[user_id] = {}
        
        category = trophy.museum_category
        if category not in self.museum_collections[user_id]:
            self.museum_collections[user_id][category] = []
        
        self.museum_collections[user_id][category].append(trophy.to_dict())
    
    def record_war_victory(self, user_id: str, opponent_name: str,
                          opponent_type: str, war_duration_years: int,
                          victory_method: str,
                          switch_statement: str = "They are switching on them now",
                          overlooked_statement: str = "",
                          trigger_timing: int = 4,
                          affection_gained: float = 0.0,
                          shadow_intensity: float = 0.0,
                          cloud_size: float = 0.0,
                          viking_frenzy_triggered: bool = False,
                          criminal_mentality_cuts: int = 0) -> Dict[str, Any]:
        """
        Record a complete war victory with all details
        """
        war_id = f"war_{user_id}_{datetime.utcnow().timestamp()}"
        
        # Create emblem
        emblem_name = f"War Victor: {opponent_name}"
        emblem_desc = f"Victory against {opponent_name} after {war_duration_years} years"
        rarity = 'mythic' if war_duration_years >= 20 else 'legendary' if war_duration_years >= 10 else 'epic'
        
        emblem_result = self.create_victory_emblem(
            user_id, emblem_name, emblem_desc, opponent_type, rarity,
            '⚔️', 1.0, switch_statement, affection_gained,
            shadow_intensity, cloud_size
        )
        
        # Create trophy
        trophy_name = f"War Trophy: {opponent_name}"
        trophy_desc = f"Victory trophy from {war_duration_years} year war against {opponent_name}"
        
        trophy_result = self.create_victory_trophy(
            user_id, trophy_name, trophy_desc, war_id, opponent_type,
            victory_method, war_duration_years, switch_statement,
            overlooked_statement, trigger_timing, criminal_mentality_cuts
        )
        
        # Trigger viking frenzy if applicable
        if viking_frenzy_triggered and emblem_result.get('emblem'):
            self.trigger_viking_blood_frenzy(
                user_id, emblem_result['emblem']['id'], 1.33
            )
        
        return {
            'success': True,
            'war_id': war_id,
            'emblem': emblem_result.get('emblem'),
            'trophy': trophy_result.get('trophy'),
            'message': f'Victory recorded! War lasted {war_duration_years} years.'
        }


# Global instance
victory_emblems_trophies_system = VictoryEmblemsTrophiesSystem()

