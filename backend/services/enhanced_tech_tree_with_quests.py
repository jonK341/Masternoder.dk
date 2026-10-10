"""
Enhanced Tech Tree System with Quest/Mission Control and Research/Conclusions
Extends the base tech tree system with quest integration and research conclusions
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.tech_tree_system import TechTreeSystem
    from backend.services.mission_quest_system import MissionQuestSystem
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class EnhancedTechTreeWithQuests:
    """
    Enhanced Tech Tree with Quest/Mission Control
    - Each tech tree node can have associated quests/missions
    - Research conclusions for each completed research
    - Quest completion unlocks tech tree nodes
    """
    
    def __init__(self):
        self.base_tech_tree = TechTreeSystem() if 'TechTreeSystem' in globals() else None
        self.mission_system = MissionQuestSystem() if 'MissionQuestSystem' in globals() else None
        self.tech_quests = defaultdict(dict)  # {tech_id: {quest_id: quest_data}}
        self.research_conclusions = defaultdict(dict)  # {tech_id: conclusion_data}
        self.quest_tech_unlocks = defaultdict(list)  # {quest_id: [tech_ids]}
        
    def add_quest_to_tech(self, tech_id: str, quest_id: str, quest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a quest/mission to a tech tree node"""
        if tech_id not in self.tech_quests:
            self.tech_quests[tech_id] = {}
        
        self.tech_quests[tech_id][quest_id] = {
            **quest_data,
            'tech_id': tech_id,
            'quest_id': quest_id,
            'added_at': datetime.utcnow().isoformat()
        }
        
        # Track reverse mapping
        if quest_id not in self.quest_tech_unlocks:
            self.quest_tech_unlocks[quest_id] = []
        if tech_id not in self.quest_tech_unlocks[quest_id]:
            self.quest_tech_unlocks[quest_id].append(tech_id)
        
        return {
            'success': True,
            'tech_id': tech_id,
            'quest_id': quest_id,
            'message': 'Quest added to tech tree node'
        }
    
    def add_research_conclusion(self, tech_id: str, conclusion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add research conclusion to a tech tree node"""
        self.research_conclusions[tech_id] = {
            **conclusion_data,
            'tech_id': tech_id,
            'created_at': datetime.utcnow().isoformat(),
            'conclusions': conclusion_data.get('conclusions', []),
            'findings': conclusion_data.get('findings', []),
            'implications': conclusion_data.get('implications', []),
            'next_steps': conclusion_data.get('next_steps', [])
        }
        
        return {
            'success': True,
            'tech_id': tech_id,
            'conclusion': self.research_conclusions[tech_id]
        }
    
    def get_tech_with_quests(self, user_id: str, tech_id: str) -> Dict[str, Any]:
        """Get tech tree node with associated quests and research conclusions"""
        if not self.base_tech_tree:
            return {'success': False, 'error': 'Base tech tree not available'}
        
        # Get base tech data
        tech_tree_result = self.base_tech_tree.get_tech_tree(user_id)
        tech_data = None
        for tech in tech_tree_result.get('tech_tree', []):
            if tech.get('id') == tech_id:
                tech_data = tech
                break
        
        if not tech_data:
            return {'success': False, 'error': 'Technology not found'}
        
        # Get associated quests
        tech_quests = list(self.tech_quests.get(tech_id, {}).values())
        
        # Get research conclusion
        research_conclusion = self.research_conclusions.get(tech_id)
        
        # Check if quests are completed (if this tech requires quest completion)
        quests_completed = True
        if tech_quests:
            if self.mission_system:
                user_quests = self.mission_system.get_user_daily_quests(user_id)
                quest_ids = [q.get('quest_id') for q in tech_quests]
                completed_quest_ids = [q.get('quest_id') for q in user_quests.get('quests', []) if q.get('status') == 'completed']
                quests_completed = all(qid in completed_quest_ids for qid in quest_ids)
        
        return {
            'success': True,
            'tech': tech_data,
            'associated_quests': tech_quests,
            'research_conclusion': research_conclusion,
            'quests_completed': quests_completed,
            'unlocked_by_quests': quests_completed
        }
    
    def complete_research_with_conclusion(self, user_id: str, tech_id: str, conclusion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete research and add conclusion"""
        if not self.base_tech_tree:
            return {'success': False, 'error': 'Base tech tree not available'}
        
        # Complete research
        result = self.base_tech_tree.complete_research(user_id, tech_id)
        if not result.get('success'):
            return result
        
        # Add research conclusion
        conclusion_result = self.add_research_conclusion(tech_id, conclusion_data)
        
        return {
            'success': True,
            'tech_id': tech_id,
            'research_completed': True,
            'conclusion': conclusion_result.get('conclusion'),
            'bonuses': result.get('bonuses', {}),
            'unlocks': result.get('unlocks', [])
        }
    
    def get_all_tech_with_quests(self, user_id: str) -> Dict[str, Any]:
        """Get all tech tree nodes with quests and conclusions"""
        if not self.base_tech_tree:
            return {'success': False, 'error': 'Base tech tree not available'}
        
        tech_tree_result = self.base_tech_tree.get_tech_tree(user_id)
        tech_list = []
        
        for tech in tech_tree_result.get('tech_tree', []):
            tech_id = tech.get('id')
            tech_with_quests = self.get_tech_with_quests(user_id, tech_id)
            tech_list.append(tech_with_quests)
        
        return {
            'success': True,
            'tech_tree': tech_list,
            'total_technologies': len(tech_list),
            'technologies_with_quests': len([t for t in tech_list if t.get('associated_quests')]),
            'technologies_with_conclusions': len([t for t in tech_list if t.get('research_conclusion')])
        }


# Global instance
enhanced_tech_tree_quests = EnhancedTechTreeWithQuests()

