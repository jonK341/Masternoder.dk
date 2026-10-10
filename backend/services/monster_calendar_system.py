"""
Fantasy Monster Calendar and Appointment System
Manages appointments, guides, and tutorials for fantasy monsters
"""
import os
import json
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

class MonsterCalendarSystem:
    """
    Calendar system for fantasy monsters with:
    - Appointment scheduling
    - Guides and tutorials
    - Monster management
    - Event tracking
    """
    
    def __init__(self):
        self.calendar_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'monster_calendar.json'
        )
        self.guides_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'monster_guides.json'
        )
        self.tutorials_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'monster_tutorials.json'
        )
        
        os.makedirs(os.path.dirname(self.calendar_file), exist_ok=True)
        
        # Load data
        self.calendar = self._load_calendar()
        self.guides = self._load_guides()
        self.tutorials = self._load_tutorials()
        
        # Initialize default monsters and guides
        self._initialize_default_data()
    
    def _load_calendar(self) -> Dict[str, Any]:
        """Load calendar data"""
        try:
            if os.path.exists(self.calendar_file):
                with open(self.calendar_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading calendar: {e}")
        return {'appointments': {}, 'monsters': {}}
    
    def _save_calendar(self):
        """Save calendar data"""
        try:
            with open(self.calendar_file, 'w', encoding='utf-8') as f:
                json.dump(self.calendar, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving calendar: {e}")
    
    def _load_guides(self) -> Dict[str, Any]:
        """Load guides"""
        try:
            if os.path.exists(self.guides_file):
                with open(self.guides_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading guides: {e}")
        return {'guides': []}
    
    def _save_guides(self):
        """Save guides"""
        try:
            with open(self.guides_file, 'w', encoding='utf-8') as f:
                json.dump(self.guides, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving guides: {e}")
    
    def _load_tutorials(self) -> Dict[str, Any]:
        """Load tutorials"""
        try:
            if os.path.exists(self.tutorials_file):
                with open(self.tutorials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tutorials: {e}")
        return {'tutorials': []}
    
    def _save_tutorials(self):
        """Save tutorials"""
        try:
            with open(self.tutorials_file, 'w', encoding='utf-8') as f:
                json.dump(self.tutorials, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving tutorials: {e}")
    
    def _initialize_default_data(self):
        """Initialize default monsters, guides, and tutorials"""
        if not self.calendar.get('monsters'):
            self.calendar['monsters'] = {
                'dragon': {
                    'name': 'Dragon',
                    'type': 'legendary',
                    'appointment_types': ['training', 'feeding', 'bonding', 'combat'],
                    'default_duration': 60
                },
                'griffin': {
                    'name': 'Griffin',
                    'type': 'mythical',
                    'appointment_types': ['flying', 'hunting', 'care'],
                    'default_duration': 45
                },
                'phoenix': {
                    'name': 'Phoenix',
                    'type': 'immortal',
                    'appointment_types': ['rebirth', 'fire_training', 'meditation'],
                    'default_duration': 90
                },
                'kraken': {
                    'name': 'Kraken',
                    'type': 'aquatic',
                    'appointment_types': ['diving', 'feeding', 'exploration'],
                    'default_duration': 120
                }
            }
            self._save_calendar()
        
        if not self.guides.get('guides'):
            self.guides['guides'] = [
                {
                    'guide_id': str(uuid.uuid4()),
                    'title': 'Dragon Care Guide',
                    'monster_type': 'dragon',
                    'content': 'Complete guide to caring for dragons...',
                    'sections': ['feeding', 'housing', 'training', 'health'],
                    'created_at': datetime.now().isoformat()
                },
                {
                    'guide_id': str(uuid.uuid4()),
                    'title': 'Griffin Flying Techniques',
                    'monster_type': 'griffin',
                    'content': 'Master the art of flying with griffins...',
                    'sections': ['basic_flying', 'advanced_maneuvers', 'safety'],
                    'created_at': datetime.now().isoformat()
                }
            ]
            self._save_guides()
        
        if not self.tutorials.get('tutorials'):
            self.tutorials['tutorials'] = [
                {
                    'tutorial_id': str(uuid.uuid4()),
                    'title': 'Introduction to Monster Bonding',
                    'monster_type': 'all',
                    'steps': [
                        'Understanding monster psychology',
                        'Establishing trust',
                        'Basic commands',
                        'Advanced communication'
                    ],
                    'duration_minutes': 30,
                    'difficulty': 'beginner',
                    'created_at': datetime.now().isoformat()
                }
            ]
            self._save_tutorials()
    
    def create_appointment(
        self,
        monster_type: str,
        appointment_type: str,
        scheduled_time: str,
        duration_minutes: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create appointment with fantasy monster"""
        try:
            appointment_id = str(uuid.uuid4())
            
            # Validate monster type
            if monster_type not in self.calendar['monsters']:
                return {'success': False, 'error': f'Unknown monster type: {monster_type}'}
            
            monster = self.calendar['monsters'][monster_type]
            
            # Validate appointment type
            if appointment_type not in monster['appointment_types']:
                return {'success': False, 'error': f'Invalid appointment type for {monster_type}'}
            
            # Parse scheduled time
            try:
                scheduled_datetime = datetime.fromisoformat(scheduled_time)
            except:
                return {'success': False, 'error': 'Invalid date format. Use ISO format.'}
            
            # Use default duration if not specified
            if duration_minutes is None:
                duration_minutes = monster['default_duration']
            
            appointment = {
                'appointment_id': appointment_id,
                'monster_type': monster_type,
                'appointment_type': appointment_type,
                'scheduled_time': scheduled_time,
                'scheduled_datetime': scheduled_datetime.isoformat(),
                'duration_minutes': duration_minutes,
                'notes': notes,
                'status': 'scheduled',
                'created_at': datetime.now().isoformat()
            }
            
            self.calendar['appointments'][appointment_id] = appointment
            self._save_calendar()
            
            return {
                'success': True,
                'appointment_id': appointment_id,
                'appointment': appointment
            }
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_appointments(
        self,
        monster_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get appointments with optional filters"""
        appointments = list(self.calendar['appointments'].values())
        
        # Filter by monster type
        if monster_type:
            appointments = [a for a in appointments if a['monster_type'] == monster_type]
        
        # Filter by date range
        if start_date:
            start = datetime.fromisoformat(start_date)
            appointments = [a for a in appointments if datetime.fromisoformat(a['scheduled_datetime']) >= start]
        
        if end_date:
            end = datetime.fromisoformat(end_date)
            appointments = [a for a in appointments if datetime.fromisoformat(a['scheduled_datetime']) <= end]
        
        # Sort by scheduled time
        appointments.sort(key=lambda x: x['scheduled_datetime'])
        
        return {
            'success': True,
            'appointments': appointments,
            'total': len(appointments)
        }
    
    def add_guide(
        self,
        title: str,
        monster_type: str,
        content: str,
        sections: List[str]
    ) -> Dict[str, Any]:
        """Add guide for monster"""
        try:
            guide_id = str(uuid.uuid4())
            
            guide = {
                'guide_id': guide_id,
                'title': title,
                'monster_type': monster_type,
                'content': content,
                'sections': sections,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.guides['guides'].append(guide)
            self._save_guides()
            
            return {
                'success': True,
                'guide_id': guide_id,
                'guide': guide
            }
        except Exception as e:
            logger.error(f"Error adding guide: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_guides(self, monster_type: Optional[str] = None) -> Dict[str, Any]:
        """Get guides, optionally filtered by monster type"""
        guides = self.guides['guides']
        
        if monster_type:
            guides = [g for g in guides if g['monster_type'] == monster_type]
        
        return {
            'success': True,
            'guides': guides,
            'total': len(guides)
        }
    
    def add_tutorial(
        self,
        title: str,
        monster_type: str,
        steps: List[str],
        duration_minutes: int,
        difficulty: str = 'beginner'
    ) -> Dict[str, Any]:
        """Add tutorial for monster"""
        try:
            tutorial_id = str(uuid.uuid4())
            
            tutorial = {
                'tutorial_id': tutorial_id,
                'title': title,
                'monster_type': monster_type,
                'steps': steps,
                'duration_minutes': duration_minutes,
                'difficulty': difficulty,
                'created_at': datetime.now().isoformat()
            }
            
            self.tutorials['tutorials'].append(tutorial)
            self._save_tutorials()
            
            return {
                'success': True,
                'tutorial_id': tutorial_id,
                'tutorial': tutorial
            }
        except Exception as e:
            logger.error(f"Error adding tutorial: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_tutorials(self, monster_type: Optional[str] = None) -> Dict[str, Any]:
        """Get tutorials, optionally filtered by monster type"""
        tutorials = self.tutorials['tutorials']
        
        if monster_type:
            tutorials = [t for t in tutorials if t['monster_type'] == monster_type or t['monster_type'] == 'all']
        
        return {
            'success': True,
            'tutorials': tutorials,
            'total': len(tutorials)
        }


# Global instance
monster_calendar_system = MonsterCalendarSystem()

