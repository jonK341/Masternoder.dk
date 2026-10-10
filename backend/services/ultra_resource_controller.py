"""
Ultra-Specific Resource Controller
Mind points to generate and build energy: mind, power, time, place
Focus: Affiliate links, guides, nodes that generate returns while resting
Minimalist investment automation
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class UltraResourceController:
    """
    Ultra-Specific Resource Controller
    - Mind points system (mind, power, time, place)
    - Energy generation and management
    - Affiliate/node passive income system
    - Minimalist investment automation
    - Modular content system
    - AI simplification system
    """
    
    # Energy types
    ENERGY_TYPES = {
        'mind': {
            'name': 'Mental Energy',
            'max_capacity': 100,
            'recharge_rate': 1.0,  # per hour
            'description': 'Mental processing capacity'
        },
        'power': {
            'name': 'Power Energy',
            'max_capacity': 100,
            'recharge_rate': 0.8,
            'description': 'Physical/action capacity'
        },
        'time': {
            'name': 'Time Energy',
            'max_capacity': 100,
            'recharge_rate': 1.2,
            'description': 'Time allocation capacity'
        },
        'place': {
            'name': 'Place Energy',
            'max_capacity': 100,
            'recharge_rate': 0.5,
            'description': 'Location/spatial capacity'
        }
    }
    
    # Resource generation nodes
    NODE_TYPES = {
        'affiliate_link': {
            'name': 'Affiliate Link',
            'energy_cost': {'mind': 5, 'time': 10},
            'generation_rate': {'cash': 0.1},  # per hour
            'setup_time': 15  # minutes
        },
        'guide_module': {
            'name': 'Guide Module',
            'energy_cost': {'mind': 20, 'time': 30},
            'generation_rate': {'cash': 0.5, 'mind_points': 1},
            'setup_time': 60
        },
        'automation_node': {
            'name': 'Automation Node',
            'energy_cost': {'mind': 30, 'power': 10},
            'generation_rate': {'cash': 1.0, 'time': 2},
            'setup_time': 120
        },
        'ai_simplifier': {
            'name': 'AI Simplifier',
            'energy_cost': {'mind': 10},
            'generation_rate': {'mind_points': 5, 'cash': 0.3},
            'setup_time': 30
        }
    }
    
    def __init__(self):
        self.user_energy = defaultdict(dict)  # {user_id: {energy_type: current_value}}
        self.user_nodes = defaultdict(list)  # {user_id: [node_data]}
        self.passive_income = defaultdict(float)  # {user_id: total_income}
        self.modular_content = defaultdict(list)  # {user_id: [content_modules]}
        self.ai_prompts = defaultdict(list)  # {user_id: [prompt_data]}
        self.automation_tasks = defaultdict(list)  # {user_id: [task_data]}
        
        # Initialize energy for users
        for energy_type in self.ENERGY_TYPES:
            self.user_energy = defaultdict(lambda: {
                'mind': 100,
                'power': 100,
                'time': 100,
                'place': 100,
                'last_update': datetime.utcnow().isoformat()
            })
    
    def get_energy_status(self, user_id: str) -> Dict[str, Any]:
        """Get current energy status"""
        energy = self.user_energy.get(user_id, {
            'mind': 100,
            'power': 100,
            'time': 100,
            'place': 100,
            'last_update': datetime.utcnow().isoformat()
        })
        
        # Recharge energy based on time passed
        last_update = datetime.fromisoformat(energy.get('last_update', datetime.utcnow().isoformat()))
        hours_passed = (datetime.utcnow() - last_update).total_seconds() / 3600
        
        for energy_type, config in self.ENERGY_TYPES.items():
            current = energy.get(energy_type, config['max_capacity'])
            recharge = config['recharge_rate'] * hours_passed
            new_value = min(config['max_capacity'], current + recharge)
            energy[energy_type] = new_value
        
        energy['last_update'] = datetime.utcnow().isoformat()
        self.user_energy[user_id] = energy
        
        return {
            'success': True,
            'user_id': user_id,
            'energy': energy,
            'total_energy': sum([energy.get(et, 0) for et in self.ENERGY_TYPES.keys()]),
            'max_total': sum([config['max_capacity'] for config in self.ENERGY_TYPES.values()])
        }
    
    def add_energy(self, user_id: str, energy_type: str, amount: float) -> Dict[str, Any]:
        """Add energy to a specific type"""
        if energy_type not in self.ENERGY_TYPES:
            return {'success': False, 'error': f'Invalid energy type: {energy_type}'}
        
        energy_status = self.get_energy_status(user_id)
        current_energy = energy_status['energy']
        
        config = self.ENERGY_TYPES[energy_type]
        current = current_energy.get(energy_type, config['max_capacity'])
        new_value = min(config['max_capacity'], current + amount)
        current_energy[energy_type] = new_value
        
        current_energy['last_update'] = datetime.utcnow().isoformat()
        self.user_energy[user_id] = current_energy
        
        return {
            'success': True,
            'energy_type': energy_type,
            'amount_added': amount,
            'previous': current,
            'current': new_value,
            'max': config['max_capacity']
        }
    
    def create_node(self, user_id: str, node_type: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a passive income node"""
        if node_type not in self.NODE_TYPES:
            return {'success': False, 'error': 'Invalid node type'}
        
        node_config = self.NODE_TYPES[node_type]
        energy_cost = node_config.get('energy_cost', {})
        
        # Check energy availability
        energy_status = self.get_energy_status(user_id)
        current_energy = energy_status['energy']
        
        for energy_type, cost in energy_cost.items():
            if current_energy.get(energy_type, 0) < cost:
                return {
                    'success': False,
                    'error': f'Insufficient {energy_type} energy. Need {cost}, have {current_energy.get(energy_type, 0)}'
                }
        
        # Deduct energy
        for energy_type, cost in energy_cost.items():
            current_energy[energy_type] = max(0, current_energy.get(energy_type, 0) - cost)
        
        self.user_energy[user_id] = current_energy
        
        # Create node
        node_id = str(uuid.uuid4())
        node = {
            'node_id': node_id,
            'user_id': user_id,
            'node_type': node_type,
            'name': node_data.get('name', node_config['name']),
            'description': node_data.get('description', ''),
            'affiliate_link': node_data.get('affiliate_link', ''),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'generation_rate': node_config.get('generation_rate', {}),
            'total_generated': 0.0,
            'last_generation': datetime.utcnow().isoformat(),
            'metadata': node_data.get('metadata', {})
        }
        
        self.user_nodes[user_id].append(node)
        
        return {
            'success': True,
            'node_id': node_id,
            'node': node,
            'energy_remaining': current_energy
        }
    
    def generate_passive_income(self, user_id: str) -> Dict[str, Any]:
        """Generate passive income from all active nodes"""
        nodes = self.user_nodes.get(user_id, [])
        active_nodes = [n for n in nodes if n.get('status') == 'active']
        
        total_generated = {
            'cash': 0.0,
            'mind_points': 0.0,
            'time': 0.0
        }
        
        now = datetime.utcnow()
        
        for node in active_nodes:
            last_gen = datetime.fromisoformat(node.get('last_generation', node['created_at']))
            hours_passed = (now - last_gen).total_seconds() / 3600
            
            generation_rate = node.get('generation_rate', {})
            for resource_type, rate in generation_rate.items():
                generated = rate * hours_passed
                total_generated[resource_type] = total_generated.get(resource_type, 0) + generated
                node['total_generated'] = node.get('total_generated', 0) + generated
            
            node['last_generation'] = now.isoformat()
        
        # Update passive income total
        self.passive_income[user_id] = self.passive_income.get(user_id, 0) + total_generated.get('cash', 0)
        
        # Award points
        if point_connection:
            try:
                if total_generated.get('cash', 0) > 0:
                    point_connection.ensure_point_counting(
                        user_id,
                        'coins',
                        int(total_generated['cash'] * 100),  # Convert to coins
                        'ultra_resource_controller'
                    )
            except Exception as e:
                print(f"[UltraResourceController] Error awarding points: {e}")
        
        return {
            'success': True,
            'user_id': user_id,
            'generated': total_generated,
            'total_passive_income': self.passive_income.get(user_id, 0),
            'active_nodes': len(active_nodes)
        }
    
    def create_modular_content(self, user_id: str, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create modular content (Lego-Robot logic)"""
        module_id = str(uuid.uuid4())
        
        # Check energy (modular content uses minimal energy)
        energy_status = self.get_energy_status(user_id)
        if energy_status['energy'].get('mind', 0) < 5:
            return {'success': False, 'error': 'Insufficient mind energy for content creation'}
        
        # Deduct minimal energy
        current_energy = energy_status['energy']
        current_energy['mind'] = max(0, current_energy.get('mind', 0) - 5)
        self.user_energy[user_id] = current_energy
        
        module = {
            'module_id': module_id,
            'user_id': user_id,
            'title': content_data.get('title', 'Untitled Module'),
            'content': content_data.get('content', ''),
            'module_type': content_data.get('module_type', 'guide'),  # guide, tip, automation, affiliate
            'length': content_data.get('length', 'ultra_short'),  # ultra_short, short, medium
            'target_audience': content_data.get('target_audience', 'minimalist_investor'),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'views': 0,
            'revenue': 0.0,
            'metadata': content_data.get('metadata', {})
        }
        
        self.modular_content[user_id].append(module)
        
        return {
            'success': True,
            'module_id': module_id,
            'module': module
        }
    
    def create_ai_simplifier_prompt(self, user_id: str, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI simplifier prompt (The 1% AI Hack)"""
        prompt_id = str(uuid.uuid4())
        
        # AI simplifier uses minimal energy (the whole point!)
        energy_status = self.get_energy_status(user_id)
        if energy_status['energy'].get('mind', 0) < 10:
            return {'success': False, 'error': 'Insufficient mind energy'}
        
        current_energy = energy_status['energy']
        current_energy['mind'] = max(0, current_energy.get('mind', 0) - 10)
        self.user_energy[user_id] = current_energy
        
        # Create AI prompt template
        base_prompt = """Jeg er IT-Ninja med 130% opfattelsesevner A+. 
Gør denne her tekniske proces simpel, så selv en 8-årig forstår den.

Input: {input}
Kontekst: {context}
Mål: {goal}

Output format: Ultra-simpel guide med maks 3 trin."""

        prompt = {
            'prompt_id': prompt_id,
            'user_id': user_id,
            'input': prompt_data.get('input', ''),
            'context': prompt_data.get('context', ''),
            'goal': prompt_data.get('goal', 'Simplify for 8-year-old'),
            'base_prompt': base_prompt,
            'full_prompt': base_prompt.format(
                input=prompt_data.get('input', ''),
                context=prompt_data.get('context', ''),
                goal=prompt_data.get('goal', 'Simplify')
            ),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'ready',
            'result': None,
            'metadata': prompt_data.get('metadata', {})
        }
        
        self.ai_prompts[user_id].append(prompt)
        
        return {
            'success': True,
            'prompt_id': prompt_id,
            'prompt': prompt
        }
    
    def create_automation_task(self, user_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create automation task (automate all technical)"""
        task_id = str(uuid.uuid4())
        
        # Automation setup uses energy but saves time later
        energy_status = self.get_energy_status(user_id)
        if energy_status['energy'].get('mind', 0) < 20 or energy_status['energy'].get('power', 0) < 10:
            return {'success': False, 'error': 'Insufficient energy for automation setup'}
        
        current_energy = energy_status['energy']
        current_energy['mind'] = max(0, current_energy.get('mind', 0) - 20)
        current_energy['power'] = max(0, current_energy.get('power', 0) - 10)
        self.user_energy[user_id] = current_energy
        
        task = {
            'task_id': task_id,
            'user_id': user_id,
            'task_name': task_data.get('task_name', 'Untitled Automation'),
            'description': task_data.get('description', ''),
            'automation_type': task_data.get('automation_type', 'technical'),  # technical, content, income
            'script': task_data.get('script', ''),
            'schedule': task_data.get('schedule', {}),  # cron-like schedule
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'runs_count': 0,
            'time_saved': 0,  # hours
            'metadata': task_data.get('metadata', {})
        }
        
        self.automation_tasks[user_id].append(task)
        
        return {
            'success': True,
            'task_id': task_id,
            'task': task
        }
    
    def get_resource_summary(self, user_id: str) -> Dict[str, Any]:
        """Get complete resource summary"""
        energy_status = self.get_energy_status(user_id)
        income_status = self.generate_passive_income(user_id)
        
        nodes = self.user_nodes.get(user_id, [])
        content_modules = self.modular_content.get(user_id, [])
        automation_tasks = self.automation_tasks.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'energy': energy_status['energy'],
            'total_energy_percentage': (energy_status['total_energy'] / energy_status['max_total']) * 100,
            'passive_income': {
                'total': self.passive_income.get(user_id, 0),
                'recent_generated': income_status['generated']
            },
            'nodes': {
                'total': len(nodes),
                'active': len([n for n in nodes if n.get('status') == 'active']),
                'total_generated': sum([n.get('total_generated', 0) for n in nodes])
            },
            'content_modules': {
                'total': len(content_modules),
                'active': len([c for c in content_modules if c.get('status') == 'active']),
                'total_views': sum([c.get('views', 0) for c in content_modules])
            },
            'automation_tasks': {
                'total': len(automation_tasks),
                'active': len([t for t in automation_tasks if t.get('status') == 'active']),
                'total_time_saved': sum([t.get('time_saved', 0) for t in automation_tasks])
            }
        }


# Global instance
ultra_resource_controller = UltraResourceController()

