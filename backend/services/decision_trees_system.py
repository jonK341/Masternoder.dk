"""
Decision Trees System - Build Decision Trees with All Knowledge
Tech and progress knowledge organized into decision trees
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.tech_tree_system import TechTreeSystem
    from backend.services.unified_game_mechanics_constructor import unified_game_mechanics
    from backend.services.unified_points_database import UnifiedPointsDatabase
    unified_points_db = UnifiedPointsDatabase()
except ImportError:
    TechTreeSystem = None
    unified_game_mechanics = None
    unified_points_db = None


class DecisionTreesSystem:
    """
    Decision Trees System
    - Build decision trees from tech knowledge
    - Build decision trees from progress knowledge
    - Decision-making assistance based on user state
    - Knowledge integration
    """
    
    def __init__(self):
        self.decision_trees = {}  # {tree_id: tree_data}
        self.user_decisions = defaultdict(list)  # {user_id: [decision_data]}
        self.knowledge_base = defaultdict(dict)  # {user_id: knowledge_data}
    
    def build_tech_decision_tree(self, user_id: str) -> Dict[str, Any]:
        """Build decision tree from tech tree knowledge"""
        tree_id = f"tech_tree_{user_id}"
        
        # Get tech tree data
        tech_data = {}
        if TechTreeSystem:
            try:
                tech_tree_system = TechTreeSystem()
                tech_result = tech_tree_system.get_tech_tree(user_id)
                tech_data = tech_result.get('tech_tree', [])
            except Exception as e:
                print(f"[DecisionTrees] Error getting tech tree: {e}")
        
        # Build decision tree structure
        tree = {
            'tree_id': tree_id,
            'user_id': user_id,
            'tree_type': 'tech',
            'root_node': {
                'node_id': 'root',
                'question': 'What technology do you want to research?',
                'children': []
            },
            'nodes': {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Build nodes from tech tree
        for tech in tech_data:
            node_id = f"tech_{tech.get('id', 'unknown')}"
            node = {
                'node_id': node_id,
                'tech_id': tech.get('id'),
                'tech_name': tech.get('name'),
                'question': f"Research {tech.get('name')}?",
                'prerequisites': tech.get('prerequisites', []),
                'unlocked': tech.get('unlocked', False),
                'researched': tech.get('researched', False),
                'recommendation': self._get_tech_recommendation(tech),
                'children': []
            }
            
            tree['nodes'][node_id] = node
            
            # Add to root children if unlocked
            if tech.get('unlocked', False):
                tree['root_node']['children'].append(node_id)
        
        self.decision_trees[tree_id] = tree
        
        return {
            'success': True,
            'tree_id': tree_id,
            'tree': tree,
            'total_nodes': len(tree['nodes'])
        }
    
    def build_progress_decision_tree(self, user_id: str) -> Dict[str, Any]:
        """Build decision tree from progress knowledge"""
        tree_id = f"progress_tree_{user_id}"
        
        # Get progress data
        progress_data = {}
        if unified_game_mechanics:
            try:
                progress_result = unified_game_mechanics.get_user_progress(user_id)
                progress_data = progress_result
            except Exception as e:
                print(f"[DecisionTrees] Error getting progress: {e}")
        
        # Build decision tree
        tree = {
            'tree_id': tree_id,
            'user_id': user_id,
            'tree_type': 'progress',
            'root_node': {
                'node_id': 'root',
                'question': 'What should you focus on next?',
                'children': []
            },
            'nodes': {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add progress-based recommendations
        recommendations = self._get_progress_recommendations(progress_data)
        
        for i, rec in enumerate(recommendations):
            node_id = f"progress_rec_{i}"
            node = {
                'node_id': node_id,
                'recommendation_type': rec.get('type'),
                'question': rec.get('question'),
                'recommendation': rec.get('recommendation'),
                'priority': rec.get('priority', 'medium'),
                'action': rec.get('action'),
                'children': []
            }
            
            tree['nodes'][node_id] = node
            tree['root_node']['children'].append(node_id)
        
        self.decision_trees[tree_id] = tree
        
        return {
            'success': True,
            'tree_id': tree_id,
            'tree': tree,
            'total_recommendations': len(recommendations)
        }
    
    def get_decision_recommendation(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get decision recommendation based on context"""
        # Build or get decision trees
        tech_tree_id = f"tech_tree_{user_id}"
        progress_tree_id = f"progress_tree_{user_id}"
        
        if tech_tree_id not in self.decision_trees:
            self.build_tech_decision_tree(user_id)
        if progress_tree_id not in self.decision_trees:
            self.build_progress_decision_tree(user_id)
        
        # Analyze context
        context_type = context.get('type', 'general')
        
        recommendations = []
        
        if context_type == 'tech_research':
            tech_tree = self.decision_trees.get(tech_tree_id, {})
            recommendations = self._get_tech_recommendations_from_tree(tech_tree, context)
        elif context_type == 'progress':
            progress_tree = self.decision_trees.get(progress_tree_id, {})
            recommendations = self._get_progress_recommendations_from_tree(progress_tree, context)
        else:
            # General recommendations
            tech_tree = self.decision_trees.get(tech_tree_id, {})
            progress_tree = self.decision_trees.get(progress_tree_id, {})
            recommendations = self._get_general_recommendations(tech_tree, progress_tree, context)
        
        return {
            'success': True,
            'user_id': user_id,
            'context': context,
            'recommendations': recommendations,
            'best_recommendation': recommendations[0] if recommendations else None
        }
    
    def _get_tech_recommendation(self, tech: Dict[str, Any]) -> str:
        """Get recommendation for tech research"""
        if tech.get('researched', False):
            return 'Already researched'
        if not tech.get('unlocked', False):
            return 'Prerequisites not met'
        return 'Ready to research'
    
    def _get_progress_recommendations(self, progress_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get progress-based recommendations"""
        recommendations = []
        
        completed_count = progress_data.get('subjects_completed', 0)
        if completed_count < 5:
            recommendations.append({
                'type': 'subject_completion',
                'question': 'Complete more subjects?',
                'recommendation': 'Focus on completing subjects to unlock more content',
                'priority': 'high',
                'action': 'complete_subjects'
            })
        
        return recommendations
    
    def _get_tech_recommendations_from_tree(self, tree: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get tech recommendations from decision tree"""
        recommendations = []
        nodes = tree.get('nodes', {})
        
        for node_id, node in nodes.items():
            if node.get('unlocked') and not node.get('researched'):
                recommendations.append({
                    'type': 'tech_research',
                    'tech_id': node.get('tech_id'),
                    'tech_name': node.get('tech_name'),
                    'recommendation': node.get('recommendation'),
                    'priority': 'high' if node.get('prerequisites') == [] else 'medium'
                })
        
        return sorted(recommendations, key=lambda x: 0 if x['priority'] == 'high' else 1)
    
    def _get_progress_recommendations_from_tree(self, tree: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get progress recommendations from decision tree"""
        recommendations = []
        nodes = tree.get('nodes', {})
        
        for node_id, node in nodes.items():
            recommendations.append({
                'type': node.get('recommendation_type'),
                'recommendation': node.get('recommendation'),
                'priority': node.get('priority', 'medium'),
                'action': node.get('action')
            })
        
        return sorted(recommendations, key=lambda x: 0 if x['priority'] == 'high' else 1)
    
    def _get_general_recommendations(self, tech_tree: Dict[str, Any], progress_tree: Dict[str, Any], 
                                    context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get general recommendations combining tech and progress"""
        recommendations = []
        
        # Add tech recommendations
        tech_recs = self._get_tech_recommendations_from_tree(tech_tree, context)
        recommendations.extend(tech_recs[:3])  # Top 3 tech recommendations
        
        # Add progress recommendations
        progress_recs = self._get_progress_recommendations_from_tree(progress_tree, context)
        recommendations.extend(progress_recs[:3])  # Top 3 progress recommendations
        
        return recommendations[:5]  # Return top 5 overall


# Global instance
decision_trees_system = DecisionTreesSystem()

