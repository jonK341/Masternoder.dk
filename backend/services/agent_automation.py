"""
Agent Automation System
Automatic maintenance and autoplay for agents
"""
import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentAutomation:
    """Automated agent system with autoplay and maintenance"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.config_file = os.path.join(self.base_dir, 'logs', 'agent_automation', 'config.json')
        self.running = False
        self.threads = []
        self.tasks = []
        self.load_config()
    
    def load_config(self):
        """Load automation configuration"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = self._default_config()
        else:
            self.config = self._default_config()
        
        # Ensure enabled and autoplay are True
        self.config['enabled'] = True
        self.config['autoplay'] = True
        self.config['auto_fix_enabled'] = True
        self.save_config()
    
    def _default_config(self) -> Dict:
        """Default automation configuration"""
        return {
            'enabled': True,
            'autoplay': True,
            'maintenance_interval_minutes': 60,
            'scan_interval_minutes': 30,
            'health_check_interval_minutes': 15,
            'auto_fix_enabled': True,
            'tasks': [
                {
                    'name': 'health_check',
                    'enabled': True,
                    'interval_minutes': 15,
                    'priority': 'high'
                },
                {
                    'name': 'blueprint_check',
                    'enabled': True,
                    'interval_minutes': 60,
                    'priority': 'medium'
                },
                {
                    'name': 'database_check',
                    'enabled': True,
                    'interval_minutes': 120,
                    'priority': 'medium'
                },
                {
                    'name': 'missing_methods_scan',
                    'enabled': True,
                    'interval_minutes': 180,
                    'priority': 'low'
                }
            ]
        }
    
    def save_config(self):
        """Save automation configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def start(self):
        """Start automation system"""
        if self.running:
            return
        
        self.running = True
        
        # Start main automation loop
        main_thread = threading.Thread(target=self._automation_loop, daemon=True)
        main_thread.start()
        self.threads.append(main_thread)
        
        # Start task scheduler
        scheduler_thread = threading.Thread(target=self._task_scheduler, daemon=True)
        scheduler_thread.start()
        self.threads.append(scheduler_thread)
        
        # Start activation system
        try:
            from backend.services.agent_activation_system import agent_activation_system
            agent_activation_system.start()
        except Exception as e:
            print(f"Warning: Could not start activation system: {e}")
        
        print("[AgentAutomation] started")
    
    def stop(self):
        """Stop automation system"""
        self.running = False
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1)
        self.threads.clear()
        print("[AgentAutomation] stopped")
    
    def _automation_loop(self):
        """Main automation loop"""
        while self.running:
            try:
                if self.config.get('enabled', True):
                    self._run_maintenance_tasks()
                
                # Sleep for 1 minute
                time.sleep(60)
            except Exception as e:
                print(f"Error in automation loop: {e}")
                time.sleep(60)
    
    def _task_scheduler(self):
        """Task scheduler for scheduled tasks"""
        while self.running:
            try:
                if self.config.get('enabled', True):
                    self._execute_scheduled_tasks()
                
                # Check every minute
                time.sleep(60)
            except Exception as e:
                print(f"Error in task scheduler: {e}")
                time.sleep(60)
    
    def _run_maintenance_tasks(self):
        """Run maintenance tasks"""
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            
            # Run health check
            health = master_fix_agent_skills.skill_monitor_system_health()
            if health.get('health_score', 100) < 70:
                print(f"[WARN] System health low: {health.get('health_score')}%")
            
            # Run diagnostic if needed
            if health.get('health_score', 100) < 80:
                diagnostic = master_fix_agent_skills.skill_run_full_diagnostic()
                print(f"[INFO] Diagnostic completed: {diagnostic.get('health_score')}%")
            
        except Exception as e:
            print(f"Error running maintenance: {e}")
    
    def _execute_scheduled_tasks(self):
        """Execute scheduled tasks"""
        current_time = datetime.now()
        
        for task in self.config.get('tasks', []):
            if not task.get('enabled', True):
                continue
            
            task_name = task.get('name')
            interval = task.get('interval_minutes', 60)
            
            # Check if task should run
            last_run_key = f"{task_name}_last_run"
            last_run = self.config.get(last_run_key)
            
            if not last_run:
                # First run
                self._execute_task(task_name)
                self.config[last_run_key] = current_time.isoformat()
                self.save_config()
            else:
                try:
                    last_run_time = datetime.fromisoformat(last_run)
                    time_diff = current_time - last_run_time
                    
                    if time_diff >= timedelta(minutes=interval):
                        self._execute_task(task_name)
                        self.config[last_run_key] = current_time.isoformat()
                        self.save_config()
                except:
                    pass
    
    def _execute_task(self, task_name: str):
        """Execute a specific task"""
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            
            task_map = {
                'health_check': master_fix_agent_skills.skill_monitor_system_health,
                'blueprint_check': master_fix_agent_skills.skill_check_blueprints,
                'database_check': master_fix_agent_skills.skill_verify_database,
                'missing_methods_scan': master_fix_agent_skills.skill_scan_missing_methods,
                'file_integrity': master_fix_agent_skills.skill_check_file_integrity,
                'service_health': master_fix_agent_skills.skill_check_service_health,
                'performance_monitor': master_fix_agent_skills.skill_monitor_performance
            }
            
            task_func = task_map.get(task_name)
            if task_func:
                result = task_func()
                print(f"[OK] Task {task_name} completed: {result.get('success', False)}")
        except Exception as e:
            print(f"Error executing task {task_name}: {e}")
    
    def add_task(self, name: str, func: Callable, interval_minutes: int = 60, priority: str = 'medium'):
        """Add a custom task"""
        task = {
            'name': name,
            'enabled': True,
            'interval_minutes': interval_minutes,
            'priority': priority
        }
        
        if 'tasks' not in self.config:
            self.config['tasks'] = []
        
        # Remove existing task with same name
        self.config['tasks'] = [t for t in self.config['tasks'] if t.get('name') != name]
        
        # Add new task
        self.config['tasks'].append(task)
        self.save_config()
    
    def get_status(self) -> Dict:
        """Get automation status"""
        return {
            'running': self.running,
            'enabled': self.config.get('enabled', True),
            'autoplay': self.config.get('autoplay', True),
            'tasks_count': len(self.config.get('tasks', [])),
            'active_threads': len([t for t in self.threads if t.is_alive()]),
            'config': self.config
        }

# Global instance
agent_automation = AgentAutomation()
