"""
Matrix Generation System
Bridges and overlaps generation through a matrix system that benefits needs optimally
"""
import random
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class MatrixNode:
    """Represents a node in the generation matrix"""
    id: str
    type: str  # 'clip', 'transition', 'effect', 'audio'
    weight: float  # Importance weight (0-1)
    dependencies: List[str]  # IDs of dependent nodes
    metadata: Dict[str, Any]
    quality_score: float = 0.5  # Quality estimate (0-1)
    performance_score: float = 0.5  # Performance estimate (0-1)


class GenerationMatrix:
    """
    Matrix system for optimal generation bridging and overlap
    Creates intelligent connections between generation elements
    Learns and improves over time based on successful generations
    """
    
    def __init__(self):
        self.nodes = {}  # {node_id: MatrixNode}
        self.connections = {}  # {node_id: [connected_node_ids]}
        self.optimization_weights = {
            'quality': 0.4,
            'speed': 0.3,
            'creativity': 0.2,
            'coherence': 0.1
        }
        # Knowledge accumulation system
        self.knowledge_base = {
            'successful_patterns': [],  # Patterns that led to successful generations
            'failed_patterns': [],  # Patterns that failed
            'quality_improvements': {},  # {node_id: quality_score_history}
            'performance_metrics': {},  # {node_id: {avg_time, success_rate}}
            'user_preferences': {},  # Learned user preferences
            'generation_history': []  # History of all generations
        }
        self.learning_rate = 0.1  # How fast the matrix learns from new data
    
    def add_node(self, node: MatrixNode):
        """Add a node to the matrix"""
        self.nodes[node.id] = node
        if node.id not in self.connections:
            self.connections[node.id] = []
    
    def connect_nodes(self, node_id1: str, node_id2: str, bidirectional: bool = True):
        """Create connection between two nodes"""
        if node_id1 not in self.connections:
            self.connections[node_id1] = []
        if node_id2 not in self.connections:
            self.connections[node_id2] = []
        
        if node_id2 not in self.connections[node_id1]:
            self.connections[node_id1].append(node_id2)
        
        if bidirectional and node_id1 not in self.connections[node_id2]:
            self.connections[node_id2].append(node_id1)
    
    def find_optimal_path(self, start_node_id: str, target_duration: float, 
                         user_profile: Dict[str, Any] = None) -> List[str]:
        """
        Find optimal path through matrix to reach target duration
        
        Args:
            start_node_id: Starting node ID
            target_duration: Target duration in seconds
            user_profile: User behavioral/psychological profile
        
        Returns:
            List of node IDs representing optimal path
        """
        if start_node_id not in self.nodes:
            return []
        
        path = [start_node_id]
        current_duration = self.nodes[start_node_id].metadata.get('duration', 0)
        
        # Adjust optimization weights based on user profile
        if user_profile:
            hints = user_profile.get('optimization_hints', {})
            priority = hints.get('optimization_priority', 'balanced')
            
            if priority == 'speed':
                self.optimization_weights = {'quality': 0.2, 'speed': 0.5, 'creativity': 0.2, 'coherence': 0.1}
            elif priority == 'quality':
                self.optimization_weights = {'quality': 0.6, 'speed': 0.1, 'creativity': 0.2, 'coherence': 0.1}
            elif priority == 'creativity':
                self.optimization_weights = {'quality': 0.2, 'speed': 0.2, 'creativity': 0.5, 'coherence': 0.1}
        
        # Greedy path finding with matrix optimization
        while current_duration < target_duration:
            current_node_id = path[-1]
            candidates = self._get_candidate_nodes(current_node_id, path, target_duration - current_duration)
            
            if not candidates:
                break
            
            # Score candidates using matrix system
            scored_candidates = []
            for candidate_id in candidates:
                score = self._score_node(candidate_id, current_duration, target_duration, user_profile)
                scored_candidates.append((candidate_id, score))
            
            # Select best candidate
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            best_candidate = scored_candidates[0][0]
            
            path.append(best_candidate)
            current_duration += self.nodes[best_candidate].metadata.get('duration', 0)
        
        return path
    
    def _get_candidate_nodes(self, current_node_id: str, existing_path: List[str], 
                            remaining_duration: float) -> List[str]:
        """Get candidate nodes for next step in path"""
        candidates = []
        
        # Get connected nodes
        connected = self.connections.get(current_node_id, [])
        
        # Filter candidates
        for node_id in connected:
            if node_id in existing_path:
                continue  # Avoid cycles
            
            node = self.nodes.get(node_id)
            if not node:
                continue
            
            node_duration = node.metadata.get('duration', 0)
            
            # Prefer nodes that fit remaining duration
            if node_duration <= remaining_duration * 1.5:  # Allow some flexibility
                candidates.append(node_id)
        
        # If no connected nodes, get any available nodes
        if not candidates:
            for node_id, node in self.nodes.items():
                if node_id not in existing_path:
                    node_duration = node.metadata.get('duration', 0)
                    if node_duration <= remaining_duration * 1.5:
                        candidates.append(node_id)
        
        return candidates
    
    def _score_node(self, node_id: str, current_duration: float, target_duration: float,
                   user_profile: Dict[str, Any] = None) -> float:
        """Score a node for inclusion in path"""
        node = self.nodes.get(node_id)
        if not node:
            return 0.0
        
        score = 0.0
        
        # Quality score
        score += node.quality_score * self.optimization_weights['quality']
        
        # Performance score
        score += node.performance_score * self.optimization_weights['speed']
        
        # Weight/importance
        score += node.weight * 0.2
        
        # Duration fit (prefer nodes that bring us closer to target)
        node_duration = node.metadata.get('duration', 0)
        remaining = target_duration - current_duration
        if remaining > 0:
            fit_score = 1.0 - abs(node_duration - remaining) / max(remaining, 1.0)
            fit_score = max(0, min(1, fit_score))
            score += fit_score * 0.1
        
        # User profile alignment
        if user_profile:
            hints = user_profile.get('optimization_hints', {})
            complexity = hints.get('complexity_level', 0.5)
            
            # Prefer nodes matching user's complexity preference
            node_complexity = node.metadata.get('complexity', 0.5)
            complexity_match = 1.0 - abs(node_complexity - complexity)
            score += complexity_match * 0.1
        
        return score
    
    def create_generation_plan(self, clips: List[Dict[str, Any]], target_duration: float,
                              user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create optimal generation plan using matrix system
        
        Args:
            clips: List of available/planned clips
            target_duration: Target duration in seconds
            user_profile: User profile for optimization
        
        Returns:
            Generation plan with optimal clip sequence and transitions
        """
        # Build matrix from clips
        self._build_matrix_from_clips(clips)
        
        # Find optimal path
        if not self.nodes:
            return {'clips': clips, 'transitions': [], 'score': 0.0}
        
        start_node = list(self.nodes.keys())[0]
        optimal_path = self.find_optimal_path(start_node, target_duration, user_profile)
        
        # Extract clips from path
        planned_clips = []
        for node_id in optimal_path:
            node = self.nodes.get(node_id)
            if node and node.type == 'clip':
                planned_clips.append(node.metadata)
        
        # Calculate plan score
        plan_score = self._calculate_plan_score(optimal_path, target_duration)
        
        return {
            'clips': planned_clips,
            'path': optimal_path,
            'transitions': self._generate_transitions(optimal_path),
            'score': plan_score,
            'estimated_duration': sum(c.get('duration', 0) for c in planned_clips),
            'target_duration': target_duration
        }
    
    def _build_matrix_from_clips(self, clips: List[Dict[str, Any]]):
        """Build matrix structure from clip list"""
        self.nodes = {}
        self.connections = {}
        
        for i, clip in enumerate(clips):
            node_id = f"clip_{i}"
            node = MatrixNode(
                id=node_id,
                type='clip',
                weight=clip.get('weight', 0.5),
                dependencies=[],
                metadata=clip,
                quality_score=clip.get('quality_score', 0.5),
                performance_score=clip.get('performance_score', 0.5)
            )
            self.add_node(node)
            
            # Connect to previous clip (for sequence)
            if i > 0:
                prev_node_id = f"clip_{i-1}"
                self.connect_nodes(prev_node_id, node_id, bidirectional=False)
    
    def _generate_transitions(self, path: List[str]) -> List[Dict[str, Any]]:
        """Generate transitions between clips in path"""
        transitions = []
        
        for i in range(len(path) - 1):
            from_node = self.nodes.get(path[i])
            to_node = self.nodes.get(path[i + 1])
            
            if from_node and to_node:
                transition = {
                    'from': from_node.id,
                    'to': to_node.id,
                    'type': 'fade',  # Default transition
                    'duration': 0.5
                }
                
                # Determine transition type based on node metadata
                from_emotion = from_node.metadata.get('emotion', 'neutral')
                to_emotion = to_node.metadata.get('emotion', 'neutral')
                
                if from_emotion != to_emotion:
                    transition['type'] = 'crossfade'
                    transition['duration'] = 1.0
                
                transitions.append(transition)
        
        return transitions
    
    def _calculate_plan_score(self, path: List[str], target_duration: float) -> float:
        """Calculate overall score for generation plan"""
        if not path:
            return 0.0
        
        total_quality = 0.0
        total_performance = 0.0
        total_duration = 0.0
        
        for node_id in path:
            node = self.nodes.get(node_id)
            if node:
                total_quality += node.quality_score
                total_performance += node.performance_score
                total_duration += node.metadata.get('duration', 0)
        
        avg_quality = total_quality / len(path)
        avg_performance = total_performance / len(path)
        
        # Duration fit score
        duration_fit = 1.0 - abs(total_duration - target_duration) / max(target_duration, 1.0)
        duration_fit = max(0, min(1, duration_fit))
        
        # Combined score
        score = (
            avg_quality * self.optimization_weights['quality'] +
            avg_performance * self.optimization_weights['speed'] +
            duration_fit * 0.2
        )
        
        return score


# Global instance
generation_matrix = GenerationMatrix()

