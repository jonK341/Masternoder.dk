"""
Fear Twister - Efficient Scary Scene Leveling System
Levels scary scenes more efficiently on progress counter
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random
import math

try:
    from backend.services.unified_point_counter import unified_point_counter
    from src.utils.progress_stages import ProgressStage, ProgressStageManager
except ImportError:
    unified_point_counter = None
    ProgressStage = None
    ProgressStageManager = None


class FearTwisterSceneLeveler:
    """
    Fear Twister - Efficiently levels scary scenes in video generation
    """
    
    def __init__(self):
        self.scene_processing = {}  # {scene_id: processing_data}
        self.fear_levels = {}  # {scene_id: fear_level}
        self.progress_optimizations = {}  # {generation_id: optimization_data}
        self.fear_multipliers = defaultdict(float)  # {scene_id: multiplier}
        self.efficiency_stats = defaultdict(dict)  # {user_id: stats}
    
    def initialize_scary_scene(self, scene_id: str, generation_id: str, 
                              base_fear_level: float = 0.5) -> Dict[str, Any]:
        """
        Initialize a scary scene with fear leveling
        
        Args:
            scene_id: Scene identifier
            generation_id: Video generation identifier
            base_fear_level: Base fear level (0.0-1.0)
        """
        fear_level = min(1.0, max(0.0, base_fear_level))
        
        scene_data = {
            'scene_id': scene_id,
            'generation_id': generation_id,
            'base_fear_level': fear_level,
            'current_fear_level': fear_level,
            'target_fear_level': fear_level,
            'progress_multiplier': self._calculate_progress_multiplier(fear_level),
            'efficiency_boost': self._calculate_efficiency_boost(fear_level),
            'created_at': datetime.utcnow().isoformat(),
            'processing_stages': [],
            'completed': False
        }
        
        self.scene_processing[scene_id] = scene_data
        self.fear_levels[scene_id] = fear_level
        
        return {
            'success': True,
            'scene': scene_data,
            'message': f'Scary scene initialized with fear level {fear_level:.2f}'
        }
    
    def _calculate_progress_multiplier(self, fear_level: float) -> float:
        """Calculate progress multiplier based on fear level"""
        # Higher fear = more efficient progress (exponential curve)
        # Formula: 1.0 + (fear_level^2 * 1.5)
        # Fear 0.0 = 1.0x, Fear 0.5 = 1.375x, Fear 1.0 = 2.5x
        base_multiplier = 1.0
        fear_boost = (fear_level ** 2) * 1.5
        return base_multiplier + fear_boost
    
    def _calculate_efficiency_boost(self, fear_level: float) -> float:
        """Calculate efficiency boost for processing"""
        # Efficiency increases with fear level
        # Formula: 1.0 + (fear_level * 0.8)
        # Fear 0.0 = 1.0x, Fear 0.5 = 1.4x, Fear 1.0 = 1.8x
        return 1.0 + (fear_level * 0.8)
    
    def update_scene_progress(self, scene_id: str, stage: str, 
                             base_progress: float, context: Dict = None) -> Dict[str, Any]:
        """
        Update scene progress with fear twister efficiency
        
        Args:
            scene_id: Scene identifier
            stage: Current processing stage
            base_progress: Base progress value (0-100)
            context: Additional context
        """
        if scene_id not in self.scene_processing:
            return {
                'success': False,
                'error': 'Scene not initialized',
                'adjusted_progress': base_progress
            }
        
        scene = self.scene_processing[scene_id]
        fear_level = scene['current_fear_level']
        
        # Calculate adjusted progress with fear multiplier
        multiplier = scene['progress_multiplier']
        adjusted_progress = min(100.0, base_progress * multiplier)
        
        # Calculate efficiency gain
        efficiency_boost = scene['efficiency_boost']
        time_saved = (adjusted_progress - base_progress) / efficiency_boost
        
        # Track processing stage
        stage_data = {
            'stage': stage,
            'base_progress': base_progress,
            'adjusted_progress': adjusted_progress,
            'multiplier': multiplier,
            'efficiency_boost': efficiency_boost,
            'timestamp': datetime.utcnow().isoformat(),
            'fear_level': fear_level
        }
        scene['processing_stages'].append(stage_data)
        
        # Update scene
        scene['last_stage'] = stage
        scene['last_progress'] = adjusted_progress
        scene['last_updated'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'scene_id': scene_id,
            'base_progress': base_progress,
            'adjusted_progress': adjusted_progress,
            'multiplier': multiplier,
            'efficiency_boost': efficiency_boost,
            'progress_gain': adjusted_progress - base_progress,
            'time_saved_estimate': time_saved,
            'stage_data': stage_data
        }
    
    def twist_fear_level(self, scene_id: str, new_fear_level: float = None,
                        twist_type: str = 'increase') -> Dict[str, Any]:
        """
        Twist/adjust fear level for more efficient leveling
        
        Args:
            scene_id: Scene identifier
            new_fear_level: New fear level (0.0-1.0), if None uses twist_type
            twist_type: 'increase', 'decrease', 'maximize', 'minimize'
        """
        if scene_id not in self.scene_processing:
            return {'success': False, 'error': 'Scene not initialized'}
        
        scene = self.scene_processing[scene_id]
        current_fear = scene['current_fear_level']
        
        # Calculate new fear level
        if new_fear_level is not None:
            target_fear = min(1.0, max(0.0, new_fear_level))
        elif twist_type == 'increase':
            target_fear = min(1.0, current_fear + 0.2)
        elif twist_type == 'decrease':
            target_fear = max(0.0, current_fear - 0.2)
        elif twist_type == 'maximize':
            target_fear = 1.0
        elif twist_type == 'minimize':
            target_fear = 0.0
        else:
            target_fear = current_fear
        
        # Update fear level
        scene['current_fear_level'] = target_fear
        scene['target_fear_level'] = target_fear
        scene['progress_multiplier'] = self._calculate_progress_multiplier(target_fear)
        scene['efficiency_boost'] = self._calculate_efficiency_boost(target_fear)
        scene['fear_twisted_at'] = datetime.utcnow().isoformat()
        scene['fear_change'] = target_fear - current_fear
        
        self.fear_levels[scene_id] = target_fear
        
        return {
            'success': True,
            'scene_id': scene_id,
            'previous_fear_level': current_fear,
            'new_fear_level': target_fear,
            'fear_change': target_fear - current_fear,
            'new_multiplier': scene['progress_multiplier'],
            'new_efficiency': scene['efficiency_boost'],
            'multiplier_gain': scene['progress_multiplier'] - self._calculate_progress_multiplier(current_fear)
        }
    
    def optimize_generation_progress(self, generation_id: str, 
                                    scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize progress counter for entire generation with scary scenes
        
        Args:
            generation_id: Video generation identifier
            scenes: List of scene data with fear levels
        """
        total_base_progress = sum(s.get('base_progress', 0) for s in scenes)
        total_adjusted_progress = 0.0
        scene_optimizations = []
        
        for scene_data in scenes:
            scene_id = scene_data.get('scene_id', f"scene_{len(scene_optimizations)}")
            fear_level = scene_data.get('fear_level', 0.5)
            base_progress = scene_data.get('base_progress', 0)
            
            # Initialize scene if not already
            if scene_id not in self.scene_processing:
                self.initialize_scary_scene(scene_id, generation_id, fear_level)
            
            scene = self.scene_processing[scene_id]
            multiplier = scene['progress_multiplier']
            adjusted_progress = base_progress * multiplier
            
            scene_optimizations.append({
                'scene_id': scene_id,
                'base_progress': base_progress,
                'adjusted_progress': adjusted_progress,
                'multiplier': multiplier,
                'fear_level': fear_level,
                'gain': adjusted_progress - base_progress
            })
            
            total_adjusted_progress += adjusted_progress
        
        total_gain = total_adjusted_progress - total_base_progress
        efficiency_improvement = (total_gain / total_base_progress * 100) if total_base_progress > 0 else 0
        
        optimization_data = {
            'generation_id': generation_id,
            'total_base_progress': total_base_progress,
            'total_adjusted_progress': total_adjusted_progress,
            'total_gain': total_gain,
            'efficiency_improvement_percent': efficiency_improvement,
            'scene_optimizations': scene_optimizations,
            'optimized_at': datetime.utcnow().isoformat()
        }
        
        self.progress_optimizations[generation_id] = optimization_data
        
        return {
            'success': True,
            'optimization': optimization_data,
            'message': f'Progress optimized: {efficiency_improvement:.1f}% improvement'
        }
    
    def get_scene_progress(self, scene_id: str) -> Dict[str, Any]:
        """Get current progress data for a scene"""
        if scene_id not in self.scene_processing:
            return {'success': False, 'error': 'Scene not found'}
        
        scene = self.scene_processing[scene_id]
        
        return {
            'success': True,
            'scene': scene,
            'current_progress': scene.get('last_progress', 0.0),
            'fear_level': scene['current_fear_level'],
            'multiplier': scene['progress_multiplier'],
            'efficiency_boost': scene['efficiency_boost']
        }
    
    def get_generation_optimization(self, generation_id: str) -> Dict[str, Any]:
        """Get optimization data for a generation"""
        if generation_id not in self.progress_optimizations:
            return {'success': False, 'error': 'Generation not optimized'}
        
        return {
            'success': True,
            'optimization': self.progress_optimizations[generation_id]
        }
    
    def calculate_scary_scene_progress(self, base_progress: float, fear_level: float,
                                      scene_complexity: float = 1.0) -> Dict[str, Any]:
        """
        Calculate progress for scary scene with fear twister
        
        Args:
            base_progress: Base progress value
            fear_level: Fear level (0.0-1.0)
            scene_complexity: Scene complexity factor (1.0 = normal)
        """
        # Calculate multiplier
        multiplier = self._calculate_progress_multiplier(fear_level)
        
        # Adjust for complexity (complex scenes get less boost to balance)
        complexity_adjustment = 1.0 / scene_complexity
        adjusted_multiplier = 1.0 + ((multiplier - 1.0) * complexity_adjustment)
        
        # Calculate final progress
        adjusted_progress = min(100.0, base_progress * adjusted_multiplier)
        progress_gain = adjusted_progress - base_progress
        
        return {
            'base_progress': base_progress,
            'fear_level': fear_level,
            'multiplier': multiplier,
            'adjusted_multiplier': adjusted_multiplier,
            'adjusted_progress': adjusted_progress,
            'progress_gain': progress_gain,
            'efficiency_percent': (progress_gain / base_progress * 100) if base_progress > 0 else 0
        }
    
    def batch_optimize_scenes(self, generation_id: str, 
                             scene_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Batch optimize multiple scary scenes
        
        Args:
            generation_id: Generation identifier
            scene_configs: List of {scene_id, fear_level, base_progress, ...}
        """
        optimized_scenes = []
        total_gain = 0.0
        
        for config in scene_configs:
            scene_id = config.get('scene_id')
            fear_level = config.get('fear_level', 0.5)
            base_progress = config.get('base_progress', 0)
            
            # Initialize if needed
            if scene_id and scene_id not in self.scene_processing:
                self.initialize_scary_scene(scene_id, generation_id, fear_level)
            
            # Calculate optimized progress
            if scene_id:
                progress_result = self.calculate_scary_scene_progress(
                    base_progress, fear_level, config.get('complexity', 1.0)
                )
                optimized_scenes.append({
                    'scene_id': scene_id,
                    **progress_result
                })
                total_gain += progress_result['progress_gain']
        
        return {
            'success': True,
            'generation_id': generation_id,
            'optimized_scenes': optimized_scenes,
            'total_gain': total_gain,
            'average_gain': total_gain / len(optimized_scenes) if optimized_scenes else 0,
            'optimized_at': datetime.utcnow().isoformat()
        }


# Global instance
fear_twister_scene_leveler = FearTwisterSceneLeveler()

