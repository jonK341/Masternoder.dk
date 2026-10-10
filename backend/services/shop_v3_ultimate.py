"""
Shop System v3.0 - Ultimate Upgrade
New ideas, items, artifacts, and intelligence
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random
import json

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None
    advanced_intelligent_calculator = None


class ShopV3Ultimate:
    """
    Ultimate shop system v3.0 with:
    - New innovative items
    - Advanced artifacts
    - Intelligence-based recommendations
    - 178 point system integration
    - Knowledge and intelligence items
    """
    
    def __init__(self):
        self.items = {}
        self.artifacts = {}
        self.knowledge_items = {}
        self.intelligence_items = {}
        self.boosters = {}
        self.user_inventory = defaultdict(dict)
        self.purchase_history = defaultdict(list)
        self._initialize_all_items()
    
    def _initialize_all_items(self):
        """Initialize all shop items, artifacts, and knowledge items"""
        
        # NEW INNOVATIVE ITEMS
        self.items = {
            # Point System Boosters
            'point_multiplier_2x': {
                'id': 'point_multiplier_2x',
                'name': '2x Point Multiplier',
                'description': 'Double all point earnings for 24 hours',
                'price': 500,
                'category': 'booster',
                'rarity': 'rare',
                'duration_hours': 24,
                'effect': {'multiplier': 2.0, 'applies_to': 'all_points'},
                'icon': '⚡'
            },
            'point_multiplier_5x': {
                'id': 'point_multiplier_5x',
                'name': '5x Point Multiplier',
                'description': '5x all point earnings for 12 hours',
                'price': 2000,
                'category': 'booster',
                'rarity': 'epic',
                'duration_hours': 12,
                'effect': {'multiplier': 5.0, 'applies_to': 'all_points'},
                'icon': '🚀'
            },
            'death_portal_key': {
                'id': 'death_portal_key',
                'name': 'Death Portal Key',
                'description': 'Unlock Death Portal teleport system (10x multiplier)',
                'price': 5000,
                'category': 'special',
                'rarity': 'legendary',
                'effect': {'unlocks': 'death_portal', 'multiplier': 10.0},
                'icon': '🌀'
            },
            'production_10x_activator': {
                'id': 'production_10x_activator',
                'name': '10x Production Activator',
                'description': 'Activate 10x production multiplier for content generation',
                'price': 10000,
                'category': 'special',
                'rarity': 'legendary',
                'effect': {'unlocks': 'production_10x', 'multiplier': 10.0},
                'icon': '🎬'
            },
            'teleport_skillset_master': {
                'id': 'teleport_skillset_master',
                'name': 'Teleport Skillset Master',
                'description': 'Master teleport skillset abilities (1.5x bonus)',
                'price': 7500,
                'category': 'special',
                'rarity': 'legendary',
                'effect': {'unlocks': 'teleport_skillset', 'bonus': 1.5},
                'icon': '✨'
            },
            
            # Advanced Boosters
            'intelligence_booster': {
                'id': 'intelligence_booster',
                'name': 'Intelligence Booster',
                'description': 'Boost AI intelligence calculations (+50% accuracy)',
                'price': 1500,
                'category': 'booster',
                'rarity': 'epic',
                'duration_hours': 48,
                'effect': {'intelligence_bonus': 0.5},
                'icon': '🧠'
            },
            'calculation_accuracy_boost': {
                'id': 'calculation_accuracy_boost',
                'name': 'Calculation Accuracy Boost',
                'description': 'Improve calculator accuracy to A+ level',
                'price': 3000,
                'category': 'booster',
                'rarity': 'epic',
                'duration_hours': 72,
                'effect': {'accuracy_grade': 'A+', 'confidence_boost': 0.3},
                'icon': '📊'
            },
            
            # Behavior & Pattern Items
            'behavior_analyzer': {
                'id': 'behavior_analyzer',
                'name': 'Behavior Pattern Analyzer',
                'description': 'Advanced behavior pattern analysis tool',
                'price': 2500,
                'category': 'tool',
                'rarity': 'rare',
                'effect': {'unlocks': 'behavior_analysis', 'insights': True},
                'icon': '📈'
            },
            'pattern_detector': {
                'id': 'pattern_detector',
                'name': 'Pattern Detector',
                'description': 'Detect patterns in your activity and points',
                'price': 1800,
                'category': 'tool',
                'rarity': 'rare',
                'effect': {'unlocks': 'pattern_detection'},
                'icon': '🔍'
            },
        }
        
        # ADVANCED ARTIFACTS
        self.artifacts = {
            'ancient_calculator': {
                'id': 'ancient_calculator',
                'name': 'Ancient Calculator Artifact',
                'description': 'Legendary calculator artifact from 1000 years of engineering',
                'price': 50000,
                'category': 'artifact',
                'rarity': 'legendary',
                'effect': {
                    'unlocks': 'advanced_calculator',
                    'intelligence_boost': 2.0,
                    'accuracy_grade': 'A+',
                    'point_restoration': True
                },
                'icon': '⚛️',
                'lore': 'Forged over 1000 years, this artifact contains ultimate calculation power'
            },
            'point_restoration_crystal': {
                'id': 'point_restoration_crystal',
                'name': 'Point Restoration Crystal',
                'description': 'Automatically restore lost points',
                'price': 15000,
                'category': 'artifact',
                'rarity': 'epic',
                'effect': {
                    'auto_restore': True,
                    'restoration_confidence': 0.9,
                    'daily_restorations': 10
                },
                'icon': '💎'
            },
            'behavior_mastery_orb': {
                'id': 'behavior_mastery_orb',
                'name': 'Behavior Mastery Orb',
                'description': 'Master behavior pattern analysis',
                'price': 20000,
                'category': 'artifact',
                'rarity': 'epic',
                'effect': {
                    'behavior_insights': True,
                    'pattern_prediction': True,
                    'change_detection': True
                },
                'icon': '🔮'
            },
            '178_systems_compendium': {
                'id': '178_systems_compendium',
                'name': '178 Systems Compendium',
                'description': 'Complete knowledge of all 178 point systems',
                'price': 100000,
                'category': 'artifact',
                'rarity': 'legendary',
                'effect': {
                    'unlocks': 'all_178_systems',
                    'system_mastery': True,
                    'bonus_multiplier': 1.5
                },
                'icon': '📚'
            },
            'death_portal_artifact': {
                'id': 'death_portal_artifact',
                'name': 'Death Portal Artifact',
                'description': 'Ultimate Death Portal mastery artifact',
                'price': 75000,
                'category': 'artifact',
                'rarity': 'legendary',
                'effect': {
                    'death_portal_mastery': True,
                    'multiplier': 15.0,
                    'teleport_abilities': True
                },
                'icon': '🌀'
            },
        }
        
        # KNOWLEDGE ITEMS (178 Point System Context)
        self.knowledge_items = {
            'point_system_guide': {
                'id': 'point_system_guide',
                'name': 'Complete Point System Guide',
                'description': 'Comprehensive guide to all 178 point systems',
                'price': 5000,
                'category': 'knowledge',
                'rarity': 'rare',
                'effect': {
                    'unlocks': 'point_system_knowledge',
                    'context': 'all_178_systems',
                    'knowledge_points': 1000
                },
                'icon': '📖',
                'content': {
                    'systems_covered': 178,
                    'categories': 12,
                    'examples': True,
                    'strategies': True
                }
            },
            'calculator_mastery_book': {
                'id': 'calculator_mastery_book',
                'name': 'Calculator Mastery Book',
                'description': 'Master the advanced intelligent calculator',
                'price': 8000,
                'category': 'knowledge',
                'rarity': 'epic',
                'effect': {
                    'unlocks': 'calculator_knowledge',
                    'intelligence_boost': 0.3,
                    'knowledge_points': 2000
                },
                'icon': '📘',
                'content': {
                    'ai_intelligence': True,
                    'point_loss_detection': True,
                    'restoration_methods': True,
                    'predictive_analytics': True
                }
            },
            'behavior_pattern_encyclopedia': {
                'id': 'behavior_pattern_encyclopedia',
                'name': 'Behavior Pattern Encyclopedia',
                'description': 'Complete guide to behavior pattern analysis',
                'price': 6000,
                'category': 'knowledge',
                'rarity': 'rare',
                'effect': {
                    'unlocks': 'behavior_knowledge',
                    'pattern_recognition': True,
                    'knowledge_points': 1500
                },
                'icon': '📕',
                'content': {
                    'pattern_types': 10,
                    'detection_methods': True,
                    'analysis_techniques': True
                }
            },
            '178_systems_wisdom': {
                'id': '178_systems_wisdom',
                'name': '178 Systems Wisdom',
                'description': 'Ultimate wisdom of all 178 point systems',
                'price': 25000,
                'category': 'knowledge',
                'rarity': 'legendary',
                'effect': {
                    'unlocks': 'complete_system_wisdom',
                    'knowledge_points': 5000,
                    'intelligence_boost': 0.5
                },
                'icon': '📗',
                'content': {
                    'all_systems': True,
                    'advanced_strategies': True,
                    'optimization_guides': True,
                    'mastery_paths': True
                }
            },
        }
        
        # INTELLIGENCE ITEMS
        self.intelligence_items = {
            'ai_intelligence_core': {
                'id': 'ai_intelligence_core',
                'name': 'AI Intelligence Core',
                'description': 'Core AI intelligence module for advanced calculations',
                'price': 12000,
                'category': 'intelligence',
                'rarity': 'epic',
                'effect': {
                    'ai_intelligence': True,
                    'neural_network': True,
                    'intelligence_score': 100
                },
                'icon': '🤖'
            },
            'quantum_calculator_module': {
                'id': 'quantum_calculator_module',
                'name': 'Quantum Calculator Module',
                'description': 'Quantum-inspired calculation algorithms',
                'price': 15000,
                'category': 'intelligence',
                'rarity': 'epic',
                'effect': {
                    'quantum_algorithms': True,
                    'multi_dimensional': True,
                    'calculation_boost': 1.5
                },
                'icon': '⚛️'
            },
            'neural_network_processor': {
                'id': 'neural_network_processor',
                'name': 'Neural Network Processor',
                'description': 'Neural network analysis and pattern recognition',
                'price': 18000,
                'category': 'intelligence',
                'rarity': 'epic',
                'effect': {
                    'neural_analysis': True,
                    'pattern_recognition': True,
                    'learning_capability': True
                },
                'icon': '🧠'
            },
        }
        
        # UNIFIED POINTS ITEMS - Items purchasable with different point types
        self.unified_points_items = {
            # Battle Points Items
            'battle_armor_xp': {
                'id': 'battle_armor_xp',
                'name': '⚔️ Battle Armor',
                'description': 'Enhance your battle defense and attack power',
                'price': {'battle_points': 500, 'xp': 200},
                'category': 'battle',
                'rarity': 'rare',
                'effect': {'battle_defense': 0.25, 'battle_attack': 0.25},
                'icon': '🛡️',
                'unified_points_only': True
            },
            'battle_weapon_combat': {
                'id': 'battle_weapon_combat',
                'name': '⚔️ Legendary Weapon',
                'description': 'Legendary weapon for epic battles',
                'price': {'battle_points': 1000, 'combat_points': 300},
                'category': 'battle',
                'rarity': 'epic',
                'effect': {'battle_damage': 0.5, 'critical_chance': 0.15},
                'icon': '🗡️',
                'unified_points_only': True
            },
            'battle_energy_pack': {
                'id': 'battle_energy_pack',
                'name': '⚡ Energy Pack',
                'description': 'Replenish energy for battles',
                'price': {'energy_points': 100, 'activity_points': 50},
                'category': 'battle',
                'rarity': 'common',
                'effect': {'energy_restore': 100, 'energy_max': 20},
                'icon': '🔋',
                'unified_points_only': True
            },
            # Activity Points Items
            'activity_booster_xp': {
                'id': 'activity_booster_xp',
                'name': '📈 Activity Booster',
                'description': 'Boost all activity point gains',
                'price': {'activity_points': 300, 'xp': 150},
                'category': 'booster',
                'rarity': 'rare',
                'effect': {'activity_multiplier': 1.5, 'duration_hours': 24},
                'icon': '🚀',
                'unified_points_only': True
            },
            'activity_streak_protector': {
                'id': 'activity_streak_protector',
                'name': '🔥 Streak Protector',
                'description': 'Protect your activity streak once',
                'price': {'activity_points': 200, 'skill_points': 100},
                'category': 'utility',
                'rarity': 'epic',
                'effect': {'streak_protection': 1},
                'icon': '🛡️',
                'unified_points_only': True
            },
            # Skill Points Items
            'skill_learning_boost': {
                'id': 'skill_learning_boost',
                'name': '🧠 Learning Boost',
                'description': 'Accelerate skill learning rate',
                'price': {'skill_points': 400, 'xp': 250},
                'category': 'skill',
                'rarity': 'rare',
                'effect': {'learning_rate': 0.5, 'skill_exp_multiplier': 2.0},
                'icon': '📚',
                'unified_points_only': True
            },
            'skill_unlock_token': {
                'id': 'skill_unlock_token',
                'name': '🎯 Skill Unlock Token',
                'description': 'Instantly unlock any locked skill',
                'price': {'skill_points': 500, 'progression_points': 200},
                'category': 'skill',
                'rarity': 'epic',
                'effect': {'unlock_skill': True},
                'icon': '🔓',
                'unified_points_only': True
            },
            # Generation Points Items
            'generation_speed_boost': {
                'id': 'generation_speed_boost',
                'name': '⚡ Generation Speed Boost',
                'description': 'Speed up video generation process',
                'price': {'generation_points': 600, 'activity_points': 300},
                'category': 'generation',
                'rarity': 'rare',
                'effect': {'generation_speed': 0.3, 'duration_hours': 48},
                'icon': '🎬',
                'unified_points_only': True
            },
            'generation_quality_enhancer': {
                'id': 'generation_quality_enhancer',
                'name': '✨ Quality Enhancer',
                'description': 'Enhance video generation quality',
                'price': {'generation_points': 800, 'creative_points': 400},
                'category': 'generation',
                'rarity': 'epic',
                'effect': {'quality_boost': 0.25, 'creativity_boost': 0.15},
                'icon': '💎',
                'unified_points_only': True
            },
            # Progression Points Items
            'progression_accelerator': {
                'id': 'progression_accelerator',
                'name': '📊 Progression Accelerator',
                'description': 'Accelerate level progression',
                'price': {'progression_points': 500, 'xp': 300},
                'category': 'progression',
                'rarity': 'rare',
                'effect': {'xp_multiplier': 1.5, 'level_progression': 0.25},
                'icon': '⏩',
                'unified_points_only': True
            },
            'level_boost_pack': {
                'id': 'level_boost_pack',
                'name': '⭐ Level Boost Pack',
                'description': 'Gain instant XP boost',
                'price': {'progression_points': 300, 'xp': 200},
                'category': 'progression',
                'rarity': 'common',
                'effect': {'instant_xp': 1000},
                'icon': '📦',
                'unified_points_only': True
            },
            # Creative Points Items
            'creative_inspiration': {
                'id': 'creative_inspiration',
                'name': '🎨 Creative Inspiration',
                'description': 'Boost creativity for content creation',
                'price': {'creative_points': 400, 'skill_points': 200},
                'category': 'creative',
                'rarity': 'rare',
                'effect': {'creativity_boost': 0.4, 'inspiration_points': 500},
                'icon': '🌈',
                'unified_points_only': True
            },
            'creative_toolkit': {
                'id': 'creative_toolkit',
                'name': '🛠️ Creative Toolkit',
                'description': 'Complete toolkit for creative projects',
                'price': {'creative_points': 600, 'activity_points': 300},
                'category': 'creative',
                'rarity': 'epic',
                'effect': {'tool_unlock': True, 'creative_multiplier': 1.3},
                'icon': '🎭',
                'unified_points_only': True
            },
            # Social Points Items
            'social_network_boost': {
                'id': 'social_network_boost',
                'name': '👥 Social Network Boost',
                'description': 'Enhance social interactions and networking',
                'price': {'social_points': 350, 'activity_points': 200},
                'category': 'social',
                'rarity': 'rare',
                'effect': {'social_multiplier': 1.4, 'network_expansion': 0.2},
                'icon': '🌐',
                'unified_points_only': True
            },
            'collaboration_token': {
                'id': 'collaboration_token',
                'name': '🤝 Collaboration Token',
                'description': 'Enhanced collaboration abilities',
                'price': {'social_points': 250, 'skill_points': 150},
                'category': 'social',
                'rarity': 'epic',
                'effect': {'collaboration_bonus': 0.3, 'team_synergy': 0.25},
                'icon': '💼',
                'unified_points_only': True
            },
            # Achievement Points Items
            'achievement_unlocker': {
                'id': 'achievement_unlocker',
                'name': '🏆 Achievement Unlocker',
                'description': 'Unlock special achievements',
                'price': {'achievement_points': 800, 'progression_points': 400},
                'category': 'achievement',
                'rarity': 'epic',
                'effect': {'unlock_achievements': 3},
                'icon': '🎖️',
                'unified_points_only': True
            },
            'trophy_boost': {
                'id': 'trophy_boost',
                'name': '🥇 Trophy Boost',
                'description': 'Increase trophy collection rate',
                'price': {'achievement_points': 500, 'xp': 300},
                'category': 'achievement',
                'rarity': 'rare',
                'effect': {'trophy_rate': 0.5, 'rare_trophy_chance': 0.15},
                'icon': '🏅',
                'unified_points_only': True
            },
            # Premium Multi-Point Items
            'ultimate_point_pack': {
                'id': 'ultimate_point_pack',
                'name': '💎 Ultimate Point Pack',
                'description': 'Massive point pack with all point types',
                'price': {
                    'battle_points': 200,
                    'activity_points': 200,
                    'skill_points': 200,
                    'generation_points': 200,
                    'progression_points': 200
                },
                'category': 'premium',
                'rarity': 'legendary',
                'effect': {
                    'all_points_boost': 0.2,
                    'premium_bonus': 0.3,
                    'duration_days': 7
                },
                'icon': '💎',
                'unified_points_only': True
            },
            'mega_unified_booster': {
                'id': 'mega_unified_booster',
                'name': '🚀 Mega Unified Booster',
                'description': 'Boost all unified point categories',
                'price': {
                    'xp': 500,
                    'battle_points': 300,
                    'activity_points': 300,
                    'skill_points': 300
                },
                'category': 'premium',
                'rarity': 'legendary',
                'effect': {
                    'unified_multiplier': 2.0,
                    'all_categories': True,
                    'duration_hours': 72
                },
                'icon': '🌟',
                'unified_points_only': True
            },
            # Special Currency Items
            'coin_to_points_converter': {
                'id': 'coin_to_points_converter',
                'name': '🔄 Coin Converter',
                'description': 'Convert coins to unified points',
                'price': {'coins': 1000},
                'category': 'currency',
                'rarity': 'rare',
                'effect': {
                    'conversion_rate': 10,
                    'convert_to': 'unified_points'
                },
                'icon': '💱',
                'unified_points_only': False
            },
            'points_multiplier_all': {
                'id': 'points_multiplier_all',
                'name': '⚡ All Points Multiplier',
                'description': 'Multiply all unified point earnings',
                'price': {
                    'xp': 400,
                    'battle_points': 250,
                    'activity_points': 250,
                    'skill_points': 250,
                    'progression_points': 200
                },
                'category': 'premium',
                'rarity': 'legendary',
                'effect': {'multiplier': 3.0, 'duration_hours': 24},
                'icon': '✨',
                'unified_points_only': True
            },
            'predictive_analytics_engine': {
                'id': 'predictive_analytics_engine',
                'name': 'Predictive Analytics Engine',
                'description': 'Predict future points and trends',
                'price': 20000,
                'category': 'intelligence',
                'rarity': 'legendary',
                'effect': {
                    'predictive_analytics': True,
                    'future_forecasting': True,
                    'trend_analysis': True
                },
                'icon': '🔮'
            },
        }
        
        # BOOSTERS
        self.boosters = {
            'speed_booster': {
                'id': 'speed_booster',
                'name': 'Speed Booster',
                'description': '2x speed for all actions',
                'price': 1000,
                'category': 'booster',
                'rarity': 'common',
                'duration_hours': 24,
                'effect': {'speed_multiplier': 2.0},
                'icon': '⚡'
            },
            'luck_booster': {
                'id': 'luck_booster',
                'name': 'Luck Booster',
                'description': 'Increase luck for rare items and bonuses',
                'price': 1500,
                'category': 'booster',
                'rarity': 'rare',
                'duration_hours': 12,
                'effect': {'luck_multiplier': 1.5},
                'icon': '🍀'
            },
        }
    
    def get_all_items(self) -> Dict[str, Any]:
        """Get all shop items organized by category"""
        all_unified_items = list(getattr(self, 'unified_points_items', {}).values())
        return {
            'items': list(self.items.values()),
            'artifacts': list(self.artifacts.values()),
            'knowledge_items': list(self.knowledge_items.values()),
            'intelligence_items': list(self.intelligence_items.values()),
            'boosters': list(self.boosters.values()),
            'unified_points_items': all_unified_items,
            'total_items': (
                len(self.items) + len(self.artifacts) + 
                len(self.knowledge_items) + len(self.intelligence_items) + 
                len(self.boosters) + len(all_unified_items)
            )
        }
    
    def get_intelligent_recommendations(self, user_id: str) -> Dict[str, Any]:
        """Get intelligent item recommendations based on user's 178 point systems"""
        recommendations = {
            'recommended_items': [],
            'recommended_artifacts': [],
            'recommended_knowledge': [],
            'recommended_intelligence': [],
            'reasoning': []
        }
        
        try:
            if advanced_intelligent_calculator:
                # Get user's point data
                from backend.services.unified_point_counter import unified_point_counter
                all_points = unified_point_counter.get_all_points(user_id)
                
                # Analyze and recommend
                total_points = sum([v for k, v in all_points.items() if isinstance(v, (int, float)) and k.endswith('_points')])
                
                if total_points < 10000:
                    recommendations['recommended_items'].append(self.items['point_multiplier_2x'])
                    recommendations['reasoning'].append('Low point total - boost earnings')
                
                if all_points.get('death_portal_teleport_points', 0) == 0:
                    recommendations['recommended_artifacts'].append(self.artifacts['death_portal_key'])
                    recommendations['reasoning'].append('Unlock Death Portal for 10x multiplier')
                
                if all_points.get('production_10x_points', 0) == 0:
                    recommendations['recommended_artifacts'].append(self.artifacts['production_10x_activator'])
                    recommendations['reasoning'].append('Unlock 10x Production multiplier')
                
                # Always recommend knowledge
                recommendations['recommended_knowledge'].append(self.knowledge_items['point_system_guide'])
                recommendations['reasoning'].append('Knowledge improves all systems')
                
        except Exception as e:
            print(f"[ShopV3] Error getting recommendations: {e}", flush=True)
        
        return recommendations
    
    def purchase_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """Purchase item with 178 point system integration"""
        # Find item in all categories
        item = None
        item_category = None
        
        if item_id in self.items:
            item = self.items[item_id]
            item_category = 'items'
        elif item_id in self.artifacts:
            item = self.artifacts[item_id]
            item_category = 'artifacts'
        elif item_id in self.knowledge_items:
            item = self.knowledge_items[item_id]
            item_category = 'knowledge'
        elif item_id in self.intelligence_items:
            item = self.intelligence_items[item_id]
            item_category = 'intelligence'
        elif item_id in self.boosters:
            item = self.boosters[item_id]
            item_category = 'boosters'
        elif hasattr(self, 'unified_points_items') and item_id in self.unified_points_items:
            item = self.unified_points_items[item_id]
            item_category = 'unified_points'
        
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        # Handle unified points pricing
        if isinstance(item.get('price'), dict):
            # Item uses unified points pricing
            price_dict = item['price']
            total_price = price_dict.copy()  # Keep as dict for unified points
        else:
            # Traditional single price
            total_price = item['price'] * quantity
        
        # Handle unified points payment
        if isinstance(total_price, dict):
            # Check if user has enough unified points
            try:
                from backend.services.unified_point_system_reconstructed import unified_point_system
                user_points = unified_point_system.get_all_points(user_id)
                
                # Check each required point type
                for point_type, required_amount in total_price.items():
                    available = user_points.get(point_type, 0)
                    needed = required_amount * quantity
                    if available < needed:
                        return {
                            'success': False, 
                            'error': f'Not enough {point_type}. Need {needed}, have {available}'
                        }
                
                # Deduct unified points
                for point_type, required_amount in total_price.items():
                    needed = required_amount * quantity
                    unified_point_system.deduct_points(user_id, point_type, needed, f'shop_purchase_{item_id}')
                
                shop_points = sum(total_price.values()) // 10
            except Exception as e:
                return {'success': False, 'error': f'Payment processing failed: {str(e)}'}
        else:
            # Traditional payment (coins)
            shop_points = total_price // 10
        
        total_shop_points = shop_points
        
        # Add to inventory
        if item_id not in self.user_inventory[user_id]:
            self.user_inventory[user_id][item_id] = 0
        self.user_inventory[user_id][item_id] += quantity
        
        # Record purchase
        purchase = {
            'item_id': item_id,
            'item_name': item['name'],
            'category': item_category,
            'quantity': quantity,
            'price': total_price,
            'shop_points': total_shop_points,
            'unified_points_purchase': isinstance(total_price, dict),
            'timestamp': datetime.utcnow().isoformat()
        }
        self.purchase_history[user_id].append(purchase)
        
        # Award points via unified system
        if point_connection:
            try:
                point_connection.ensure_point_counting(user_id, 'shop_points', total_shop_points, 'shop_purchase')
            except:
                pass
        
        # Award points for purchase (if applicable)
        try:
            from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
            from backend.services.unified_point_system_reconstructed import unified_point_system
            enhanced_game_mechanics.set_unified_points(unified_point_system)
            points_awarded = enhanced_game_mechanics.award_comprehensive_points(
                user_id=user_id,
                action='shop_purchase',
                difficulty='normal',
                multiplier=1.0,
                metadata={
                    'item_id': item_id,
                    'item_name': item['name'],
                    'category': item_category,
                    'unified_points_purchase': isinstance(total_price, dict)
                }
            )
        except:
            points_awarded = {}
        
        # Integrate with monetization system
        try:
            from backend.services.v3_monetization_integration import v3_monetization_integration
            monetization_result = v3_monetization_integration.integrate_shop_v3_purchase(
                user_id=user_id,
                item_id=item_id,
                purchase_data=purchase
            )
        except:
            monetization_result = None
        
        return {
            'success': True,
            'item': item,
            'quantity': quantity,
            'total_price': total_price,
            'shop_points_awarded': total_shop_points,
            'inventory': self.user_inventory[user_id],
            'monetization': monetization_result
        }


# Global instance
shop_v3_ultimate = ShopV3Ultimate()

