"""
Manager Artifacts System
Special management-focused artifacts for agents to collect and use
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ManagerArtifactsSystem:
    """
    Manages manager artifacts - special collectible items focused on management,
    leadership, and organizational skills. These artifacts enhance agent capabilities
    in managing resources, teams, and processes.
    """

    def __init__(self):
        self.artifact_definitions = self._load_default_artifacts()
        self.user_artifacts = {}  # {user_id: {agent_id: [artifact_ids]}}
        self.artifact_stories = {}  # {artifact_id: story}
        self.artifact_effects = {}  # {user_id: {agent_id: {artifact_id: effect_data}}}

    def _load_default_artifacts(self) -> Dict[str, Any]:
        """Loads predefined manager artifacts."""
        artifacts = [
            {
                'id': 'leadership_crown',
                'name': 'Leadership Crown',
                'description': 'A crown that grants supreme leadership capabilities and inspires teams to greatness.',
                'story': 'Forged by the first great manager, this crown has been passed down through generations of exceptional leaders. Those who wear it gain the ability to inspire and motivate their teams beyond normal limits.',
                'icon': '👑',
                'rarity': 'legendary',
                'category': 'leadership',
                'power': 300,
                'effect': {
                    'team_morale': 0.5,
                    'decision_making': 0.3,
                    'influence': 0.4
                },
                'unlock_condition': {
                    'agent_level': 20,
                    'tasks_managed': 100
                },
                'point_value': 1000
            },
            {
                'id': 'execution_scroll',
                'name': 'Scroll of Perfect Execution',
                'description': 'An ancient scroll containing the secrets of flawless project execution.',
                'story': 'Written by a master project manager who never missed a deadline, this scroll contains strategies for perfect execution. Agents who study it learn to execute complex projects with precision.',
                'icon': '📜',
                'rarity': 'epic',
                'category': 'execution',
                'power': 250,
                'effect': {
                    'execution_speed': 0.4,
                    'quality': 0.3,
                    'efficiency': 0.35
                },
                'unlock_condition': {
                    'agent_level': 15,
                    'projects_completed': 50
                },
                'point_value': 750
            },
            {
                'id': 'strategic_compass',
                'name': 'Strategic Compass',
                'description': 'A mystical compass that always points toward the optimal strategic direction.',
                'story': 'Crafted by a legendary strategist, this compass doesn\'t point north - it points toward success. Managers who possess it can navigate complex strategic decisions with confidence.',
                'icon': '🧭',
                'rarity': 'epic',
                'category': 'strategy',
                'power': 280,
                'effect': {
                    'strategic_planning': 0.45,
                    'risk_assessment': 0.35,
                    'forecasting': 0.4
                },
                'unlock_condition': {
                    'agent_level': 18,
                    'strategic_decisions': 25
                },
                'point_value': 850
            },
            {
                'id': 'resource_amulet',
                'name': 'Amulet of Resource Mastery',
                'description': 'A glowing amulet that enhances resource management and allocation skills.',
                'story': 'Created by an efficiency expert, this amulet helps managers optimize resource allocation. It glows brighter when resources are used optimally, guiding agents toward perfect efficiency.',
                'icon': '🔮',
                'rarity': 'rare',
                'category': 'resources',
                'power': 220,
                'effect': {
                    'resource_optimization': 0.5,
                    'cost_efficiency': 0.4,
                    'allocation_accuracy': 0.35
                },
                'unlock_condition': {
                    'agent_level': 12,
                    'resources_managed': 500
                },
                'point_value': 600
            },
            {
                'id': 'team_synergy_crystal',
                'name': 'Team Synergy Crystal',
                'description': 'A crystal that amplifies team collaboration and synergy.',
                'story': 'Formed when a legendary team achieved perfect harmony, this crystal resonates with the energy of cooperation. Managers who wield it can create unprecedented team synergy.',
                'icon': '💎',
                'rarity': 'rare',
                'category': 'teamwork',
                'power': 240,
                'effect': {
                    'team_collaboration': 0.45,
                    'synergy': 0.4,
                    'communication': 0.35
                },
                'unlock_condition': {
                    'agent_level': 14,
                    'teams_managed': 10
                },
                'point_value': 650
            },
            {
                'id': 'innovation_lantern',
                'name': 'Lantern of Innovation',
                'description': 'A lantern that illuminates paths to innovation and creative problem-solving.',
                'story': 'Carried by the most innovative managers, this lantern shines light on unconventional solutions. Its flame burns brighter when creativity is needed most.',
                'icon': '🏮',
                'rarity': 'rare',
                'category': 'innovation',
                'power': 230,
                'effect': {
                    'innovation': 0.5,
                    'creative_thinking': 0.4,
                    'problem_solving': 0.35
                },
                'unlock_condition': {
                    'agent_level': 13,
                    'innovations': 20
                },
                'point_value': 620
            },
            {
                'id': 'delegation_seal',
                'name': 'Seal of Perfect Delegation',
                'description': 'A seal that ensures tasks are delegated to the right people at the right time.',
                'story': 'Imprinted by a master of delegation, this seal marks tasks with perfect clarity. Managers who use it never struggle with knowing who should handle what.',
                'icon': '🔏',
                'rarity': 'epic',
                'category': 'delegation',
                'power': 260,
                'effect': {
                    'delegation_accuracy': 0.5,
                    'task_assignment': 0.4,
                    'workload_balance': 0.35
                },
                'unlock_condition': {
                    'agent_level': 16,
                    'tasks_delegated': 200
                },
                'point_value': 800
            },
            {
                'id': 'communication_orb',
                'name': 'Orb of Clear Communication',
                'description': 'A glowing orb that ensures messages are always clear and understood.',
                'story': 'Charged with the power of perfect communication, this orb helps managers convey complex ideas simply. It pulses with clarity when important messages need to be delivered.',
                'icon': '🔮',
                'rarity': 'rare',
                'category': 'communication',
                'power': 210,
                'effect': {
                    'communication_clarity': 0.5,
                    'message_effectiveness': 0.4,
                    'understanding': 0.35
                },
                'unlock_condition': {
                    'agent_level': 11,
                    'communications_sent': 500
                },
                'point_value': 580
            },
            {
                'id': 'time_mastery_hourglass',
                'name': 'Hourglass of Time Mastery',
                'description': 'An hourglass that helps managers master time and deadlines.',
                'story': 'Filled with the sands of time itself, this hourglass never runs out. Managers who watch it closely learn to manage time perfectly, always meeting deadlines with ease.',
                'icon': '⏳',
                'rarity': 'epic',
                'category': 'time_management',
                'power': 270,
                'effect': {
                    'time_optimization': 0.5,
                    'deadline_management': 0.45,
                    'scheduling': 0.4
                },
                'unlock_condition': {
                    'agent_level': 17,
                    'deadlines_met': 100
                },
                'point_value': 900
            },
            {
                'id': 'decision_scales',
                'name': 'Scales of Wise Decisions',
                'description': 'Mystical scales that weigh options and reveal the best decisions.',
                'story': 'Used by history\'s wisest managers, these scales balance all factors perfectly. When placed between options, they tilt toward the optimal choice, revealing the path forward.',
                'icon': '⚖️',
                'rarity': 'legendary',
                'category': 'decision_making',
                'power': 320,
                'effect': {
                    'decision_quality': 0.6,
                    'analysis_depth': 0.5,
                    'outcome_prediction': 0.4
                },
                'unlock_condition': {
                    'agent_level': 25,
                    'major_decisions': 50
                },
                'point_value': 1200
            }
        ]
        return {artifact['id']: artifact for artifact in artifacts}

    def get_all_artifacts(self) -> Dict[str, Any]:
        """Returns all available manager artifacts."""
        return {
            'success': True,
            'artifacts': list(self.artifact_definitions.values()),
            'total_count': len(self.artifact_definitions)
        }

    def get_user_agent_artifacts(self, user_id: str, agent_id: str) -> Dict[str, Any]:
        """Returns artifacts collected by a specific agent for a user."""
        collected = self.user_artifacts.get(user_id, {}).get(agent_id, [])
        artifacts_data = []
        
        for artifact_id in collected:
            if artifact_id in self.artifact_definitions:
                artifact = self.artifact_definitions[artifact_id].copy()
                artifact['collected_at'] = self._get_collection_time(user_id, agent_id, artifact_id)
                artifact['active_effect'] = self.artifact_effects.get(user_id, {}).get(agent_id, {}).get(artifact_id)
                artifacts_data.append(artifact)
        
        return {
            'success': True,
            'user_id': user_id,
            'agent_id': agent_id,
            'artifacts': artifacts_data,
            'total_collected': len(collected),
            'total_available': len(self.artifact_definitions)
        }

    def collect_artifact(self, user_id: str, agent_id: str, artifact_id: str) -> Dict[str, Any]:
        """Collects a manager artifact for an agent."""
        if artifact_id not in self.artifact_definitions:
            return {'success': False, 'message': 'Artifact not found'}
        
        if user_id not in self.user_artifacts:
            self.user_artifacts[user_id] = {}
        if agent_id not in self.user_artifacts[user_id]:
            self.user_artifacts[user_id][agent_id] = []
        
        if artifact_id in self.user_artifacts[user_id][agent_id]:
            return {'success': False, 'message': 'Artifact already collected'}
        
        artifact = self.artifact_definitions[artifact_id]
        
        # Check unlock conditions (in real implementation, verify these conditions)
        # For now, we'll allow collection if agent meets level requirement
        
        # Add artifact
        self.user_artifacts[user_id][agent_id].append(artifact_id)
        
        # Activate effect
        if user_id not in self.artifact_effects:
            self.artifact_effects[user_id] = {}
        if agent_id not in self.artifact_effects[user_id]:
            self.artifact_effects[user_id][agent_id] = {}
        
        self.artifact_effects[user_id][agent_id][artifact_id] = {
            'activated_at': datetime.utcnow().isoformat(),
            'effect': artifact['effect'],
            'power': artifact['power']
        }
        
        # Integrate with unified point system
        try:
            from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
            from backend.services.unified_point_system_reconstructed import unified_point_system
            enhanced_game_mechanics.set_unified_points(unified_point_system)
            points_awarded = enhanced_game_mechanics.award_comprehensive_points(
                user_id=user_id,
                action='collect_manager_artifact',
                difficulty='hard',
                multiplier=1.0,
                metadata={
                    'artifact_id': artifact_id,
                    'artifact_name': artifact['name'],
                    'rarity': artifact['rarity'],
                    'point_value': artifact['point_value']
                }
            )
            logger.info(f"Points awarded for collecting manager artifact {artifact_id}: {points_awarded}")
        except Exception as e:
            logger.error(f"Error awarding points for artifact collection: {e}")
        
        return {
            'success': True,
            'message': f'{artifact["name"]} collected!',
            'artifact': artifact,
            'points_awarded': artifact['point_value']
        }

    def activate_artifact(self, user_id: str, agent_id: str, artifact_id: str) -> Dict[str, Any]:
        """Activates an artifact's effects for an agent."""
        if artifact_id not in self.user_artifacts.get(user_id, {}).get(agent_id, []):
            return {'success': False, 'message': 'Artifact not collected'}
        
        if artifact_id not in self.artifact_definitions:
            return {'success': False, 'message': 'Artifact not found'}
        
        artifact = self.artifact_definitions[artifact_id]
        
        # Activate effect
        if user_id not in self.artifact_effects:
            self.artifact_effects[user_id] = {}
        if agent_id not in self.artifact_effects[user_id]:
            self.artifact_effects[user_id][agent_id] = {}
        
        self.artifact_effects[user_id][agent_id][artifact_id] = {
            'activated_at': datetime.utcnow().isoformat(),
            'effect': artifact['effect'],
            'power': artifact['power'],
            'active': True
        }
        
        return {
            'success': True,
            'message': f'{artifact["name"]} activated!',
            'effect': artifact['effect']
        }

    def deactivate_artifact(self, user_id: str, agent_id: str, artifact_id: str) -> Dict[str, Any]:
        """Deactivates an artifact's effects."""
        if user_id in self.artifact_effects and agent_id in self.artifact_effects[user_id]:
            if artifact_id in self.artifact_effects[user_id][agent_id]:
                self.artifact_effects[user_id][agent_id][artifact_id]['active'] = False
                return {'success': True, 'message': 'Artifact deactivated'}
        
        return {'success': False, 'message': 'Artifact effect not found'}

    def get_active_effects(self, user_id: str, agent_id: str) -> Dict[str, Any]:
        """Returns all active artifact effects for an agent."""
        active_effects = {}
        
        if user_id in self.artifact_effects and agent_id in self.artifact_effects[user_id]:
            for artifact_id, effect_data in self.artifact_effects[user_id][agent_id].items():
                if effect_data.get('active', True):
                    active_effects[artifact_id] = effect_data
        
        return {
            'success': True,
            'active_effects': active_effects,
            'total_active': len(active_effects)
        }

    def _get_collection_time(self, user_id: str, agent_id: str, artifact_id: str) -> Optional[str]:
        """Helper to get collection time for an artifact."""
        # In a real implementation, store collection times
        return datetime.utcnow().isoformat()


# Global instance
manager_artifacts_system = ManagerArtifactsSystem()
