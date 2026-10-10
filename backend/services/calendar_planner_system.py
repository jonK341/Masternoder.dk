"""
Calendar Planner System - Planning and Schedule Calendar Tasks
Enhanced calendar with planning, scheduling, and task management
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    from backend.services.agent_system import AgentSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None
    AgentSystem = None


class CalendarPlannerSystem:
    """
    Calendar Planner System
    - Planning functions for calendar tasks
    - Schedule management
    - Task assignment and tracking
    - Integration with agents for XP/cash earning
    """
    
    def __init__(self):
        self.calendar_events = defaultdict(list)  # {user_id: [event_data]}
        self.scheduled_tasks = defaultdict(list)  # {user_id: [task_data]}
        self.task_plans = defaultdict(dict)  # {user_id: {plan_id: plan_data}}
        self.agent_calendar_tasks = defaultdict(list)  # {agent_id: [task_data]}
    
    def create_plan(self, user_id: str, plan_name: str, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new calendar plan"""
        plan_id = str(uuid.uuid4())
        
        plan = {
            'plan_id': plan_id,
            'user_id': user_id,
            'plan_name': plan_name,
            'created_at': datetime.utcnow().isoformat(),
            'tasks': plan_data.get('tasks', []),
            'schedule': plan_data.get('schedule', {}),
            'deadline': plan_data.get('deadline'),
            'priority': plan_data.get('priority', 'medium'),
            'status': 'active',
            'metadata': plan_data.get('metadata', {})
        }
        
        self.task_plans[user_id][plan_id] = plan
        
        return {
            'success': True,
            'plan_id': plan_id,
            'plan': plan
        }
    
    def schedule_task(self, user_id: str, task_data: Dict[str, Any], 
                     agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Schedule a task in the calendar"""
        task_id = str(uuid.uuid4())
        
        scheduled_time = task_data.get('scheduled_time')
        if isinstance(scheduled_time, str):
            scheduled_time = datetime.fromisoformat(scheduled_time)
        
        task = {
            'task_id': task_id,
            'user_id': user_id,
            'agent_id': agent_id,
            'task_name': task_data.get('task_name', 'Untitled Task'),
            'description': task_data.get('description', ''),
            'scheduled_time': scheduled_time.isoformat() if scheduled_time else datetime.utcnow().isoformat(),
            'duration': task_data.get('duration', 60),  # minutes
            'priority': task_data.get('priority', 'medium'),
            'task_type': task_data.get('task_type', 'general'),
            'status': 'scheduled',
            'xp_reward': task_data.get('xp_reward', 0),
            'cash_reward': task_data.get('cash_reward', 0),
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.scheduled_tasks[user_id].append(task)
        
        # If agent_id provided, add to agent calendar
        if agent_id:
            self.agent_calendar_tasks[agent_id].append(task)
        
        return {
            'success': True,
            'task_id': task_id,
            'task': task
        }
    
    def complete_scheduled_task(self, user_id: str, task_id: str, 
                               agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Complete a scheduled task and award XP/cash"""
        # Find task
        task = None
        task_index = None
        
        for i, t in enumerate(self.scheduled_tasks.get(user_id, [])):
            if t['task_id'] == task_id:
                task = t
                task_index = i
                break
        
        if not task:
            return {'success': False, 'error': 'Task not found'}
        
        if task.get('status') == 'completed':
            return {'success': False, 'error': 'Task already completed'}
        
        # Mark as completed
        task['status'] = 'completed'
        task['completed_at'] = datetime.utcnow().isoformat()
        
        # Award XP and cash
        xp_reward = task.get('xp_reward', 0)
        cash_reward = task.get('cash_reward', 0)
        
        if point_connection:
            try:
                if xp_reward > 0:
                    point_connection.ensure_point_counting(
                        user_id,
                        'xp',
                        xp_reward,
                        'calendar_planner_system'
                    )
                if cash_reward > 0:
                    point_connection.ensure_point_counting(
                        user_id,
                        'coins',
                        cash_reward,
                        'calendar_planner_system'
                    )
            except Exception as e:
                print(f"[CalendarPlanner] Error awarding rewards: {e}")
        
        # If agent task, award to agent
        if agent_id and AgentSystem:
            try:
                agent_system = AgentSystem()
                # Award agent XP/cash (would need agent system methods)
            except Exception as e:
                print(f"[CalendarPlanner] Error awarding agent rewards: {e}")
        
        return {
            'success': True,
            'task_id': task_id,
            'xp_awarded': xp_reward,
            'cash_awarded': cash_reward,
            'completed_at': task['completed_at']
        }
    
    def get_calendar_events(self, user_id: str, start_date: Optional[datetime] = None, 
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get calendar events for a date range"""
        if start_date is None:
            start_date = datetime.utcnow().date()
        if end_date is None:
            end_date = start_date + timedelta(days=30)
        
        # Get scheduled tasks
        tasks = self.scheduled_tasks.get(user_id, [])
        
        # Filter by date range
        filtered_tasks = []
        for task in tasks:
            task_date = datetime.fromisoformat(task['scheduled_time']).date()
            if start_date <= task_date <= end_date:
                filtered_tasks.append(task)
        
        # Sort by scheduled time
        filtered_tasks.sort(key=lambda x: x['scheduled_time'])
        
        return {
            'success': True,
            'user_id': user_id,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'events': filtered_tasks,
            'total_events': len(filtered_tasks)
        }
    
    def get_agent_calendar_tasks(self, agent_id: str) -> Dict[str, Any]:
        """Get calendar tasks for an agent"""
        tasks = self.agent_calendar_tasks.get(agent_id, [])
        
        # Filter active tasks
        active_tasks = [t for t in tasks if t.get('status') != 'completed']
        
        return {
            'success': True,
            'agent_id': agent_id,
            'tasks': active_tasks,
            'total_tasks': len(tasks),
            'active_tasks': len(active_tasks)
        }
    
    def create_recurring_task(self, user_id: str, task_data: Dict[str, Any], 
                            recurrence: Dict[str, Any]) -> Dict[str, Any]:
        """Create a recurring task"""
        recurrence_type = recurrence.get('type', 'daily')  # daily, weekly, monthly
        recurrence_count = recurrence.get('count', 1)
        start_date = datetime.fromisoformat(recurrence.get('start_date', datetime.utcnow().isoformat()))
        
        created_tasks = []
        
        for i in range(recurrence_count):
            if recurrence_type == 'daily':
                scheduled_time = start_date + timedelta(days=i)
            elif recurrence_type == 'weekly':
                scheduled_time = start_date + timedelta(weeks=i)
            elif recurrence_type == 'monthly':
                scheduled_time = start_date + timedelta(days=30*i)
            else:
                scheduled_time = start_date + timedelta(days=i)
            
            task_data_copy = task_data.copy()
            task_data_copy['scheduled_time'] = scheduled_time.isoformat()
            
            result = self.schedule_task(user_id, task_data_copy)
            if result.get('success'):
                created_tasks.append(result['task_id'])
        
        return {
            'success': True,
            'tasks_created': len(created_tasks),
            'task_ids': created_tasks,
            'recurrence_type': recurrence_type
        }


# Global instance
calendar_planner_system = CalendarPlannerSystem()

