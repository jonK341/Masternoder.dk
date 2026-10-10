"""
Battle Arena Agents System
Extra agents for battle arena operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.battle_arena_gear_system import battle_arena_gear_system
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    from backend.services.unified_point_counter import unified_point_counter
except ImportError:
    battle_arena_gear_system = None
    advanced_intelligent_calculator = None
    unified_point_counter = None


class BattleArenaGearAgent:
    """Agent 1: Handles gear operations and recommendations"""
    
    def __init__(self):
        self.agent_id = f"gear_agent_{uuid.uuid4().hex[:8]}"
        self.agent_type = "gear_operations"
        self.tasks_completed = 0
        self.recommendations_given = 0
    
    def recommend_gear(self, user_id: str, battle_type: str = None) -> Dict[str, Any]:
        """Recommend gear based on user stats and battle type"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            # Get user gear
            user_gear = battle_arena_gear_system.get_user_gear(user_id)
            total_stats = user_gear.get('total_stats', {})
            
            # Get user divisions
            divisions = battle_arena_gear_system.get_user_divisions(user_id)
            
            # Generate recommendations
            recommendations = []
            all_definitions = battle_arena_gear_system.gear_definitions
            
            for gear_id, gear_def in all_definitions.items():
                if battle_type and gear_def.get('type') != battle_type:
                    continue
                
                stats = battle_arena_gear_system.calculate_gear_stats(user_id, gear_id)
                final_stats = stats.get('final_stats', {})
                
                # Calculate improvement
                improvement = {
                    'attack': final_stats.get('attack', 0) - total_stats.get('attack', 0),
                    'defense': final_stats.get('defense', 0) - total_stats.get('defense', 0),
                    'health': final_stats.get('health', 0) - total_stats.get('health', 0)
                }
                
                total_improvement = sum(improvement.values())
                
                if total_improvement > 0:
                    recommendations.append({
                        'gear_id': gear_id,
                        'gear': gear_def,
                        'improvement': improvement,
                        'total_improvement': total_improvement,
                        'calculated_stats': final_stats
                    })
            
            # Sort by improvement
            recommendations.sort(key=lambda x: x['total_improvement'], reverse=True)
            
            self.recommendations_given += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'recommendations': recommendations[:5],  # Top 5
                'user_stats': total_stats,
                'divisions_used': divisions
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}
    
    def optimize_gear_loadout(self, user_id: str) -> Dict[str, Any]:
        """Optimize user's gear loadout"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            # Get current gear
            current_gear = battle_arena_gear_system.get_user_gear(user_id)
            inventory = battle_arena_gear_system.get_inventory(user_id)
            
            # Optimize each slot
            optimized = {}
            for slot in ['head', 'weapon', 'armor', 'accessory', 'boots']:
                slot_gear = [g for g in inventory.get('inventory', []) if g.get('type') == slot]
                
                if slot_gear:
                    # Find best gear for slot
                    best_gear = max(slot_gear, key=lambda g: sum(g.get('calculated_stats', {}).values()))
                    optimized[slot] = best_gear.get('id')
            
            self.tasks_completed += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'optimized_loadout': optimized,
                'current_loadout': current_gear.get('equipped', [])
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}


class BattleArenaStatsAgent:
    """Agent 2: Handles stats calculations and analysis"""
    
    def __init__(self):
        self.agent_id = f"stats_agent_{uuid.uuid4().hex[:8]}"
        self.agent_type = "stats_analysis"
        self.calculations_completed = 0
    
    def analyze_gear_stats(self, user_id: str, gear_id: str) -> Dict[str, Any]:
        """Analyze gear stats with detailed breakdown"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            stats = battle_arena_gear_system.calculate_gear_stats(user_id, gear_id)
            
            # Detailed analysis
            analysis = {
                'base_stats': stats.get('base_stats', {}),
                'final_stats': stats.get('final_stats', {}),
                'multipliers': stats.get('multipliers', {}),
                'divisions': stats.get('divisions', {}),
                'stat_increases': {
                    'attack': stats.get('final_stats', {}).get('attack', 0) - stats.get('base_stats', {}).get('attack', 0),
                    'defense': stats.get('final_stats', {}).get('defense', 0) - stats.get('base_stats', {}).get('defense', 0),
                    'health': stats.get('final_stats', {}).get('health', 0) - stats.get('base_stats', {}).get('health', 0)
                }
            }
            
            self.calculations_completed += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'analysis': analysis,
                'gear_id': gear_id
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}
    
    def compare_gear(self, user_id: str, gear_id1: str, gear_id2: str) -> Dict[str, Any]:
        """Compare two pieces of gear"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            stats1 = battle_arena_gear_system.calculate_gear_stats(user_id, gear_id1)
            stats2 = battle_arena_gear_system.calculate_gear_stats(user_id, gear_id2)
            
            comparison = {
                'gear1': {
                    'id': gear_id1,
                    'stats': stats1.get('final_stats', {})
                },
                'gear2': {
                    'id': gear_id2,
                    'stats': stats2.get('final_stats', {})
                },
                'differences': {
                    'attack': stats2.get('final_stats', {}).get('attack', 0) - stats1.get('final_stats', {}).get('attack', 0),
                    'defense': stats2.get('final_stats', {}).get('defense', 0) - stats1.get('final_stats', {}).get('defense', 0),
                    'health': stats2.get('final_stats', {}).get('health', 0) - stats1.get('final_stats', {}).get('health', 0)
                }
            }
            
            self.calculations_completed += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'comparison': comparison
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}


class BattleArenaDivisionAgent:
    """Agent 3: Handles division data extraction and processing"""
    
    def __init__(self):
        self.agent_id = f"division_agent_{uuid.uuid4().hex[:8]}"
        self.agent_type = "division_processing"
        self.extractions_completed = 0
    
    def extract_divisions(self, user_id: str) -> Dict[str, Any]:
        """Extract and process user divisions"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            divisions = battle_arena_gear_system.get_user_divisions(user_id)
            
            # Process divisions
            processed = {
                'my_index': {
                    'value': divisions.get('my_index', 0),
                    'multiplier': 1.0 + (divisions.get('my_index', 0) * 0.01),
                    'source': 'UserProfile.level or total_xp'
                },
                'egos_subconscious_preferences': {
                    'value': divisions.get('egos_subconscious_preferences', {}),
                    'count': len(divisions.get('egos_subconscious_preferences', {})),
                    'multiplier': 1.0 + (len(divisions.get('egos_subconscious_preferences', {})) * 0.05),
                    'source': 'UserProfile.preferences.subconscious'
                },
                'my_mobil': {
                    'value': divisions.get('my_mobil', {}),
                    'count': len(divisions.get('my_mobil', {})),
                    'multiplier': 1.0 + (len(divisions.get('my_mobil', {})) * 0.03),
                    'source': 'UserProfile.settings.mobile'
                },
                'invalideret_visual_brian_sector': {
                    'value': divisions.get('invalideret_visual_brian_sector', {}),
                    'count': len(divisions.get('invalideret_visual_brian_sector', {})),
                    'multiplier': 1.0 + (len(divisions.get('invalideret_visual_brian_sector', {})) * 0.04),
                    'source': 'UserProfile.catch_stats.visual'
                }
            }
            
            # Calculate total multiplier
            total_multiplier = 1.0
            for div in processed.values():
                total_multiplier *= div.get('multiplier', 1.0)
            
            processed['total_multiplier'] = total_multiplier
            
            self.extractions_completed += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'divisions': processed,
                'raw_divisions': divisions
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}


class BattleArenaCalculatorAgent:
    """Agent 4: Handles calculator integration"""
    
    def __init__(self):
        self.agent_id = f"calculator_agent_{uuid.uuid4().hex[:8]}"
        self.agent_type = "calculator_integration"
        self.calculations_completed = 0
    
    def calculate_with_calculator(self, user_id: str, point_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Calculate gear stats using advanced calculator"""
        try:
            if not advanced_intelligent_calculator:
                return {'success': False, 'error': 'Calculator not available'}
            
            # Get point data if not provided
            if not point_data and unified_point_counter:
                point_data = unified_point_counter.get_all_points(user_id) or {}
            
            # Calculate with calculator
            calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                point_data, user_id
            )
            
            # Extract relevant data
            result = {
                'final_calculation': calc_result.get('final_calculation', {}),
                'base_calculation': calc_result.get('base_calculation', {}),
                'multipliers': calc_result.get('intelligent_multipliers', {}),
                'confidence_score': calc_result.get('confidence_score', 0),
                'advanced_features': calc_result.get('advanced_features', {})
            }
            
            self.calculations_completed += 1
            
            return {
                'success': True,
                'agent_id': self.agent_id,
                'calculator_result': result
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}


class BattleArenaInventoryAgent:
    """Agent 5: Handles inventory management and operations"""
    
    def __init__(self):
        self.agent_id = f"inventory_agent_{uuid.uuid4().hex[:8]}"
        self.agent_type = "inventory_management"
        self.operations_completed = 0
    
    def manage_inventory(self, user_id: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Manage inventory operations"""
        try:
            if not battle_arena_gear_system:
                return {'success': False, 'error': 'Gear system not available'}
            
            if operation == 'get':
                inventory = battle_arena_gear_system.get_inventory(user_id)
                return {'success': True, 'agent_id': self.agent_id, 'inventory': inventory}
            
            elif operation == 'add':
                gear_id = kwargs.get('gear_id')
                quantity = kwargs.get('quantity', 1)
                result = battle_arena_gear_system.add_gear_to_inventory(user_id, gear_id, quantity)
                self.operations_completed += 1
                return {'success': True, 'agent_id': self.agent_id, 'result': result}
            
            elif operation == 'equip':
                gear_id = kwargs.get('gear_id')
                result = battle_arena_gear_system.equip_gear(user_id, gear_id)
                self.operations_completed += 1
                return {'success': True, 'agent_id': self.agent_id, 'result': result}
            
            elif operation == 'unequip':
                slot = kwargs.get('slot')
                result = battle_arena_gear_system.unequip_gear(user_id, slot)
                self.operations_completed += 1
                return {'success': True, 'agent_id': self.agent_id, 'result': result}
            
            else:
                return {'success': False, 'error': f'Unknown operation: {operation}'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'agent_id': self.agent_id}


class BattleArenaAgentSystem:
    """Main agent system that coordinates all agents"""
    
    def __init__(self):
        self.gear_agent = BattleArenaGearAgent()
        self.stats_agent = BattleArenaStatsAgent()
        self.division_agent = BattleArenaDivisionAgent()
        self.calculator_agent = BattleArenaCalculatorAgent()
        self.inventory_agent = BattleArenaInventoryAgent()
        self.agents = {
            'gear': self.gear_agent,
            'stats': self.stats_agent,
            'division': self.division_agent,
            'calculator': self.calculator_agent,
            'inventory': self.inventory_agent
        }
    
    def get_agent(self, agent_type: str):
        """Get agent by type"""
        return self.agents.get(agent_type)
    
    def get_all_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        return {
            'agents': {
                agent_type: {
                    'agent_id': agent.agent_id,
                    'agent_type': agent.agent_type,
                    'tasks_completed': getattr(agent, 'tasks_completed', 0) or 
                                     getattr(agent, 'calculations_completed', 0) or 
                                     getattr(agent, 'extractions_completed', 0) or 
                                     getattr(agent, 'operations_completed', 0) or 
                                     getattr(agent, 'recommendations_given', 0) or 0
                }
                for agent_type, agent in self.agents.items()
            },
            'total_agents': len(self.agents)
        }


# Global instance
battle_arena_agent_system = BattleArenaAgentSystem()

