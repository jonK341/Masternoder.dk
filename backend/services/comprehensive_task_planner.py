"""
Comprehensive Task Planner
Plans and schedules tasks with dependencies and priorities
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

class TaskPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class ComprehensiveTaskPlanner:
    """Comprehensive task planning and scheduling system"""
    
    def __init__(self):
        self.tasks = {}  # task_id -> task_data
        self.schedules = {}  # schedule_id -> schedule_data
        self.dependencies = {}  # task_id -> [dependent_task_ids]
        self.blockers = {}  # task_id -> [blocking_task_ids]
    
    def create_task(self, title: str, description: str = "",
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   estimated_duration: timedelta = None,
                   dependencies: List[str] = None,
                   assignee: str = None) -> str:
        """Create a new task"""
        task_id = str(uuid.uuid4())
        
        task = {
            'id': task_id,
            'title': title,
            'description': description,
            'priority': priority.value,
            'status': TaskStatus.PLANNED.value,
            'estimated_duration': estimated_duration.total_seconds() if estimated_duration else None,
            'dependencies': dependencies or [],
            'assignee': assignee,
            'created_at': datetime.utcnow().isoformat(),
            'scheduled_start': None,
            'scheduled_end': None,
            'actual_start': None,
            'actual_end': None,
            'progress': 0,
            'tags': []
        }
        
        self.tasks[task_id] = task
        
        # Update dependencies
        if dependencies:
            for dep_id in dependencies:
                if dep_id not in self.blockers:
                    self.blockers[dep_id] = []
                self.blockers[dep_id].append(task_id)
        
        return task_id
    
    def schedule_task(self, task_id: str, start_time: datetime, 
                     end_time: datetime = None) -> Dict[str, Any]:
        """Schedule a task"""
        if task_id not in self.tasks:
            return {'success': False, 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        # Check dependencies
        for dep_id in task.get('dependencies', []):
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task['status'] != TaskStatus.COMPLETED.value:
                return {
                    'success': False,
                    'error': f'Dependency {dep_id} not completed'
                }
        
        # Schedule task
        task['scheduled_start'] = start_time.isoformat()
        if end_time:
            task['scheduled_end'] = end_time.isoformat()
        elif task.get('estimated_duration'):
            duration = timedelta(seconds=task['estimated_duration'])
            task['scheduled_end'] = (start_time + duration).isoformat()
        
        task['status'] = TaskStatus.SCHEDULED.value
        
        return {'success': True, 'task': task}
    
    def start_task(self, task_id: str) -> Dict[str, Any]:
        """Start working on a task"""
        if task_id not in self.tasks:
            return {'success': False, 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        # Check if dependencies are met
        for dep_id in task.get('dependencies', []):
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task['status'] != TaskStatus.COMPLETED.value:
                task['status'] = TaskStatus.BLOCKED.value
                return {
                    'success': False,
                    'error': f'Blocked by dependency {dep_id}',
                    'task': task
                }
        
        task['status'] = TaskStatus.IN_PROGRESS.value
        task['actual_start'] = datetime.utcnow().isoformat()
        task['progress'] = 0
        
        return {'success': True, 'task': task}
    
    def complete_task(self, task_id: str) -> Dict[str, Any]:
        """Complete a task"""
        if task_id not in self.tasks:
            return {'success': False, 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        task['status'] = TaskStatus.COMPLETED.value
        task['actual_end'] = datetime.utcnow().isoformat()
        task['progress'] = 100
        
        # Unblock dependent tasks
        dependent_tasks = self.blockers.get(task_id, [])
        for dep_task_id in dependent_tasks:
            dep_task = self.tasks.get(dep_task_id)
            if dep_task and dep_task['status'] == TaskStatus.BLOCKED.value:
                # Check if all dependencies are now met
                all_deps_met = all(
                    self.tasks.get(dep_id, {}).get('status') == TaskStatus.COMPLETED.value
                    for dep_id in dep_task.get('dependencies', [])
                )
                if all_deps_met:
                    dep_task['status'] = TaskStatus.PLANNED.value
        
        return {'success': True, 'task': task}
    
    def get_task_plan(self, task_id: str) -> Dict[str, Any]:
        """Get comprehensive task plan"""
        if task_id not in self.tasks:
            return {'success': False, 'error': 'Task not found'}
        
        task = self.tasks[task_id]
        
        # Get dependencies
        dependencies = []
        for dep_id in task.get('dependencies', []):
            dep_task = self.tasks.get(dep_id)
            if dep_task:
                dependencies.append(dep_task)
        
        # Get blockers
        blockers = []
        for blocker_id in self.blockers.get(task_id, []):
            blocker_task = self.tasks.get(blocker_id)
            if blocker_task:
                blockers.append(blocker_task)
        
        return {
            'success': True,
            'task': task,
            'dependencies': dependencies,
            'blockers': blockers,
            'can_start': all(
                dep.get('status') == TaskStatus.COMPLETED.value
                for dep in dependencies
            )
        }
    
    def get_schedule(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get schedule for date range"""
        scheduled_tasks = [
            task for task in self.tasks.values()
            if task.get('scheduled_start') and
            datetime.fromisoformat(task['scheduled_start']) >= start_date and
            datetime.fromisoformat(task['scheduled_start']) <= end_date
        ]
        
        scheduled_tasks.sort(key=lambda x: x.get('scheduled_start', ''))
        
        return {
            'success': True,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'tasks': scheduled_tasks,
            'count': len(scheduled_tasks)
        }

# Global instance
comprehensive_task_planner = ComprehensiveTaskPlanner()

