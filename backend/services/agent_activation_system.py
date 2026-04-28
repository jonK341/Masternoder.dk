"""
Agent Activation System
Automatic activation methods and functions
"""
import os
import sys
import json
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentActivationSystem:
    """Automatic activation system for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.activation_file = os.path.join(self.base_dir, 'logs', 'agent_activation', 'activations.json')
        self.running = False
        self.activation_threads = []
        self.load_activations()
    
    def load_activations(self):
        """Load activation configuration"""
        os.makedirs(os.path.dirname(self.activation_file), exist_ok=True)
        if os.path.exists(self.activation_file):
            try:
                with open(self.activation_file, 'r') as f:
                    self.activations = json.load(f)
            except:
                self.activations = self._default_activations()
        else:
            self.activations = self._default_activations()
            self.save_activations()
    
    def _default_activations(self) -> Dict:
        """Default activation configuration"""
        return {
            'auto_activations': [
                {
                    'id': 'auto_health_check',
                    'name': 'Auto Health Check',
                    'function': 'skill_monitor_system_health',
                    'interval_minutes': 15,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_blueprint_check',
                    'name': 'Auto Blueprint Check',
                    'function': 'skill_check_blueprints',
                    'interval_minutes': 60,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_database_check',
                    'name': 'Auto Database Check',
                    'function': 'skill_verify_database',
                    'interval_minutes': 120,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_research',
                    'name': 'Auto Research',
                    'function': 'start_research_cycle',
                    'interval_minutes': 180,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_monitoring',
                    'name': 'Auto Monitoring',
                    'function': 'collect_monitoring_data',
                    'interval_minutes': 30,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_python_scan',
                    'name': 'Auto Python Script Scan',
                    'function': 'skill_list_python_scripts',
                    'interval_minutes': 240,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_trigger_check',
                    'name': 'Auto Trigger System Check',
                    'function': 'skill_get_trigger_stats',
                    'interval_minutes': 60,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_research_summary',
                    'name': 'Auto Research Summary',
                    'function': 'skill_get_research_summary',
                    'interval_minutes': 120,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_monitoring_summary',
                    'name': 'Auto Monitoring Summary',
                    'function': 'skill_get_monitoring_summary',
                    'interval_minutes': 90,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_point_calculation',
                    'name': 'Auto Point Calculation',
                    'function': 'skill_calculate_with_intelligence',
                    'interval_minutes': 180,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_anomaly_detection',
                    'name': 'Auto Anomaly Detection',
                    'function': 'skill_detect_point_loss',
                    'interval_minutes': 240,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_system_repair',
                    'name': 'Auto System Repair',
                    'function': 'skill_repair_all_systems',
                    'interval_minutes': 360,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_pattern_analysis',
                    'name': 'Auto Pattern Analysis',
                    'function': 'skill_analyze_patterns',
                    'interval_minutes': 480,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_future_prediction',
                    'name': 'Auto Future Prediction',
                    'function': 'skill_predict_future_points',
                    'interval_minutes': 720,
                    'enabled': True,
                    'trigger_points': True
                },
                {
                    'id': 'auto_support_check',
                    'name': 'Auto Support Check',
                    'function': 'skill_get_support_tickets',
                    'interval_minutes': 30,
                    'enabled': True,
                    'trigger_points': True
                }
            ],
            'activation_history': [],
            'last_activations': {}
        }
    
    def save_activations(self):
        """Save activation configuration"""
        try:
            with open(self.activation_file, 'w') as f:
                json.dump(self.activations, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving activations: {e}")
    
    def start(self):
        """Start activation system"""
        if self.running:
            return
        
        self.running = True
        
        # Start activation loop
        thread = threading.Thread(target=self._activation_loop, daemon=True)
        thread.start()
        self.activation_threads.append(thread)
        
        print("[AgentActivation] started")
    
    def stop(self):
        """Stop activation system"""
        self.running = False
        for thread in self.activation_threads:
            if thread.is_alive():
                thread.join(timeout=1)
        self.activation_threads.clear()
        print("[AgentActivation] stopped")
    
    def _activation_loop(self):
        """Main activation loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for activation in self.activations.get('auto_activations', []):
                    if not activation.get('enabled', True):
                        continue
                    
                    activation_id = activation.get('id')
                    interval = activation.get('interval_minutes', 60)
                    last_activation = self.activations.get('last_activations', {}).get(activation_id)
                    
                    should_activate = False
                    
                    if not last_activation:
                        should_activate = True
                    else:
                        try:
                            last_time = datetime.fromisoformat(last_activation)
                            time_diff = current_time - last_time
                            if time_diff >= timedelta(minutes=interval):
                                should_activate = True
                        except:
                            should_activate = True
                    
                    if should_activate:
                        self._execute_activation(activation)
                        self.activations['last_activations'][activation_id] = current_time.isoformat()
                        self.save_activations()
                
                # Sleep for 1 minute
                time.sleep(60)
                
            except Exception as e:
                print(f"Error in activation loop: {e}")
                time.sleep(60)
    
    def _execute_activation(self, activation: Dict):
        """Execute an activation"""
        try:
            function_name = activation.get('function')
            activation_id = activation.get('id')
            
            # Get function from master_fix_agent_skills
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            
            if hasattr(master_fix_agent_skills, function_name):
                func = getattr(master_fix_agent_skills, function_name)
                result = func()
                
                # Record activation
                activation_record = {
                    'activation_id': activation_id,
                    'activation_name': activation.get('name'),
                    'function': function_name,
                    'success': result.get('success', False),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.activations['activation_history'].append(activation_record)
                
                # Keep only last 1000 records
                if len(self.activations['activation_history']) > 1000:
                    self.activations['activation_history'] = self.activations['activation_history'][-1000:]
                
                # Award points if enabled
                if activation.get('trigger_points', False) and result.get('success', False):
                    try:
                        from backend.services.agent_trigger_system import agent_trigger_system
                        agent_trigger_system.award_points('automation_task', 'agent_user', {
                            'activation': activation_id,
                            'function': function_name
                        })
                    except:
                        pass
                
                print(f"[OK] Activation {activation.get('name')} executed: {result.get('success', False)}")
                
            elif function_name == 'start_research_cycle':
                # Special handling for research
                from backend.services.agent_research_tracker import agent_research_tracker
                topics = agent_research_tracker.research_data.get('research_topics', [])
                if topics:
                    topic = topics[0]  # Start with first topic
                    result = agent_research_tracker.start_research(topic.get('id'))
                    
                    if result.get('success') and activation.get('trigger_points', False):
                        from backend.services.agent_trigger_system import agent_trigger_system
                        agent_trigger_system.award_points('research_completed', 'agent_user')
                
            elif function_name == 'collect_monitoring_data':
                # Special handling for monitoring
                from backend.services.agent_research_tracker import agent_research_tracker
                targets = agent_research_tracker.monitoring_data.get('monitoring_targets', [])
                for target in targets[:2]:  # Collect data for first 2 targets
                    metrics = {
                        'status': 'active',
                        'timestamp': datetime.now().isoformat()
                    }
                    agent_research_tracker.collect_monitoring_data(target.get('id'), metrics)
                
                if activation.get('trigger_points', False):
                    from backend.services.agent_trigger_system import agent_trigger_system
                    agent_trigger_system.award_points('health_check', 'agent_user')
                
        except Exception as e:
            print(f"Error executing activation {activation.get('name')}: {e}")

    def self_activate_and_repair(self, reason: str = 'offline_or_error') -> Dict:
        """
        Self-activate critical automation and attempt lightweight repair tasks.
        Used when agents are offline or erroring.
        """
        actions = []
        try:
            # Ensure activation loop is running
            if not self.running:
                self.start()
                actions.append('activation_system_started')

            # Re-enable all auto activations
            for act in self.activations.get('auto_activations', []):
                if not act.get('enabled', True):
                    act['enabled'] = True
                    actions.append(f"enabled:{act.get('id')}")

            # Trigger immediate health + repair checks
            quick_fix_ids = ['auto_health_check', 'auto_system_repair', 'auto_database_check', 'auto_blueprint_check']
            index = {a.get('id'): a for a in self.activations.get('auto_activations', [])}
            for activation_id in quick_fix_ids:
                activation = index.get(activation_id)
                if activation:
                    self._execute_activation(activation)
                    self.activations['last_activations'][activation_id] = datetime.now().isoformat()
                    actions.append(f"executed:{activation_id}")

            self.save_activations()
            return {
                'success': True,
                'reason': reason,
                'actions': actions,
                'status': self.get_status(),
            }
        except Exception as e:
            return {
                'success': False,
                'reason': reason,
                'actions': actions,
                'error': str(e),
            }
    
    def add_activation(self, activation_data: Dict):
        """Add a new activation"""
        activation = {
            'id': activation_data.get('id', f"auto_{len(self.activations['auto_activations']) + 1}"),
            'name': activation_data.get('name', 'New Activation'),
            'function': activation_data.get('function', ''),
            'interval_minutes': activation_data.get('interval_minutes', 60),
            'enabled': activation_data.get('enabled', True),
            'trigger_points': activation_data.get('trigger_points', True)
        }
        
        self.activations['auto_activations'].append(activation)
        self.save_activations()
        
        return {
            'success': True,
            'activation': activation
        }
    
    def get_status(self) -> Dict:
        """Get activation system status"""
        enabled = [a for a in self.activations.get('auto_activations', []) if a.get('enabled', True)]
        
        return {
            'running': self.running,
            'total_activations': len(self.activations.get('auto_activations', [])),
            'enabled_activations': len(enabled),
            'activation_history_count': len(self.activations.get('activation_history', [])),
            'active_threads': len([t for t in self.activation_threads if t.is_alive()])
        }

# Global instance
agent_activation_system = AgentActivationSystem()
