"""
Compass and HourGlass System
Navigation, time management, and textual spells
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CompassHourglassSystem:
    """
    Compass and HourGlass System
    Provides navigation, time management, and textual spells
    """
    
    def __init__(self):
        self.compass_directions = {}
        self.hourglass_timers = {}
        self.textual_spells = {}
        self.rulebook_v2 = {}
        self.rulebook_v3 = {}
        self.rule_templates = {}
        self.rule_analytics = {}
        self.rule_history = {}
        self.fantasy_monsters = {}
        self.divine_elements = {}
        self.psycho_factors = {}
        self.enhanced_stats = {}
    
        # Initialize default rules
        self._initialize_default_rules()
    
    def _initialize_default_rules(self):
        """Initialize default rules in Rulebook v3.0"""
        # Rule #1: Only create one JSON file and only choose which folder it should be stored/saved
        self.add_to_rulebook_v3(
            rule_name="Rule #1: Single JSON File Creation",
            rule_text="Only create one JSON file and only choose which folder it should be stored/saved",
            category="file_management",
            subcategory="json_files",
            tags=["json", "file_creation", "storage", "priority", "rule_1"],
            priority=10,  # Highest priority since it's rule #1
            metadata={
                "rule_number": 1,
                "rule_type": "file_management",
                "enforcement": "mandatory",
                "description": "When creating JSON files, only create one file at a time and explicitly choose the appropriate folder for storage"
            }
        )
    
    def create_compass(self, user_id: str, target: str) -> Dict[str, Any]:
        """
        Create a compass pointing to target
        """
        compass_id = f"compass_{user_id}_{datetime.utcnow().timestamp()}"
        
        compass = {
            'id': compass_id,
            'user_id': user_id,
            'target': target,
            'direction': 'north',  # Would calculate actual direction
            'distance': 0.0,
            'created_at': datetime.utcnow().isoformat(),
            'active': True
        }
        
        self.compass_directions[compass_id] = compass
        return {'success': True, 'compass': compass}
    
    def create_hourglass(self, user_id: str, duration_minutes: int,
                        purpose: str) -> Dict[str, Any]:
        """
        Create an hourglass timer
        """
        hourglass_id = f"hourglass_{user_id}_{datetime.utcnow().timestamp()}"
        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        hourglass = {
            'id': hourglass_id,
            'user_id': user_id,
            'duration_minutes': duration_minutes,
            'purpose': purpose,
            'start_time': datetime.utcnow().isoformat(),
            'end_time': end_time.isoformat(),
            'remaining_seconds': duration_minutes * 60,
            'active': True
        }
        
        self.hourglass_timers[hourglass_id] = hourglass
        return {'success': True, 'hourglass': hourglass}
    
    def create_textual_spell(self, spell_name: str, spell_text: str,
                            effect_type: str, power_level: int) -> Dict[str, Any]:
        """
        Create a textual spell
        """
        spell_id = f"spell_{spell_name}_{datetime.utcnow().timestamp()}"
        
        spell = {
            'id': spell_id,
            'name': spell_name,
            'text': spell_text,
            'effect_type': effect_type,
            'power_level': power_level,
            'created_at': datetime.utcnow().isoformat(),
            'uses': 0,
            'max_uses': 10
        }
        
        self.textual_spells[spell_id] = spell
        return {'success': True, 'spell': spell}
    
    def cast_spell(self, spell_id: str, target: str) -> Dict[str, Any]:
        """
        Cast a textual spell
        """
        spell = self.textual_spells.get(spell_id)
        if not spell:
            return {'success': False, 'error': 'Spell not found'}
        
        if spell['uses'] >= spell['max_uses']:
            return {'success': False, 'error': 'Spell exhausted'}
        
        spell['uses'] += 1
        
        effect = {
            'spell_id': spell_id,
            'spell_name': spell['name'],
            'target': target,
            'effect_type': spell['effect_type'],
            'power_level': spell['power_level'],
            'cast_at': datetime.utcnow().isoformat(),
            'success': True
        }
        
        return {'success': True, 'effect': effect}
    
    def add_to_rulebook_v2(self, rule_name: str, rule_text: str,
                          category: str) -> Dict[str, Any]:
        """
        Add rule to Rulebook v2.0
        """
        rule_id = f"rule_{rule_name}_{datetime.utcnow().timestamp()}"
        
        rule = {
            'id': rule_id,
            'name': rule_name,
            'text': rule_text,
            'category': category,
            'added_at': datetime.utcnow().isoformat(),
            'version': '2.0'
        }
        
        if category not in self.rulebook_v2:
            self.rulebook_v2[category] = []
        
        self.rulebook_v2[category].append(rule)
        
        return {'success': True, 'rule': rule}
    
    def get_rulebook_v2(self) -> Dict[str, Any]:
        """
        Get complete Rulebook v2.0
        """
        return {
            'success': True,
            'version': '2.0',
            'categories': list(self.rulebook_v2.keys()),
            'rules': self.rulebook_v2,
            'total_rules': sum(len(rules) for rules in self.rulebook_v2.values())
        }
    
    def add_to_rulebook_v3(self, rule_name: str, rule_text: str,
                          category: str, subcategory: str = None,
                          tags: List[str] = None, priority: int = 5,
                          dependencies: List[str] = None,
                          expires_at: Optional[datetime] = None,
                          active: bool = True,
                          metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Add rule to Rulebook v3.0 with enhanced features
        """
        rule_id = f"rule_v3_{rule_name}_{datetime.utcnow().timestamp()}"
        
        rule = {
            'id': rule_id,
            'name': rule_name,
            'text': rule_text,
            'category': category,
            'subcategory': subcategory,
            'tags': tags or [],
            'priority': priority,  # 1-10, 10 being highest
            'dependencies': dependencies or [],
            'expires_at': expires_at.isoformat() if expires_at else None,
            'active': active,
            'metadata': metadata or {},
            'added_at': datetime.utcnow().isoformat(),
            'version': '3.0',
            'views': 0,
            'uses': 0,
            'rating': 0.0,
            'ratings_count': 0
        }
        
        # Store in category structure
        if category not in self.rulebook_v3:
            self.rulebook_v3[category] = {}
        
        if subcategory:
            if subcategory not in self.rulebook_v3[category]:
                self.rulebook_v3[category][subcategory] = []
            self.rulebook_v3[category][subcategory].append(rule)
        else:
            if '_general' not in self.rulebook_v3[category]:
                self.rulebook_v3[category]['_general'] = []
            self.rulebook_v3[category]['_general'].append(rule)
        
        # Store in history
        if rule_id not in self.rule_history:
            self.rule_history[rule_id] = []
        self.rule_history[rule_id].append({
            'action': 'created',
            'timestamp': datetime.utcnow().isoformat(),
            'rule': rule.copy()
        })
        
        return {'success': True, 'rule': rule}
    
    def get_rulebook_v3(self, category: str = None, 
                        subcategory: str = None,
                        tags: List[str] = None,
                        active_only: bool = True,
                        priority_min: int = None) -> Dict[str, Any]:
        """
        Get complete Rulebook v3.0 with filtering
        """
        rules_result = {}
        total_rules = 0
        
        # Filter rules
        for cat, subcats in self.rulebook_v3.items():
            if category and cat != category:
                continue
            
            rules_result[cat] = {}
            
            for subcat, rules in subcats.items():
                if subcategory and subcat != subcategory:
                    continue
                
                filtered_rules = []
                for rule in rules:
                    # Active filter
                    if active_only and not rule.get('active', True):
                        continue
                    
                    # Expiration filter
                    if rule.get('expires_at'):
                        expires = datetime.fromisoformat(rule['expires_at'])
                        if datetime.utcnow() > expires:
                            continue
                    
                    # Tags filter
                    if tags:
                        rule_tags = rule.get('tags', [])
                        if not any(tag in rule_tags for tag in tags):
                            continue
                    
                    # Priority filter
                    if priority_min is not None:
                        if rule.get('priority', 5) < priority_min:
                            continue
                    
                    filtered_rules.append(rule)
                    total_rules += 1
                
                if filtered_rules:
                    rules_result[cat][subcat] = filtered_rules
        
        return {
            'success': True,
            'version': '3.0',
            'categories': list(rules_result.keys()),
            'rules': rules_result,
            'total_rules': total_rules,
            'filters_applied': {
                'category': category,
                'subcategory': subcategory,
                'tags': tags,
                'active_only': active_only,
                'priority_min': priority_min
            }
        }
    
    def search_rules_v3(self, query: str, category: str = None) -> Dict[str, Any]:
        """
        Search rules in Rulebook v3.0
        """
        results = []
        query_lower = query.lower()
        
        for cat, subcats in self.rulebook_v3.items():
            if category and cat != category:
                continue
            
            for subcat, rules in subcats.items():
                for rule in rules:
                    # Search in name, text, tags
                    if (query_lower in rule['name'].lower() or
                        query_lower in rule['text'].lower() or
                        any(query_lower in tag.lower() for tag in rule.get('tags', []))):
                        results.append(rule)
        
        return {
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        }
    
    def update_rule_v3(self, rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a rule in Rulebook v3.0
        """
        # Find rule
        rule = None
        rule_location = None
        
        for cat, subcats in self.rulebook_v3.items():
            for subcat, rules in subcats.items():
                for r in rules:
                    if r['id'] == rule_id:
                        rule = r
                        rule_location = (cat, subcat, rules.index(r))
                        break
                if rule:
                    break
            if rule:
                break
        
        if not rule:
            return {'success': False, 'error': 'Rule not found'}
        
        # Store old version in history
        if rule_id not in self.rule_history:
            self.rule_history[rule_id] = []
        self.rule_history[rule_id].append({
            'action': 'updated',
            'timestamp': datetime.utcnow().isoformat(),
            'old_rule': rule.copy(),
            'updates': updates
        })
        
        # Update rule
        rule.update(updates)
        rule['updated_at'] = datetime.utcnow().isoformat()
        
        return {'success': True, 'rule': rule}
    
    def deactivate_rule_v3(self, rule_id: str) -> Dict[str, Any]:
        """
        Deactivate a rule in Rulebook v3.0
        """
        return self.update_rule_v3(rule_id, {'active': False})
    
    def activate_rule_v3(self, rule_id: str) -> Dict[str, Any]:
        """
        Activate a rule in Rulebook v3.0
        """
        return self.update_rule_v3(rule_id, {'active': True})
    
    def view_rule_v3(self, rule_id: str) -> Dict[str, Any]:
        """
        View a rule (increments view count)
        """
        # Find rule
        rule = None
        for cat, subcats in self.rulebook_v3.items():
            for subcat, rules in subcats.items():
                for r in rules:
                    if r['id'] == rule_id:
                        rule = r
                        rule['views'] = rule.get('views', 0) + 1
                        break
                if rule:
                    break
            if rule:
                break
        
        if not rule:
            return {'success': False, 'error': 'Rule not found'}
        
        return {'success': True, 'rule': rule}
    
    def rate_rule_v3(self, rule_id: str, rating: float) -> Dict[str, Any]:
        """
        Rate a rule (1-10 scale)
        """
        if rating < 1 or rating > 10:
            return {'success': False, 'error': 'Rating must be between 1 and 10'}
        
        # Find rule
        rule = None
        for cat, subcats in self.rulebook_v3.items():
            for subcat, rules in subcats.items():
                for r in rules:
                    if r['id'] == rule_id:
                        rule = r
                        break
                if rule:
                    break
            if rule:
                break
        
        if not rule:
            return {'success': False, 'error': 'Rule not found'}
        
        # Update rating
        current_rating = rule.get('rating', 0.0)
        ratings_count = rule.get('ratings_count', 0)
        
        new_rating = ((current_rating * ratings_count) + rating) / (ratings_count + 1)
        
        rule['rating'] = new_rating
        rule['ratings_count'] = ratings_count + 1
        
        return {'success': True, 'rule': rule, 'new_rating': new_rating}
    
    def get_rule_analytics_v3(self) -> Dict[str, Any]:
        """
        Get analytics for Rulebook v3.0
        """
        total_rules = 0
        active_rules = 0
        expired_rules = 0
        total_views = 0
        total_ratings = 0
        avg_rating = 0.0
        category_counts = {}
        priority_distribution = {i: 0 for i in range(1, 11)}
        
        for cat, subcats in self.rulebook_v3.items():
            category_counts[cat] = 0
            for subcat, rules in subcats.items():
                for rule in rules:
                    total_rules += 1
                    category_counts[cat] += 1
                    
                    if rule.get('active', True):
                        active_rules += 1
                    
                    if rule.get('expires_at'):
                        expires = datetime.fromisoformat(rule['expires_at'])
                        if datetime.utcnow() > expires:
                            expired_rules += 1
                    
                    total_views += rule.get('views', 0)
                    total_ratings += rule.get('ratings_count', 0)
                    
                    priority = rule.get('priority', 5)
                    priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        if total_ratings > 0:
            # Calculate average rating from all rules
            rating_sum = 0.0
            for cat, subcats in self.rulebook_v3.items():
                for subcat, rules in subcats.items():
                    for rule in rules:
                        if rule.get('rating', 0) > 0:
                            rating_sum += rule['rating']
            avg_rating = rating_sum / total_rules if total_rules > 0 else 0.0
        
        return {
            'success': True,
            'analytics': {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'inactive_rules': total_rules - active_rules,
                'expired_rules': expired_rules,
                'total_views': total_views,
                'total_ratings': total_ratings,
                'average_rating': avg_rating,
                'category_counts': category_counts,
                'priority_distribution': priority_distribution
            }
        }
    
    def create_rule_template_v3(self, template_name: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a rule template for Rulebook v3.0
        """
        template_id = f"template_{template_name}_{datetime.utcnow().timestamp()}"
        
        template = {
            'id': template_id,
            'name': template_name,
            'data': template_data,
            'created_at': datetime.utcnow().isoformat(),
            'uses': 0
        }
        
        self.rule_templates[template_id] = template
        return {'success': True, 'template': template}
    
    # ========== Fantasy Monsters System ==========
    
    def create_fantasy_monster(self, monster_name: str, monster_type: str,
                              stats: Dict[str, int], abilities: List[str],
                              weaknesses: List[str] = None,
                              divine_power: float = 0.0,
                              psycho_factors: List[str] = None) -> Dict[str, Any]:
        """
        Create a fantasy monster for Rulebook v3.0
        """
        monster_id = f"monster_{monster_name}_{datetime.utcnow().timestamp()}"
        
        monster = {
            'id': monster_id,
            'name': monster_name,
            'type': monster_type,
            'stats': stats,
            'abilities': abilities,
            'weaknesses': weaknesses or [],
            'divine_power': divine_power,
            'psycho_factors': psycho_factors or [],
            'created_at': datetime.utcnow().isoformat(),
            'level': stats.get('level', 1),
            'hp': stats.get('hp', 100),
            'max_hp': stats.get('hp', 100),
            'mp': stats.get('mp', 50),
            'max_mp': stats.get('mp', 50),
            'attack': stats.get('attack', 10),
            'defense': stats.get('defense', 10),
            'speed': stats.get('speed', 10),
            'magic': stats.get('magic', 10),
            'experience_value': stats.get('exp', 100),
            'gold_value': stats.get('gold', 50)
        }
        
        self.fantasy_monsters[monster_id] = monster
        return {'success': True, 'monster': monster}
    
    def get_fantasy_monster(self, monster_id: str) -> Dict[str, Any]:
        """Get a fantasy monster"""
        monster = self.fantasy_monsters.get(monster_id)
        if not monster:
            return {'success': False, 'error': 'Monster not found'}
        return {'success': True, 'monster': monster}
    
    def list_fantasy_monsters(self, monster_type: str = None) -> Dict[str, Any]:
        """List all fantasy monsters"""
        monsters = list(self.fantasy_monsters.values())
        if monster_type:
            monsters = [m for m in monsters if m['type'] == monster_type]
        return {'success': True, 'monsters': monsters, 'count': len(monsters)}
    
    # ========== Enhanced Spells with Pluses/Minus ==========
    
    def create_enhanced_spell(self, spell_name: str, spell_text: str,
                             effect_type: str, power_level: int,
                             pluses: Dict[str, float] = None,
                             minuses: Dict[str, float] = None,
                             divine_bonus: float = 0.0,
                             psycho_effects: List[str] = None,
                             mana_cost: int = 10) -> Dict[str, Any]:
        """
        Create an enhanced spell with pluses, minuses, divine, and psycho factors
        """
        spell_id = f"spell_enhanced_{spell_name}_{datetime.utcnow().timestamp()}"
        
        spell = {
            'id': spell_id,
            'name': spell_name,
            'text': spell_text,
            'effect_type': effect_type,
            'power_level': power_level,
            'pluses': pluses or {},  # Bonuses: {'attack': 10, 'defense': 5, etc.}
            'minuses': minuses or {},  # Penalties: {'speed': -5, 'hp': -20, etc.}
            'divine_bonus': divine_bonus,
            'psycho_effects': psycho_effects or [],
            'mana_cost': mana_cost,
            'created_at': datetime.utcnow().isoformat(),
            'uses': 0,
            'max_uses': 10,
            'version': '3.0_enhanced'
        }
        
        self.textual_spells[spell_id] = spell
        return {'success': True, 'spell': spell}
    
    def cast_enhanced_spell(self, spell_id: str, target: str,
                            target_type: str = 'monster') -> Dict[str, Any]:
        """
        Cast an enhanced spell with all effects
        """
        spell = self.textual_spells.get(spell_id)
        if not spell:
            return {'success': False, 'error': 'Spell not found'}
        
        if spell['uses'] >= spell['max_uses']:
            return {'success': False, 'error': 'Spell exhausted'}
        
        spell['uses'] += 1
        
        effect = {
            'spell_id': spell_id,
            'spell_name': spell['name'],
            'target': target,
            'target_type': target_type,
            'effect_type': spell['effect_type'],
            'power_level': spell['power_level'],
            'pluses_applied': spell.get('pluses', {}),
            'minuses_applied': spell.get('minuses', {}),
            'divine_bonus': spell.get('divine_bonus', 0.0),
            'psycho_effects': spell.get('psycho_effects', []),
            'mana_cost': spell.get('mana_cost', 10),
            'cast_at': datetime.utcnow().isoformat(),
            'success': True
        }
        
        return {'success': True, 'effect': effect}
    
    # ========== Divine Elements System ==========
    
    def create_divine_element(self, element_name: str, element_type: str,
                             power_level: float, blessings: List[str],
                             curses: List[str] = None) -> Dict[str, Any]:
        """
        Create a divine element
        """
        element_id = f"divine_{element_name}_{datetime.utcnow().timestamp()}"
        
        element = {
            'id': element_id,
            'name': element_name,
            'type': element_type,
            'power_level': power_level,
            'blessings': blessings,
            'curses': curses or [],
            'created_at': datetime.utcnow().isoformat(),
            'active': True
        }
        
        self.divine_elements[element_id] = element
        return {'success': True, 'element': element}
    
    def apply_divine_blessing(self, element_id: str, target: str) -> Dict[str, Any]:
        """Apply a divine blessing"""
        element = self.divine_elements.get(element_id)
        if not element:
            return {'success': False, 'error': 'Divine element not found'}
        
        if not element.get('active', True):
            return {'success': False, 'error': 'Divine element not active'}
        
        blessing = {
            'element_id': element_id,
            'element_name': element['name'],
            'target': target,
            'blessings': element['blessings'],
            'power_level': element['power_level'],
            'applied_at': datetime.utcnow().isoformat(),
            'success': True
        }
        
        return {'success': True, 'blessing': blessing}
    
    def apply_divine_curse(self, element_id: str, target: str) -> Dict[str, Any]:
        """Apply a divine curse"""
        element = self.divine_elements.get(element_id)
        if not element:
            return {'success': False, 'error': 'Divine element not found'}
        
        if not element.get('active', True):
            return {'success': False, 'error': 'Divine element not active'}
        
        curse = {
            'element_id': element_id,
            'element_name': element['name'],
            'target': target,
            'curses': element['curses'],
            'power_level': element['power_level'],
            'applied_at': datetime.utcnow().isoformat(),
            'success': True
        }
        
        return {'success': True, 'curse': curse}
    
    # ========== Multiple Psycho Factors System ==========
    
    def create_psycho_factor(self, factor_name: str, factor_type: str,
                           intensity: float, effects: Dict[str, Any],
                           triggers: List[str] = None) -> Dict[str, Any]:
        """
        Create a psycho factor
        """
        factor_id = f"psycho_{factor_name}_{datetime.utcnow().timestamp()}"
        
        factor = {
            'id': factor_id,
            'name': factor_name,
            'type': factor_type,
            'intensity': intensity,  # 0.0 to 1.0
            'effects': effects,
            'triggers': triggers or [],
            'created_at': datetime.utcnow().isoformat(),
            'active': True
        }
        
        self.psycho_factors[factor_id] = factor
        return {'success': True, 'factor': factor}
    
    def apply_psycho_factors(self, target: str, factor_ids: List[str]) -> Dict[str, Any]:
        """
        Apply multiple psycho factors to a target
        """
        applied_factors = []
        combined_effects = {}
        total_intensity = 0.0
        
        for factor_id in factor_ids:
            factor = self.psycho_factors.get(factor_id)
            if not factor:
                continue
            
            if not factor.get('active', True):
                continue
            
            applied_factors.append(factor)
            total_intensity += factor['intensity']
            
            # Combine effects
            for key, value in factor['effects'].items():
                if key in combined_effects:
                    if isinstance(value, (int, float)):
                        combined_effects[key] += value
                    else:
                        combined_effects[key] = [combined_effects[key], value]
                else:
                    combined_effects[key] = value
        
        result = {
            'target': target,
            'factors_applied': [f['name'] for f in applied_factors],
            'total_intensity': min(total_intensity, 1.0),  # Cap at 1.0
            'combined_effects': combined_effects,
            'applied_at': datetime.utcnow().isoformat(),
            'success': True
        }
        
        return {'success': True, 'result': result}
    
    def get_all_psycho_factors(self) -> Dict[str, Any]:
        """Get all psycho factors"""
        return {
            'success': True,
            'factors': list(self.psycho_factors.values()),
            'count': len(self.psycho_factors)
        }
    
    # ========== Enhanced Stats System ==========
    
    def create_enhanced_stats(self, entity_id: str, entity_type: str,
                            base_stats: Dict[str, int],
                            stat_modifiers: Dict[str, float] = None,
                            divine_modifiers: Dict[str, float] = None,
                            psycho_modifiers: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Create enhanced stats with all modifiers
        """
        enhanced_stats = {
            'entity_id': entity_id,
            'entity_type': entity_type,
            'base_stats': base_stats,
            'stat_modifiers': stat_modifiers or {},
            'divine_modifiers': divine_modifiers or {},
            'psycho_modifiers': psycho_modifiers or {},
            'calculated_stats': {},
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        # Calculate final stats
        for stat_name, base_value in base_stats.items():
            final_value = base_value
            
            # Apply stat modifiers (percentage)
            if stat_name in enhanced_stats['stat_modifiers']:
                modifier = enhanced_stats['stat_modifiers'][stat_name]
                final_value = int(final_value * (1 + modifier))
            
            # Apply divine modifiers
            if stat_name in enhanced_stats['divine_modifiers']:
                modifier = enhanced_stats['divine_modifiers'][stat_name]
                final_value = int(final_value * (1 + modifier))
            
            # Apply psycho modifiers
            if stat_name in enhanced_stats['psycho_modifiers']:
                modifier = enhanced_stats['psycho_modifiers'][stat_name]
                final_value = int(final_value * (1 + modifier))
            
            enhanced_stats['calculated_stats'][stat_name] = final_value
        
        self.enhanced_stats[entity_id] = enhanced_stats
        return {'success': True, 'enhanced_stats': enhanced_stats}
    
    def update_enhanced_stats(self, entity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update enhanced stats"""
        if entity_id not in self.enhanced_stats:
            return {'success': False, 'error': 'Entity not found'}
        
        stats = self.enhanced_stats[entity_id]
        stats.update(updates)
        stats['last_updated'] = datetime.utcnow().isoformat()
        
        # Recalculate stats
        return self.create_enhanced_stats(
            entity_id,
            stats['entity_type'],
            stats['base_stats'],
            stats.get('stat_modifiers', {}),
            stats.get('divine_modifiers', {}),
            stats.get('psycho_modifiers', {})
        )
    
    def get_enhanced_stats(self, entity_id: str) -> Dict[str, Any]:
        """Get enhanced stats for entity"""
        stats = self.enhanced_stats.get(entity_id)
        if not stats:
            return {'success': False, 'error': 'Entity not found'}
        return {'success': True, 'enhanced_stats': stats}
    
    def get_rule_history_v3(self, rule_id: str) -> Dict[str, Any]:
        """
        Get history for a rule
        """
        history = self.rule_history.get(rule_id, [])
        return {
            'success': True,
            'rule_id': rule_id,
            'history': history,
            'versions': len(history)
        }

# Global instance
compass_hourglass_system = CompassHourglassSystem()

