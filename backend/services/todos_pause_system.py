"""
Todos and Pause System
Task management with pause/resume functionality
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

try:
    from backend.services.skill_reward_system import skill_reward_system
    from backend.services.point_connection_system import PointConnectionSystem
    point_connection = PointConnectionSystem()
except ImportError:
    skill_reward_system = None
    point_connection = None


class TodosPauseSystem:
    """
    Todos and Pause System
    - Todo task management
    - Pause/resume functionality
    - Task tracking and completion
    - Integration with skill rewards
    """
    
    def __init__(self):
        self.user_todos = defaultdict(list)  # {user_id: [todo_data]}
        self.paused_todos = defaultdict(dict)  # {user_id: {todo_id: pause_data}}
        self.todo_history = defaultdict(list)  # {user_id: [history_data]}
    
    def create_todo(self, user_id: str, todo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new todo"""
        todo_id = str(uuid.uuid4())
        
        todo = {
            'todo_id': todo_id,
            'user_id': user_id,
            'title': todo_data.get('title', 'Untitled Todo'),
            'description': todo_data.get('description', ''),
            'priority': todo_data.get('priority', 'medium'),  # low, medium, high
            'category': todo_data.get('category', 'general'),
            'status': 'pending',  # pending, in_progress, paused, completed, cancelled
            'created_at': datetime.utcnow().isoformat(),
            'due_date': todo_data.get('due_date'),
            'estimated_time': todo_data.get('estimated_time', 0),  # minutes
            'tags': todo_data.get('tags', []),
            'metadata': todo_data.get('metadata', {})
        }
        
        self.user_todos[user_id].append(todo)
        
        return {
            'success': True,
            'todo_id': todo_id,
            'todo': todo
        }
    
    def start_todo(self, user_id: str, todo_id: str) -> Dict[str, Any]:
        """Start working on a todo"""
        todo = self._find_todo(user_id, todo_id)
        if not todo:
            return {'success': False, 'error': 'Todo not found'}
        
        if todo['status'] == 'completed':
            return {'success': False, 'error': 'Todo already completed'}
        
        todo['status'] = 'in_progress'
        todo['started_at'] = datetime.utcnow().isoformat()
        
        # Remove from paused if was paused
        if todo_id in self.paused_todos.get(user_id, {}):
            del self.paused_todos[user_id][todo_id]
        
        return {
            'success': True,
            'todo_id': todo_id,
            'status': 'in_progress',
            'started_at': todo['started_at']
        }
    
    def pause_todo(self, user_id: str, todo_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Pause a todo"""
        todo = self._find_todo(user_id, todo_id)
        if not todo:
            return {'success': False, 'error': 'Todo not found'}
        
        if todo['status'] != 'in_progress':
            return {'success': False, 'error': 'Todo is not in progress'}
        
        # Calculate time spent
        started_at = datetime.fromisoformat(todo.get('started_at', datetime.utcnow().isoformat()))
        time_spent = (datetime.utcnow() - started_at).total_seconds() / 60  # minutes
        
        pause_data = {
            'todo_id': todo_id,
            'paused_at': datetime.utcnow().isoformat(),
            'time_spent_before_pause': time_spent,
            'reason': reason,
            'resume_count': self.paused_todos[user_id].get(todo_id, {}).get('resume_count', 0)
        }
        
        self.paused_todos[user_id][todo_id] = pause_data
        todo['status'] = 'paused'
        todo['paused_at'] = pause_data['paused_at']
        
        return {
            'success': True,
            'todo_id': todo_id,
            'status': 'paused',
            'pause_data': pause_data
        }
    
    def resume_todo(self, user_id: str, todo_id: str) -> Dict[str, Any]:
        """Resume a paused todo"""
        todo = self._find_todo(user_id, todo_id)
        if not todo:
            return {'success': False, 'error': 'Todo not found'}
        
        if todo['status'] != 'paused':
            return {'success': False, 'error': 'Todo is not paused'}
        
        pause_data = self.paused_todos[user_id].get(todo_id, {})
        pause_data['resume_count'] = pause_data.get('resume_count', 0) + 1
        pause_data['resumed_at'] = datetime.utcnow().isoformat()
        
        todo['status'] = 'in_progress'
        todo['started_at'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'todo_id': todo_id,
            'status': 'in_progress',
            'pause_count': pause_data.get('resume_count', 0)
        }
    
    def complete_todo(self, user_id: str, todo_id: str) -> Dict[str, Any]:
        """Complete a todo"""
        todo = self._find_todo(user_id, todo_id)
        if not todo:
            return {'success': False, 'error': 'Todo not found'}
        
        if todo['status'] == 'completed':
            return {'success': False, 'error': 'Todo already completed'}
        
        # Calculate total time spent
        total_time = 0
        if todo.get('started_at'):
            started_at = datetime.fromisoformat(todo['started_at'])
            total_time = (datetime.utcnow() - started_at).total_seconds() / 60
        
        # Add paused time if was paused
        if todo_id in self.paused_todos.get(user_id, {}):
            pause_data = self.paused_todos[user_id][todo_id]
            total_time += pause_data.get('time_spent_before_pause', 0)
            del self.paused_todos[user_id][todo_id]
        
        todo['status'] = 'completed'
        todo['completed_at'] = datetime.utcnow().isoformat()
        todo['total_time_spent'] = total_time
        
        # Record in history
        self.todo_history[user_id].append({
            'todo_id': todo_id,
            'completed_at': todo['completed_at'],
            'time_spent': total_time
        })
        
        # Award skill reward for completion
        if skill_reward_system:
            try:
                skill_reward_system.record_completion(
                    user_id,
                    'todo',
                    todo_id,
                    {'title': todo['title'], 'time_spent': total_time}
                )
            except Exception as e:
                print(f"[TodosPause] Error awarding skill reward: {e}")
        
        return {
            'success': True,
            'todo_id': todo_id,
            'status': 'completed',
            'time_spent': total_time,
            'completed_at': todo['completed_at']
        }
    
    def get_user_todos(self, user_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Get user's todos"""
        todos = self.user_todos.get(user_id, [])
        
        if status:
            todos = [t for t in todos if t['status'] == status]
        
        # Sort by priority and created date
        todos.sort(key=lambda x: (0 if x['priority'] == 'high' else 1 if x['priority'] == 'medium' else 2, x['created_at']))
        
        return {
            'success': True,
            'user_id': user_id,
            'todos': todos,
            'total_todos': len(self.user_todos.get(user_id, [])),
            'pending': len([t for t in self.user_todos.get(user_id, []) if t['status'] == 'pending']),
            'in_progress': len([t for t in self.user_todos.get(user_id, []) if t['status'] == 'in_progress']),
            'paused': len([t for t in self.user_todos.get(user_id, []) if t['status'] == 'paused']),
            'completed': len([t for t in self.user_todos.get(user_id, []) if t['status'] == 'completed'])
        }
    
    def _find_todo(self, user_id: str, todo_id: str) -> Optional[Dict[str, Any]]:
        """Find a todo by ID"""
        todos = self.user_todos.get(user_id, [])
        for todo in todos:
            if todo['todo_id'] == todo_id:
                return todo
        return None
    
    def cancel_todo(self, user_id: str, todo_id: str) -> Dict[str, Any]:
        """Cancel a todo"""
        todo = self._find_todo(user_id, todo_id)
        if not todo:
            return {'success': False, 'error': 'Todo not found'}
        
        if todo['status'] == 'completed':
            return {'success': False, 'error': 'Cannot cancel completed todo'}
        
        todo['status'] = 'cancelled'
        todo['cancelled_at'] = datetime.utcnow().isoformat()
        
        # Remove from paused if was paused
        if todo_id in self.paused_todos.get(user_id, {}):
            del self.paused_todos[user_id][todo_id]
        
        return {
            'success': True,
            'todo_id': todo_id,
            'status': 'cancelled'
        }


# Global instance
todos_pause_system = TodosPauseSystem()

