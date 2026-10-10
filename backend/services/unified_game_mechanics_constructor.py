"""
Unified Game Mechanics Constructor
Comprehensive system with 10+ subjects, academic classes (1a, 2a, 3a), and function types
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from collections import defaultdict
import uuid
import json
import os

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class UnifiedGameMechanicsConstructor:
    """
    Unified Game Mechanics Constructor
    - 10+ subjects divided by academic classes (1a, 2a, 3a)
    - Functions divided by types
    - Integrated with point system and tech tree
    """
    
    # 10+ Subjects organized by academic classes
    SUBJECTS = {
        '1a': {  # Foundation Level
            'mathematics': {
                'id': 'math_1a',
                'name': 'Mathematics 1a',
                'level': 1,
                'functions': ['basic_calculation', 'algebra_basics', 'geometry_intro'],
                'point_multiplier': 1.0,
                'unlocks': ['math_2a']
            },
            'science': {
                'id': 'science_1a',
                'name': 'Science 1a',
                'level': 1,
                'functions': ['observation', 'experiment_basics', 'hypothesis'],
                'point_multiplier': 1.0,
                'unlocks': ['science_2a']
            },
            'language': {
                'id': 'language_1a',
                'name': 'Language 1a',
                'level': 1,
                'functions': ['reading', 'writing_basics', 'vocabulary'],
                'point_multiplier': 1.0,
                'unlocks': ['language_2a']
            },
            'technology': {
                'id': 'technology_1a',
                'name': 'Technology 1a',
                'level': 1,
                'functions': ['basic_computing', 'digital_literacy', 'online_safety'],
                'point_multiplier': 1.0,
                'unlocks': ['technology_2a']
            },
            'arts': {
                'id': 'arts_1a',
                'name': 'Arts 1a',
                'level': 1,
                'functions': ['drawing', 'color_theory', 'creative_expression'],
                'point_multiplier': 1.0,
                'unlocks': ['arts_2a']
            }
        },
        '2a': {  # Intermediate Level
            'mathematics': {
                'id': 'math_2a',
                'name': 'Mathematics 2a',
                'level': 2,
                'functions': ['advanced_algebra', 'trigonometry', 'calculus_intro'],
                'point_multiplier': 1.5,
                'prerequisites': ['math_1a'],
                'unlocks': ['math_3a']
            },
            'science': {
                'id': 'science_2a',
                'name': 'Science 2a',
                'level': 2,
                'functions': ['advanced_experiments', 'scientific_method', 'data_analysis'],
                'point_multiplier': 1.5,
                'prerequisites': ['science_1a'],
                'unlocks': ['science_3a']
            },
            'language': {
                'id': 'language_2a',
                'name': 'Language 2a',
                'level': 2,
                'functions': ['advanced_writing', 'literature', 'communication'],
                'point_multiplier': 1.5,
                'prerequisites': ['language_1a'],
                'unlocks': ['language_3a']
            },
            'technology': {
                'id': 'technology_2a',
                'name': 'Technology 2a',
                'level': 2,
                'functions': ['programming', 'web_development', 'data_storage'],
                'point_multiplier': 1.5,
                'prerequisites': ['technology_1a'],
                'unlocks': ['technology_3a']
            },
            'arts': {
                'id': 'arts_2a',
                'name': 'Arts 2a',
                'level': 2,
                'functions': ['advanced_design', 'digital_arts', 'composition'],
                'point_multiplier': 1.5,
                'prerequisites': ['arts_1a'],
                'unlocks': ['arts_3a']
            },
            'social_studies': {
                'id': 'social_2a',
                'name': 'Social Studies 2a',
                'level': 2,
                'functions': ['history', 'geography', 'civics'],
                'point_multiplier': 1.5,
                'unlocks': ['social_3a']
            },
            'physical_education': {
                'id': 'pe_2a',
                'name': 'Physical Education 2a',
                'level': 2,
                'functions': ['fitness', 'sports', 'health'],
                'point_multiplier': 1.5,
                'unlocks': ['pe_3a']
            },
            'music': {
                'id': 'music_2a',
                'name': 'Music 2a',
                'level': 2,
                'functions': ['music_theory', 'performance', 'composition'],
                'point_multiplier': 1.5,
                'unlocks': ['music_3a']
            }
        },
        '3a': {  # Advanced Level
            'mathematics': {
                'id': 'math_3a',
                'name': 'Mathematics 3a',
                'level': 3,
                'functions': ['advanced_calculus', 'statistics', 'discrete_math'],
                'point_multiplier': 2.0,
                'prerequisites': ['math_2a']
            },
            'science': {
                'id': 'science_3a',
                'name': 'Science 3a',
                'level': 3,
                'functions': ['advanced_research', 'theoretical_physics', 'chemistry'],
                'point_multiplier': 2.0,
                'prerequisites': ['science_2a']
            },
            'language': {
                'id': 'language_3a',
                'name': 'Language 3a',
                'level': 3,
                'functions': ['advanced_literature', 'critical_analysis', 'creative_writing'],
                'point_multiplier': 2.0,
                'prerequisites': ['language_2a']
            },
            'technology': {
                'id': 'technology_3a',
                'name': 'Technology 3a',
                'level': 3,
                'functions': ['ai_development', 'machine_learning', 'advanced_programming'],
                'point_multiplier': 2.0,
                'prerequisites': ['technology_2a']
            },
            'arts': {
                'id': 'arts_3a',
                'name': 'Arts 3a',
                'level': 3,
                'functions': ['master_techniques', 'artistic_expression', 'portfolio'],
                'point_multiplier': 2.0,
                'prerequisites': ['arts_2a']
            },
            'social_studies': {
                'id': 'social_3a',
                'name': 'Social Studies 3a',
                'level': 3,
                'functions': ['advanced_history', 'political_science', 'economics'],
                'point_multiplier': 2.0,
                'prerequisites': ['social_2a']
            },
            'physical_education': {
                'id': 'pe_3a',
                'name': 'Physical Education 3a',
                'level': 3,
                'functions': ['advanced_fitness', 'sports_science', 'wellness'],
                'point_multiplier': 2.0,
                'prerequisites': ['pe_2a']
            },
            'music': {
                'id': 'music_3a',
                'name': 'Music 3a',
                'level': 3,
                'functions': ['advanced_composition', 'orchestration', 'music_production'],
                'point_multiplier': 2.0,
                'prerequisites': ['music_2a']
            },
            'philosophy': {
                'id': 'philosophy_3a',
                'name': 'Philosophy 3a',
                'level': 3,
                'functions': ['ethics', 'logic', 'metaphysics'],
                'point_multiplier': 2.0
            },
            'economics': {
                'id': 'economics_3a',
                'name': 'Economics 3a',
                'level': 3,
                'functions': ['microeconomics', 'macroeconomics', 'finance'],
                'point_multiplier': 2.0
            }
        }
    }
    
    # Function types
    FUNCTION_TYPES = {
        'calculation': {
            'name': 'Calculation Functions',
            'subjects': ['mathematics'],
            'point_value': 10
        },
        'experimental': {
            'name': 'Experimental Functions',
            'subjects': ['science'],
            'point_value': 15
        },
        'creative': {
            'name': 'Creative Functions',
            'subjects': ['language', 'arts', 'music'],
            'point_value': 12
        },
        'technical': {
            'name': 'Technical Functions',
            'subjects': ['technology'],
            'point_value': 20
        },
        'analytical': {
            'name': 'Analytical Functions',
            'subjects': ['mathematics', 'science', 'social_studies'],
            'point_value': 15
        },
        'practical': {
            'name': 'Practical Functions',
            'subjects': ['physical_education', 'technology'],
            'point_value': 10
        },
        'theoretical': {
            'name': 'Theoretical Functions',
            'subjects': ['philosophy', 'mathematics', 'science'],
            'point_value': 18
        }
    }
    
    def __init__(self):
        self.data_dir = 'data/game_mechanics'
        os.makedirs(self.data_dir, exist_ok=True)
        self.user_progress = defaultdict(dict)  # {user_id: {subject_id: progress_data}}
        self.function_usage = defaultdict(dict)  # {user_id: {function_type: usage_count}}
        
    def get_all_subjects(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all subjects organized by academic classes"""
        user_progress = self.user_progress.get(user_id, {}) if user_id else {}
        
        result = {
            '1a': [],
            '2a': [],
            '3a': []
        }
        
        for class_level, subjects in self.SUBJECTS.items():
            for subject_key, subject_data in subjects.items():
                subject_id = subject_data['id']
                progress = user_progress.get(subject_id, {})
                
                # Check prerequisites
                prerequisites_met = True
                if subject_data.get('prerequisites'):
                    for prereq in subject_data['prerequisites']:
                        if prereq not in user_progress or user_progress[prereq].get('completed', False) != True:
                            prerequisites_met = False
                            break
                
                result[class_level].append({
                    **subject_data,
                    'progress': progress.get('progress', 0),
                    'completed': progress.get('completed', False),
                    'unlocked': prerequisites_met or not subject_data.get('prerequisites'),
                    'functions_unlocked': progress.get('functions_unlocked', [])
                })
        
        return {
            'success': True,
            'subjects': result,
            'total_subjects': sum(len(subjects) for subjects in self.SUBJECTS.values())
        }
    
    def start_subject(self, user_id: str, subject_id: str) -> Dict[str, Any]:
        """Start learning a subject"""
        # Find subject
        subject_data = None
        for class_level, subjects in self.SUBJECTS.items():
            for subject_key, subj in subjects.items():
                if subj['id'] == subject_id:
                    subject_data = subj
                    break
            if subject_data:
                break
        
        if not subject_data:
            return {'success': False, 'error': 'Subject not found'}
        
        # Check prerequisites
        if subject_data.get('prerequisites'):
            user_progress = self.user_progress.get(user_id, {})
            for prereq in subject_data['prerequisites']:
                if prereq not in user_progress or not user_progress[prereq].get('completed', False):
                    return {
                        'success': False,
                        'error': f'Prerequisites not met: {prereq}',
                        'missing_prerequisites': [p for p in subject_data['prerequisites'] 
                                                  if p not in user_progress or not user_progress[p].get('completed', False)]
                    }
        
        # Start subject
        if subject_id not in self.user_progress[user_id]:
            self.user_progress[user_id][subject_id] = {
                'subject_id': subject_id,
                'started_at': datetime.utcnow().isoformat(),
                'progress': 0,
                'completed': False,
                'functions_unlocked': [],
                'functions_used': {}
            }
        
        return {
            'success': True,
            'subject_id': subject_id,
            'subject_name': subject_data['name'],
            'functions': subject_data['functions']
        }
    
    def use_function(self, user_id: str, subject_id: str, function_name: str, function_type: str) -> Dict[str, Any]:
        """Use a function from a subject"""
        if subject_id not in self.user_progress.get(user_id, {}):
            return {'success': False, 'error': 'Subject not started'}
        
        subject_data = None
        for class_level, subjects in self.SUBJECTS.items():
            for subject_key, subj in subjects.items():
                if subj['id'] == subject_id:
                    subject_data = subj
                    break
            if subject_data:
                break
        
        if not subject_data or function_name not in subject_data.get('functions', []):
            return {'success': False, 'error': 'Function not found in subject'}
        
        # Track function usage
        progress = self.user_progress[user_id][subject_id]
        if function_name not in progress['functions_unlocked']:
            progress['functions_unlocked'].append(function_name)
        
        if function_name not in progress['functions_used']:
            progress['functions_used'][function_name] = 0
        progress['functions_used'][function_name] += 1
        
        # Track by function type
        if function_type not in self.function_usage[user_id]:
            self.function_usage[user_id][function_type] = 0
        self.function_usage[user_id][function_type] += 1
        
        # Award points
        function_type_data = self.FUNCTION_TYPES.get(function_type, {})
        base_points = function_type_data.get('point_value', 10)
        multiplier = subject_data.get('point_multiplier', 1.0)
        points = int(base_points * multiplier)
        
        if point_connection:
            try:
                point_connection.ensure_point_counting(
                    user_id,
                    'academic_points',
                    points,
                    'unified_game_mechanics'
                )
            except Exception as e:
                print(f"[UnifiedGameMechanics] Error awarding points: {e}")
        
        # Update progress
        progress['progress'] = min(progress['progress'] + (100 // len(subject_data['functions'])), 100)
        if progress['progress'] >= 100 and not progress.get('completed', False):
            progress['completed'] = True
            progress['completed_at'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'function_name': function_name,
            'points_awarded': points,
            'progress': progress['progress'],
            'completed': progress.get('completed', False)
        }
    
    def complete_subject(self, user_id: str, subject_id: str) -> Dict[str, Any]:
        """Complete a subject"""
        if subject_id not in self.user_progress.get(user_id, {}):
            return {'success': False, 'error': 'Subject not started'}
        
        progress = self.user_progress[user_id][subject_id]
        progress['completed'] = True
        progress['completed_at'] = datetime.utcnow().isoformat()
        progress['progress'] = 100
        
        # Award completion bonus
        if point_connection:
            try:
                point_connection.ensure_point_counting(
                    user_id,
                    'academic_points',
                    500,  # Completion bonus
                    'unified_game_mechanics'
                )
            except Exception as e:
                print(f"[UnifiedGameMechanics] Error awarding completion bonus: {e}")
        
        return {
            'success': True,
            'subject_id': subject_id,
            'completed': True,
            'bonus_points': 500
        }
    
    def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get user's progress across all subjects"""
        user_progress = self.user_progress.get(user_id, {})
        function_usage = self.function_usage.get(user_id, {})
        
        completed_count = sum(1 for p in user_progress.values() if p.get('completed', False))
        total_progress = sum(p.get('progress', 0) for p in user_progress.values())
        
        return {
            'success': True,
            'user_id': user_id,
            'subjects_started': len(user_progress),
            'subjects_completed': completed_count,
            'total_progress': total_progress / max(len(user_progress), 1),
            'function_usage': function_usage,
            'progress_by_class': {
                '1a': len([s for s in user_progress.keys() if s.startswith('math_1a') or s.startswith('science_1a') or s.startswith('language_1a') or s.startswith('technology_1a') or s.startswith('arts_1a')]),
                '2a': len([s for s in user_progress.keys() if s.endswith('_2a')]),
                '3a': len([s for s in user_progress.keys() if s.endswith('_3a')])
            }
        }
    
    def save_to_file(self, user_id: str):
        """Save user progress to JSON file"""
        file_path = os.path.join(self.data_dir, f'{user_id}_mechanics.json')
        data = {
            'user_id': user_id,
            'progress': dict(self.user_progress.get(user_id, {})),
            'function_usage': dict(self.function_usage.get(user_id, {})),
            'last_updated': datetime.utcnow().isoformat()
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, user_id: str):
        """Load user progress from JSON file"""
        file_path = os.path.join(self.data_dir, f'{user_id}_mechanics.json')
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.user_progress[user_id] = data.get('progress', {})
                    self.function_usage[user_id] = data.get('function_usage', {})
            except Exception as e:
                print(f"[UnifiedGameMechanics] Error loading from file: {e}")


# Global instance
unified_game_mechanics = UnifiedGameMechanicsConstructor()

