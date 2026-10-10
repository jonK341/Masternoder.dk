"""
Generator Progress Enhancer
Enhances video generation progress with Fear Twister, future tech, and calculator integration
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

# Fear Twister Import
try:
    from backend.services.fear_twister_scene_leveler import fear_twister_scene_leveler
    FEAR_TWISTER_AVAILABLE = True
except ImportError:
    fear_twister_scene_leveler = None
    FEAR_TWISTER_AVAILABLE = False

# Future Tech Import
try:
    from backend.services.future_tech_integration_service import future_tech_integration_service
    FUTURE_TECH_AVAILABLE = True
except ImportError:
    future_tech_integration_service = None
    FUTURE_TECH_AVAILABLE = False

# Calculator Import
try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    CALCULATOR_AVAILABLE = True
except ImportError:
    advanced_intelligent_calculator = None
    CALCULATOR_AVAILABLE = False


class GeneratorProgressEnhancer:
    """
    Enhances video generation progress with:
    - Fear Twister for scary scene leveling
    - Future tech integration
    - Calculator for progress calculations
    """
    
    def __init__(self):
        self.generation_progress = {}  # {doc_id: progress_data}
        self.scene_tracking = {}  # {doc_id: [scene_ids]}
    
    def enhance_progress_callback(self, doc_id: str, base_progress: int, 
                                  message: str, message_key: str = None,
                                  context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhance progress callback with Fear Twister and other enhancements
        
        Args:
            doc_id: Documentary ID
            base_progress: Base progress percentage (0-100)
            message: Progress message
            message_key: Progress stage key
            context: Additional context (scene_data, fear_level, etc.)
        """
        enhanced_progress = base_progress
        enhancements = {}
        
        # Apply Fear Twister if applicable (scary scenes)
        if FEAR_TWISTER_AVAILABLE and context:
            fear_level = context.get('fear_level', 0.0)
            scene_id = context.get('scene_id')
            
            if fear_level > 0 and scene_id:
                try:
                    # Initialize or update scary scene
                    if scene_id not in self.scene_tracking.get(doc_id, []):
                        fear_twister_scene_leveler.initialize_scary_scene(
                            scene_id, doc_id, fear_level
                        )
                        if doc_id not in self.scene_tracking:
                            self.scene_tracking[doc_id] = []
                        self.scene_tracking[doc_id].append(scene_id)
                    
                    # Update scene progress with Fear Twister
                    result = fear_twister_scene_leveler.update_scene_progress(
                        scene_id, message_key or 'clip_generation', base_progress, context
                    )
                    
                    if result.get('success'):
                        enhanced_progress = result.get('adjusted_progress', base_progress)
                        enhancements['fear_twister'] = {
                            'enabled': True,
                            'base_progress': base_progress,
                            'adjusted_progress': enhanced_progress,
                            'multiplier': result.get('multiplier', 1.0),
                            'efficiency_boost': result.get('efficiency_boost', 1.0),
                            'progress_gain': result.get('progress_gain', 0)
                        }
                except Exception as e:
                    print(f"[GeneratorProgressEnhancer] Error applying Fear Twister: {e}")
        
        # Store progress data
        progress_data = {
            'doc_id': doc_id,
            'base_progress': base_progress,
            'enhanced_progress': enhanced_progress,
            'message': message,
            'message_key': message_key,
            'enhancements': enhancements,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        self.generation_progress[doc_id] = progress_data
        
        return {
            'progress': int(min(100, enhanced_progress)),
            'base_progress': base_progress,
            'enhanced_progress': enhanced_progress,
            'message': message,
            'message_key': message_key,
            'enhancements': enhancements,
            'fear_twister_active': FEAR_TWISTER_AVAILABLE and bool(enhancements.get('fear_twister')),
            'future_tech_active': FUTURE_TECH_AVAILABLE,
            'calculator_active': CALCULATOR_AVAILABLE
        }
    
    def calculate_enhanced_progress(self, doc_id: str, stage: str, 
                                   substage_progress: float = 0.0,
                                   current_item: int = 0, total_items: int = 1,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calculate enhanced progress using calculator and progress stage manager
        
        Args:
            doc_id: Documentary ID
            stage: Current stage key
            substage_progress: Progress within stage (0.0-1.0)
            current_item: Current item number
            total_items: Total items
            context: Additional context
        """
        try:
            from src.utils.progress_stages import ProgressStageManager
            base_progress = ProgressStageManager.calculate_progress(
                stage, substage_progress, current_item, total_items
            )
        except Exception as e:
            print(f"[GeneratorProgressEnhancer] Error calculating base progress: {e}")
            base_progress = 0
        
        # Enhance with Fear Twister if applicable
        if context and context.get('fear_level', 0) > 0:
            enhanced = self.enhance_progress_callback(
                doc_id, base_progress, f"Processing {stage}...", stage, context
            )
            return enhanced
        
        return {
            'progress': base_progress,
            'base_progress': base_progress,
            'enhanced_progress': base_progress,
            'message': f"Processing {stage}...",
            'message_key': stage,
            'enhancements': {},
            'fear_twister_active': False,
            'future_tech_active': FUTURE_TECH_AVAILABLE,
            'calculator_active': CALCULATOR_AVAILABLE
        }
    
    def optimize_generation_scenes(self, doc_id: str, 
                                   scene_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize multiple scenes in a generation using Fear Twister
        
        Args:
            doc_id: Documentary ID
            scene_configs: List of scene configurations with fear_level, base_progress, etc.
        """
        if not FEAR_TWISTER_AVAILABLE:
            return {
                'success': False,
                'error': 'Fear Twister not available'
            }
        
        try:
            result = fear_twister_scene_leveler.batch_optimize_scenes(
                doc_id, scene_configs
            )
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_enhanced_progress(self, doc_id: str) -> Dict[str, Any]:
        """Get enhanced progress data for a generation"""
        progress_data = self.generation_progress.get(doc_id, {})
        
        if not progress_data:
            return {
                'success': False,
                'error': 'Generation progress not found'
            }
        
        # Add future tech enhancements if available
        if FUTURE_TECH_AVAILABLE:
            try:
                # Could add future tech projections here
                progress_data['future_tech_available'] = True
            except Exception as e:
                print(f"[GeneratorProgressEnhancer] Error adding future tech: {e}")
        
        return {
            'success': True,
            'progress_data': progress_data
        }
    
    def apply_calculator_to_progress(self, doc_id: str, point_data: Dict[str, Any],
                                    user_id: str) -> Dict[str, Any]:
        """
        Apply calculator to enhance progress calculations
        
        Args:
            doc_id: Documentary ID
            point_data: Point data for calculation
            user_id: User ID
        """
        if not CALCULATOR_AVAILABLE:
            return {
                'success': False,
                'error': 'Calculator not available'
            }
        
        try:
            calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                point_data, user_id
            )
            
            # Extract progress-related multipliers
            multipliers = calc_result.get('intelligent_multipliers', {})
            final_calc = calc_result.get('final_calculation', {})
            
            return {
                'success': True,
                'calculation_id': calc_result.get('calculation_id'),
                'multipliers': multipliers,
                'final_calculation': final_calc,
                'confidence': calc_result.get('confidence_score', 0)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
generator_progress_enhancer = GeneratorProgressEnhancer()

