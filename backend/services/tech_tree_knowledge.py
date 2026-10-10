"""
Tech Tree Knowledge System
Adds knowledge nodes to tech tree
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class TechTreeKnowledge:
    """
    Knowledge system for tech tree
    Adds knowledge nodes, research branches, and discoveries
    """
    
    def __init__(self):
        self.knowledge_nodes = {
            'monetization': {
                'id': 'monetization',
                'name': 'Monetization Knowledge',
                'description': 'How to turn resources into cash',
                'prerequisites': [],
                'unlocked': False,
                'knowledge_points': 100
            },
            'cash_generation': {
                'id': 'cash_generation',
                'name': 'Cash Generation',
                'description': 'Advanced cash generation techniques',
                'prerequisites': ['monetization'],
                'unlocked': False,
                'knowledge_points': 200
            },
            'resource_optimization': {
                'id': 'resource_optimization',
                'name': 'Resource Optimization',
                'description': 'Optimize resource generation',
                'prerequisites': ['cash_generation'],
                'unlocked': False,
                'knowledge_points': 300
            },
            'trophy_system': {
                'id': 'trophy_system',
                'name': 'Trophy System',
                'description': 'Victory trophy generation',
                'prerequisites': ['resource_optimization'],
                'unlocked': False,
                'knowledge_points': 400
            },
            'top_performer': {
                'id': 'top_performer',
                'name': 'Top Performer Knowledge',
                'description': 'Knowledge for top 6 performers',
                'prerequisites': ['trophy_system'],
                'unlocked': False,
                'knowledge_points': 500
            },
            'advanced_battles': {
                'id': 'advanced_battles',
                'name': 'Advanced Battle Knowledge',
                'description': 'Insane battle techniques and strategies',
                'prerequisites': ['top_performer'],
                'unlocked': False,
                'knowledge_points': 600
            }
        }
        
        self.user_knowledge = {}  # user_id -> [knowledge_ids]
        self.knowledge_research = {}  # user_id -> [research_data]
    
    def unlock_knowledge(self, user_id: str, knowledge_id: str) -> Dict[str, Any]:
        """Unlock knowledge node"""
        if knowledge_id not in self.knowledge_nodes:
            return {'success': False, 'error': 'Knowledge node not found'}
        
        knowledge = self.knowledge_nodes[knowledge_id]
        
        # Check prerequisites
        if user_id not in self.user_knowledge:
            self.user_knowledge[user_id] = []
        
        for prereq in knowledge['prerequisites']:
            if prereq not in self.user_knowledge[user_id]:
                return {
                    'success': False,
                    'error': f'Prerequisite {prereq} not unlocked'
                }
        
        # Unlock knowledge
        if knowledge_id not in self.user_knowledge[user_id]:
            self.user_knowledge[user_id].append(knowledge_id)
            self.knowledge_nodes[knowledge_id]['unlocked'] = True
        
        return {
            'success': True,
            'user_id': user_id,
            'knowledge_id': knowledge_id,
            'knowledge': knowledge,
            'unlocked_at': datetime.utcnow().isoformat()
        }
    
    def get_user_knowledge(self, user_id: str) -> Dict[str, Any]:
        """Get user knowledge"""
        unlocked = self.user_knowledge.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'unlocked_knowledge': unlocked,
            'available_knowledge': [
                k for k, v in self.knowledge_nodes.items()
                if k not in unlocked
            ],
            'total_knowledge_points': sum([
                self.knowledge_nodes[k]['knowledge_points']
                for k in unlocked
            ])
        }
    
    def add_knowledge_to_tech_tree(self, tech_tree_data: Dict) -> Dict[str, Any]:
        """Add knowledge nodes to existing tech tree"""
        knowledge_branch = {
            'branch_id': 'knowledge',
            'branch_name': 'Knowledge System',
            'nodes': []
        }
        
        for knowledge_id, knowledge in self.knowledge_nodes.items():
            knowledge_branch['nodes'].append({
                'id': knowledge_id,
                'name': knowledge['name'],
                'description': knowledge['description'],
                'knowledge_points': knowledge['knowledge_points'],
                'prerequisites': knowledge['prerequisites']
            })
        
        # Add to tech tree
        if 'branches' not in tech_tree_data:
            tech_tree_data['branches'] = []
        
        tech_tree_data['branches'].append(knowledge_branch)
        
        return {
            'success': True,
            'tech_tree': tech_tree_data,
            'knowledge_branch': knowledge_branch
        }

# Global instance
tech_tree_knowledge = TechTreeKnowledge()

