"""
Path Corrector Service
Corrects paths on-demand across the system
"""
import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class PathCorrector:
    """Path correction system that fixes paths on-demand across the system"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.corrections_file = os.path.join(self.base_dir, 'logs', 'path_corrector', 'corrections.json')
        self.path_mappings_file = os.path.join(self.base_dir, 'logs', 'path_corrector', 'path_mappings.json')
        self.load_data()
    
    def load_data(self):
        """Load path correction data"""
        os.makedirs(os.path.dirname(self.corrections_file), exist_ok=True)
        
        if os.path.exists(self.corrections_file):
            try:
                with open(self.corrections_file, 'r') as f:
                    self.corrections = json.load(f)
            except:
                self.corrections = self._default_corrections()
        else:
            self.corrections = self._default_corrections()
        
        if os.path.exists(self.path_mappings_file):
            try:
                with open(self.path_mappings_file, 'r') as f:
                    self.path_mappings = json.load(f)
            except:
                self.path_mappings = {}
        else:
            self.path_mappings = {}
        
        self.save_data()
    
    def _default_corrections(self) -> Dict:
        """Default corrections structure"""
        return {
            'corrections': [],
            'patterns': {},
            'statistics': {
                'total_corrections': 0,
                'successful_corrections': 0,
                'failed_corrections': 0
            },
            'last_updated': datetime.now().isoformat()
        }
    
    def save_data(self):
        """Save path correction data. Skips save on RecursionError to avoid blocking."""
        try:
            self.corrections['last_updated'] = datetime.now().isoformat()
            with open(self.corrections_file, 'w') as f:
                json.dump(self.corrections, f, indent=2, default=str)
            with open(self.path_mappings_file, 'w') as f:
                json.dump(self.path_mappings, f, indent=2, default=str)
        except RecursionError:
            pass
        except Exception as e:
            if "recursion" in str(e).lower():
                pass
            else:
                print(f"Error saving path correction data: {e}")
    
    def correct_path(self, path: str, context: Optional[Dict] = None) -> Tuple[str, Dict]:
        """Correct a path on-demand with AI enhancement"""
        original_path = path
        context = context or {}
        
        # Try AI-enhanced correction first
        try:
            from backend.services.ai_enhanced_paths import ai_enhanced_paths
            corrected_path, correction_info = ai_enhanced_paths.intelligent_path_correction(path, context)
            return corrected_path, correction_info
        except RecursionError:
            # AI path correction can recurse via agent_ai_intelligence; fall back silently
            pass
        except Exception as e:
            if "recursion" in str(e).lower():
                pass
            else:
                print(f"Error in AI path correction, falling back to standard: {e}")
        
        # Check if we have a mapping for this path
        if path in self.path_mappings:
            corrected_path = self.path_mappings[path]['correct_path']
            confidence = self.path_mappings[path].get('confidence', 1.0)
            
            correction_info = {
                'original': original_path,
                'corrected': corrected_path,
                'method': 'mapping',
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            }
            
            self._record_correction(correction_info, success=True)
            return corrected_path, correction_info
        
        # Try pattern-based correction
        corrected_path, pattern_info = self._correct_by_pattern(path, context)
        
        if corrected_path != path:
            correction_info = {
                'original': original_path,
                'corrected': corrected_path,
                'method': 'pattern',
                'pattern': pattern_info.get('pattern'),
                'confidence': pattern_info.get('confidence', 0.7),
                'timestamp': datetime.now().isoformat()
            }
            
            # Store mapping for future use
            self.path_mappings[original_path] = {
                'correct_path': corrected_path,
                'confidence': pattern_info.get('confidence', 0.7),
                'method': 'pattern',
                'created_at': datetime.now().isoformat()
            }
            
            self._record_correction(correction_info, success=True)
            return corrected_path, correction_info
        
        # No correction needed
        return path, {
            'original': original_path,
            'corrected': original_path,
            'method': 'none',
            'confidence': 1.0,
            'timestamp': datetime.now().isoformat()
        }
    
    def _correct_by_pattern(self, path: str, context: Dict) -> Tuple[str, Dict]:
        """Correct path using patterns"""
        # Common path correction patterns
        patterns = [
            # API path corrections
            {
                'pattern': r'/api/([^/]+)/([^/]+)',
                'corrections': {
                    r'/api/user/(\w+)': r'/api/users/\1',
                    r'/api/agent/(\w+)': r'/api/agents/\1',
                    r'/api/task/(\w+)': r'/api/tasks/\1'
                }
            },
            # Vidgenerator path corrections
            {
                'pattern': r'/vidgenerator/([^/]+)',
                'corrections': {
                    r'/vidgenerator/debugger/(\w+)': r'/vidgenerator/debugger/\1',
                    r'/vidgenerator/game/(\w+)': r'/vidgenerator/game/\1'
                }
            },
            # Static file path corrections
            {
                'pattern': r'/static/([^/]+)/([^/]+)',
                'corrections': {
                    r'/static/js/(\w+)\.js': r'/vidgenerator/static/js/\1.js',
                    r'/static/css/(\w+)\.css': r'/vidgenerator/static/css/\1.css'
                }
            },
            # Backend path corrections
            {
                'pattern': r'/backend/([^/]+)',
                'corrections': {
                    r'/backend/routes/(\w+)': r'/api/\1',
                    r'/backend/services/(\w+)': r'/api/services/\1'
                }
            }
        ]
        
        for pattern_group in patterns:
            for pattern, replacement in pattern_group.get('corrections', {}).items():
                if re.match(pattern, path):
                    corrected = re.sub(pattern, replacement, path)
                    if corrected != path:
                        return corrected, {
                            'pattern': pattern,
                            'confidence': 0.8
                        }
        
        # Context-based corrections
        if context:
            # Check if context suggests a correction
            if 'expected_type' in context:
                expected_type = context['expected_type']
                if expected_type == 'api' and not path.startswith('/api/'):
                    corrected = path
                    if path.startswith('/vidgenerator/api/'):
                        corrected = path.replace('/vidgenerator/api/', '/api/')
                    elif path.startswith('/vidgenerator/'):
                        corrected = path.replace('/vidgenerator/', '/api/')
                    if corrected != path:
                        return corrected, {
                            'pattern': 'context_api',
                            'confidence': 0.7
                        }
        
        return path, {'pattern': None, 'confidence': 0.0}
    
    def _record_correction(self, correction_info: Dict, success: bool):
        """Record a path correction"""
        if 'corrections' not in self.corrections:
            self.corrections['corrections'] = []
        
        correction_info['success'] = success
        self.corrections['corrections'].append(correction_info)
        
        # Update statistics
        stats = self.corrections['statistics']
        stats['total_corrections'] += 1
        if success:
            stats['successful_corrections'] += 1
        else:
            stats['failed_corrections'] += 1
        
        # Keep only last 1000 corrections
        if len(self.corrections['corrections']) > 1000:
            self.corrections['corrections'] = self.corrections['corrections'][-1000:]
        
        self.save_data()
    
    def learn_correction(self, original_path: str, corrected_path: str, 
                        context: Optional[Dict] = None, success: bool = True):
        """Learn a path correction with AI enhancement"""
        # Use AI-enhanced learning
        try:
            from backend.services.ai_enhanced_paths import ai_enhanced_paths
            ai_enhanced_paths.intelligent_path_learning(original_path, corrected_path, success, context)
        except RecursionError:
            pass
        except Exception as e:
            if "recursion" in str(e).lower():
                pass
            else:
                print(f"Error in AI path learning: {e}")
        
        if original_path not in self.path_mappings:
            self.path_mappings[original_path] = {
                'correct_path': corrected_path,
                'confidence': 1.0 if success else 0.5,
                'method': 'learned',
                'context': context or {},
                'created_at': datetime.now().isoformat(),
                'success_count': 1 if success else 0,
                'failure_count': 0 if success else 1
            }
        else:
            # Update existing mapping
            mapping = self.path_mappings[original_path]
            if success:
                mapping['success_count'] = mapping.get('success_count', 0) + 1
                # Increase confidence with successful uses
                mapping['confidence'] = min(1.0, mapping.get('confidence', 0.5) + 0.1)
            else:
                mapping['failure_count'] = mapping.get('failure_count', 0) + 1
                # Decrease confidence with failures
                mapping['confidence'] = max(0.0, mapping.get('confidence', 0.5) - 0.1)
            
            mapping['last_used'] = datetime.now().isoformat()
        
        self.save_data()
    
    def correct_paths_crossways(self, paths: List[str], context: Optional[Dict] = None) -> List[Tuple[str, str, Dict]]:
        """Correct multiple paths across the system"""
        corrected_paths = []
        
        for path in paths:
            corrected, info = self.correct_path(path, context)
            corrected_paths.append((path, corrected, info))
        
        return corrected_paths
    
    def get_correction_statistics(self) -> Dict:
        """Get path correction statistics"""
        return {
            'total_corrections': self.corrections['statistics'].get('total_corrections', 0),
            'successful_corrections': self.corrections['statistics'].get('successful_corrections', 0),
            'failed_corrections': self.corrections['statistics'].get('failed_corrections', 0),
            'mappings_count': len(self.path_mappings),
            'success_rate': (
                self.corrections['statistics'].get('successful_corrections', 0) /
                max(1, self.corrections['statistics'].get('total_corrections', 1))
            ) * 100
        }


# Global instance
path_corrector = PathCorrector()
