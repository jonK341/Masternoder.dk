"""
Mission One Controller and One Operator System
power.force.quest
Enhanced with coordinates, secretary, vold flise metal, and new tech
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import hashlib
import random

class MissionControllerOperator:
    """Mission Controller and Operator System"""
    
    def __init__(self):
        self.controllers = {}  # {controller_id: controller_data}
        self.operators = {}  # {operator_id: operator_data}
        self.missions = {}  # {mission_id: mission_data}
        self.active_assignments = defaultdict(list)  # {user_id: [assignment_ids]}
        self.power_force_quests = {}  # {quest_id: quest_data}
        self.quests = {}  # {quest_id: quest_data} - Additional quests
        self.tasks = {}  # {task_id: task_data} - Additional tasks
        self.secretaries = {}  # {secretary_id: secretary_data}
        self.download_intruders = {}  # {intruder_id: intruder_data}
        self.trashpassers = {}  # {trashpasser_id: trashpasser_data}
        self.vold_flise_metal_integration = {}  # {user_id: metal_data}
        self.available_tech = self._initialize_tech()  # Available technology
        self.quest_templates = self._initialize_quest_templates()  # Pre-defined quest templates
        self.task_templates = self._initialize_task_templates()  # Pre-defined task templates
    
    def create_controller(
        self,
        user_id: str,
        controller_name: str = "Mission Controller One"
    ) -> Dict[str, Any]:
        """Create mission controller"""
        controller_id = f"controller_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        controller_data = {
            'controller_id': controller_id,
            'user_id': user_id,
            'name': controller_name,
            'type': 'controller',
            'power_level': 100,
            'force_level': 100,
            'quest_capacity': 10,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'missions_controlled': []
        }
        
        self.controllers[controller_id] = controller_data
        
        return {
            'success': True,
            'controller': controller_data,
            'message': f'Controller {controller_name} created'
        }
    
    def create_operator(
        self,
        user_id: str,
        operator_name: str = "Mission Operator One",
        coordinates: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Create mission operator with coordinates"""
        operator_id = f"operator_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        # Default coordinates if not provided
        if not coordinates:
            coordinates = {
                'x': random.uniform(-1000, 1000),
                'y': random.uniform(-1000, 1000),
                'z': random.uniform(-500, 500)
            }
        
        operator_data = {
            'operator_id': operator_id,
            'user_id': user_id,
            'name': operator_name,
            'type': 'operator',
            'power_level': 75,
            'force_level': 75,
            'fix_capability': True,
            'use_power': True,
            'use_force': True,
            'coordinates': coordinates,
            'current_location': coordinates,
            'movement_speed': 10.0,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'missions_operated': []
        }
        
        self.operators[operator_id] = operator_data
        
        return {
            'success': True,
            'operator': operator_data,
            'message': f'Operator {operator_name} created at coordinates {coordinates}'
        }
    
    def update_operator_coordinates(
        self,
        operator_id: str,
        coordinates: Dict[str, float]
    ) -> Dict[str, Any]:
        """Update operator coordinates"""
        if operator_id not in self.operators:
            return {
                'success': False,
                'error': 'Operator not found'
            }
        
        operator = self.operators[operator_id]
        operator['current_location'] = coordinates
        operator['last_movement'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'operator': operator,
            'message': f'Operator coordinates updated to {coordinates}'
        }
    
    def create_power_force_quest(
        self,
        user_id: str,
        quest_name: str,
        controller_id: Optional[str] = None,
        operator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create power.force.quest"""
        quest_id = f"quest_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        # Auto-create controller and operator if not provided
        if not controller_id:
            controller_result = self.create_controller(user_id)
            controller_id = controller_result['controller']['controller_id']
        
        if not operator_id:
            operator_result = self.create_operator(user_id)
            operator_id = operator_result['operator']['operator_id']
        
        quest_data = {
            'quest_id': quest_id,
            'user_id': user_id,
            'name': quest_name,
            'controller_id': controller_id,
            'operator_id': operator_id,
            'power_level': 100,
            'force_level': 100,
            'quest_type': 'power_force',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'objectives': [],
            'fixes_applied': [],
            'power_used': 0,
            'force_used': 0
        }
        
        self.power_force_quests[quest_id] = quest_data
        
        # Link to controller and operator
        if controller_id in self.controllers:
            self.controllers[controller_id]['missions_controlled'].append(quest_id)
        
        if operator_id in self.operators:
            self.operators[operator_id]['missions_operated'].append(quest_id)
        
        return {
            'success': True,
            'quest': quest_data,
            'controller': self.controllers.get(controller_id),
            'operator': self.operators.get(operator_id),
            'message': f'Power.Force.Quest {quest_name} created'
        }
    
    def use_power_force(
        self,
        quest_id: str,
        power_amount: int = 10,
        force_amount: int = 10,
        action: str = 'fix'
    ) -> Dict[str, Any]:
        """Use power and force in quest"""
        if quest_id not in self.power_force_quests:
            return {
                'success': False,
                'error': 'Quest not found'
            }
        
        quest = self.power_force_quests[quest_id]
        
        if quest['status'] != 'active':
            return {
                'success': False,
                'error': f'Quest is {quest["status"]}'
            }
        
        quest['power_used'] += power_amount
        quest['force_used'] += force_amount
        
        if action == 'fix':
            fix_data = {
                'fix_id': f"fix_{datetime.utcnow().timestamp()}",
                'power_used': power_amount,
                'force_used': force_amount,
                'fixed_at': datetime.utcnow().isoformat()
            }
            quest['fixes_applied'].append(fix_data)
        
        return {
            'success': True,
            'quest': quest,
            'power_used': quest['power_used'],
            'force_used': quest['force_used'],
            'message': f'Used {power_amount} power and {force_amount} force'
        }
    
    def _initialize_tech(self) -> Dict[str, Dict[str, Any]]:
        """Initialize available technology"""
        return {
            'quantum_computing': {
                'name': 'Quantum Computing',
                'description': 'Advanced quantum processing technology',
                'power_boost': 50,
                'force_boost': 50,
                'unlocked': False
            },
            'neural_network': {
                'name': 'Neural Network AI',
                'description': 'AI-powered neural network system',
                'power_boost': 30,
                'force_boost': 40,
                'unlocked': False
            },
            'quantum_stabilizer': {
                'name': 'Quantum Stabilizer',
                'description': 'Stabilizes quantum operations',
                'power_boost': 25,
                'force_boost': 25,
                'unlocked': False
            },
            'ai_prediction': {
                'name': 'AI Battle Prediction',
                'description': 'Predicts battle outcomes using AI',
                'power_boost': 20,
                'force_boost': 30,
                'unlocked': False
            },
            'automation_system': {
                'name': 'Advanced Automation',
                'description': 'Automates mission operations',
                'power_boost': 40,
                'force_boost': 35,
                'unlocked': False
            }
        }
    
    def create_quest(
        self,
        user_id: str,
        quest_name: str,
        quest_type: str = 'standard',
        objectives: Optional[List[Dict[str, Any]]] = None,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create additional quest (can use template)"""
        quest_id = f"quest_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        # Use template if provided
        if template_name and template_name in self.quest_templates:
            template = self.quest_templates[template_name]
            quest_name = template['name']
            quest_type = template['quest_type']
            objectives = template['objectives']
            rewards = template['rewards']
        else:
            if not objectives:
                objectives = [
                    {'objective_id': f"obj_{i}", 'description': f'Objective {i+1}', 'status': 'pending'}
                    for i in range(3)
                ]
            rewards = {
                'points': 100,
                'items': [],
                'tech_unlocks': []
            }
        
        quest_data = {
            'quest_id': quest_id,
            'user_id': user_id,
            'name': quest_name,
            'quest_type': quest_type,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'objectives': objectives,
            'rewards': rewards,
            'progress': 0,
            'template_used': template_name if template_name else None
        }
        
        self.quests[quest_id] = quest_data
        
        return {
            'success': True,
            'quest': quest_data,
            'message': f'Quest {quest_name} created'
        }
    
    def get_quest_templates(self) -> Dict[str, Any]:
        """Get all quest templates"""
        return {
            'success': True,
            'templates': self.quest_templates,
            'total': len(self.quest_templates)
        }
    
    def create_task(
        self,
        user_id: str,
        task_name: str,
        task_type: str = 'standard',
        priority: str = 'medium',
        quest_id: Optional[str] = None,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create additional task (can use template)"""
        task_id = f"task_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        # Use template if provided
        if template_name and template_name in self.task_templates:
            template = self.task_templates[template_name]
            task_name = template['name']
            task_type = template['task_type']
            priority = template['priority']
            description = template.get('description', '')
            estimated_time = template.get('estimated_time', '1 hour')
        else:
            description = ''
            estimated_time = '1 hour'
        
        task_data = {
            'task_id': task_id,
            'user_id': user_id,
            'name': task_name,
            'description': description,
            'task_type': task_type,
            'priority': priority,
            'quest_id': quest_id,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'due_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'completion': 0,
            'estimated_time': estimated_time,
            'template_used': template_name if template_name else None
        }
        
        self.tasks[task_id] = task_data
        
        # Link to quest if provided
        if quest_id and quest_id in self.quests:
            if 'tasks' not in self.quests[quest_id]:
                self.quests[quest_id]['tasks'] = []
            self.quests[quest_id]['tasks'].append(task_id)
        
        return {
            'success': True,
            'task': task_data,
            'message': f'Task {task_name} created'
        }
    
    def get_task_templates(self) -> Dict[str, Any]:
        """Get all task templates"""
        return {
            'success': True,
            'templates': self.task_templates,
            'total': len(self.task_templates)
        }
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Complete a task"""
        if task_id not in self.tasks:
            return {
                'success': False,
                'error': 'Task not found'
            }
        
        task = self.tasks[task_id]
        task['status'] = 'completed'
        task['completed_at'] = datetime.utcnow().isoformat()
        task['completion'] = 100
        
        # Update quest progress if linked
        if task.get('quest_id'):
            quest_id = task['quest_id']
            if quest_id in self.quests:
                quest = self.quests[quest_id]
                # Calculate quest progress
                quest_tasks = [t for t in self.tasks.values() if t.get('quest_id') == quest_id]
                completed_tasks = [t for t in quest_tasks if t.get('status') == 'completed']
                if quest_tasks:
                    quest['progress'] = int((len(completed_tasks) / len(quest_tasks)) * 100)
        
        return {
            'success': True,
            'task': task,
            'message': f'Task {task["name"]} completed'
        }
    
    def create_secretary(
        self,
        user_id: str,
        secretary_name: str = "ZA Secretary"
    ) -> Dict[str, Any]:
        """Create secretary to track download intruders and trashpassers"""
        secretary_id = f"secretary_{hashlib.sha256(f'{user_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        secretary_data = {
            'secretary_id': secretary_id,
            'user_id': user_id,
            'name': secretary_name,
            'type': 'secretary',
            'tracking_capability': True,
            'intruder_tracking': True,
            'trashpasser_tracking': True,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'intruders_tracked': 0,
            'trashpassers_tracked': 0,
            'download_monitoring': True
        }
        
        self.secretaries[secretary_id] = secretary_data
        
        return {
            'success': True,
            'secretary': secretary_data,
            'message': f'Secretary {secretary_name} created - Ready to track intruders and trashpassers'
        }
    
    def track_download_intruder(
        self,
        secretary_id: str,
        intruder_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track download intruder"""
        if secretary_id not in self.secretaries:
            return {
                'success': False,
                'error': 'Secretary not found'
            }
        
        intruder_id = f"intruder_{hashlib.sha256(f'{secretary_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        intruder = {
            'intruder_id': intruder_id,
            'secretary_id': secretary_id,
            'detected_at': datetime.utcnow().isoformat(),
            'intruder_type': 'download',
            'threat_level': intruder_data.get('threat_level', 'medium'),
            'ip_address': intruder_data.get('ip_address', 'unknown'),
            'download_count': intruder_data.get('download_count', 0),
            'download_size': intruder_data.get('download_size', 0),
            'files_downloaded': intruder_data.get('files_downloaded', []),
            'user_agent': intruder_data.get('user_agent', 'unknown'),
            'location': intruder_data.get('location', 'unknown'),
            'status': 'tracked',
            'action_taken': None,
            'severity': 'high' if intruder_data.get('download_count', 0) > 100 else 'medium'
        }
        
        self.download_intruders[intruder_id] = intruder
        self.secretaries[secretary_id]['intruders_tracked'] += 1
        
        return {
            'success': True,
            'intruder': intruder,
            'message': f'Download intruder tracked - Threat: {intruder["threat_level"]}, Downloads: {intruder["download_count"]}'
        }
    
    def get_tracked_intruders(self, secretary_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all tracked download intruders"""
        if secretary_id:
            intruders = [
                i for i in self.download_intruders.values()
                if i.get('secretary_id') == secretary_id
            ]
        else:
            intruders = list(self.download_intruders.values())
        
        return {
            'success': True,
            'intruders': intruders,
            'total': len(intruders)
        }
    
    def track_trashpasser(
        self,
        secretary_id: str,
        trashpasser_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Track trashpasser"""
        if secretary_id not in self.secretaries:
            return {
                'success': False,
                'error': 'Secretary not found'
            }
        
        trashpasser_id = f"trashpasser_{hashlib.sha256(f'{secretary_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        violations = trashpasser_data.get('violations', [])
        violation_count = len(violations)
        
        trashpasser = {
            'trashpasser_id': trashpasser_id,
            'secretary_id': secretary_id,
            'detected_at': datetime.utcnow().isoformat(),
            'trashpasser_type': trashpasser_data.get('type', 'unknown'),
            'threat_level': trashpasser_data.get('threat_level', 'low'),
            'violations': violations,
            'violation_count': violation_count,
            'ip_address': trashpasser_data.get('ip_address', 'unknown'),
            'activity_log': trashpasser_data.get('activity_log', []),
            'status': 'tracked',
            'action_taken': None,
            'severity': 'high' if violation_count > 5 else 'medium' if violation_count > 2 else 'low'
        }
        
        self.trashpassers[trashpasser_id] = trashpasser
        self.secretaries[secretary_id]['trashpassers_tracked'] += 1
        
        return {
            'success': True,
            'trashpasser': trashpasser,
            'message': f'Trashpasser tracked - Type: {trashpasser["trashpasser_type"]}, Violations: {violation_count}'
        }
    
    def get_tracked_trashpassers(self, secretary_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all tracked trashpassers"""
        if secretary_id:
            trashpassers = [
                t for t in self.trashpassers.values()
                if t.get('secretary_id') == secretary_id
            ]
        else:
            trashpassers = list(self.trashpassers.values())
        
        return {
            'success': True,
            'trashpassers': trashpassers,
            'total': len(trashpassers)
        }
    
    def activate_vold_flise_metal(
        self,
        user_id: str,
        operator_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Activate Vold Flise Metal integration"""
        # Import metal system
        try:
            from backend.services.jons_id_metal_system import jons_id_metal_system
            metal_result = jons_id_metal_system.activate_theme(user_id, 'vold_flise_metal')
            
            if metal_result.get('success'):
                self.vold_flise_metal_integration[user_id] = {
                    'activated': True,
                    'activated_at': datetime.utcnow().isoformat(),
                    'metal_data': metal_result.get('user_data'),
                    'operator_id': operator_id
                }
                
                # Apply metal bonuses to operator if provided
                if operator_id and operator_id in self.operators:
                    operator = self.operators[operator_id]
                    operator['vold_flise_metal'] = True
                    operator['power_level'] += 50  # Metal power boost
                    operator['force_level'] += 50  # Metal force boost
                
                return {
                    'success': True,
                    'vold_flise_metal': self.vold_flise_metal_integration[user_id],
                    'metal_result': metal_result,
                    'message': 'Vold Flise Metal activated and integrated'
                }
        except ImportError:
            pass
        
        return {
            'success': False,
            'error': 'Metal system not available'
        }
    
    def unlock_tech(
        self,
        user_id: str,
        tech_name: str
    ) -> Dict[str, Any]:
        """Unlock new technology"""
        if tech_name not in self.available_tech:
            return {
                'success': False,
                'error': f'Technology {tech_name} not found'
            }
        
        tech = self.available_tech[tech_name]
        
        if tech.get('unlocked'):
            return {
                'success': False,
                'error': f'Technology {tech_name} already unlocked'
            }
        
        tech['unlocked'] = True
        tech['unlocked_by'] = user_id
        tech['unlocked_at'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'tech': tech,
            'message': f'Technology {tech_name} unlocked!'
        }
    
    def get_available_tech(self) -> Dict[str, Any]:
        """Get all available technology"""
        return {
            'success': True,
            'tech': self.available_tech,
            'unlocked_count': sum(1 for t in self.available_tech.values() if t.get('unlocked')),
            'total_count': len(self.available_tech)
        }
    
    def get_user_mission_system(self, user_id: str) -> Dict[str, Any]:
        """Get user's mission controller and operator system"""
        controllers = [
            c for c in self.controllers.values()
            if c.get('user_id') == user_id
        ]
        operators = [
            o for o in self.operators.values()
            if o.get('user_id') == user_id
        ]
        quests = [
            q for q in self.power_force_quests.values()
            if q.get('user_id') == user_id
        ]
        additional_quests = [
            q for q in self.quests.values()
            if q.get('user_id') == user_id
        ]
        tasks = [
            t for t in self.tasks.values()
            if t.get('user_id') == user_id
        ]
        secretaries = [
            s for s in self.secretaries.values()
            if s.get('user_id') == user_id
        ]
        
        return {
            'success': True,
            'controllers': controllers,
            'operators': operators,
            'quests': quests,
            'additional_quests': additional_quests,
            'tasks': tasks,
            'secretaries': secretaries,
            'vold_flise_metal': self.vold_flise_metal_integration.get(user_id),
            'available_tech': self.available_tech,
            'total_controllers': len(controllers),
            'total_operators': len(operators),
            'total_quests': len(quests) + len(additional_quests),
            'total_tasks': len(tasks),
            'total_secretaries': len(secretaries)
        }


# Global instance
mission_controller_operator = MissionControllerOperator()

