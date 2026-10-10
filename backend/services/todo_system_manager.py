"""
TODO System Manager
Manages and tracks all TODO items across the system
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum
import json
import os

class TodoPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"

class TodoSystemManager:
    """Manages TODO items across the entire system"""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'todos'
        )
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.todos = {}  # todo_id -> todo_data
        self.categories = {
            'integration': [],
            'testing': [],
            'features': [],
            'enhancements': [],
            'bug_fixes': [],
            'documentation': []
        }
    
    def create_todo(self, title: str, description: str = "", 
                   priority: TodoPriority = TodoPriority.MEDIUM,
                   category: str = "features",
                   dependencies: List[str] = None,
                   estimated_hours: float = None) -> str:
        """Create a new TODO item"""
        import uuid
        todo_id = str(uuid.uuid4())
        
        todo = {
            'id': todo_id,
            'title': title,
            'description': description,
            'priority': priority.value,
            'category': category,
            'status': TodoStatus.PENDING.value,
            'dependencies': dependencies or [],
            'estimated_hours': estimated_hours,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'completed_at': None,
            'assigned_to': None,
            'tags': [],
            'progress': 0
        }
        
        self.todos[todo_id] = todo
        
        # Add to category
        if category in self.categories:
            self.categories[category].append(todo_id)
        
        self._save_todos()
        
        return todo_id
    
    def update_todo(self, todo_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update TODO item"""
        if todo_id not in self.todos:
            return {'success': False, 'error': 'TODO not found'}
        
        todo = self.todos[todo_id]
        todo.update(updates)
        todo['updated_at'] = datetime.utcnow().isoformat()
        
        if 'status' in updates and updates['status'] == TodoStatus.COMPLETED.value:
            todo['completed_at'] = datetime.utcnow().isoformat()
            todo['progress'] = 100
        
        self._save_todos()
        
        return {'success': True, 'todo': todo}
    
    def complete_todo(self, todo_id: str) -> Dict[str, Any]:
        """Mark TODO as completed"""
        return self.update_todo(todo_id, {
            'status': TodoStatus.COMPLETED.value,
            'progress': 100
        })
    
    def start_todo(self, todo_id: str) -> Dict[str, Any]:
        """Start working on TODO"""
        return self.update_todo(todo_id, {
            'status': TodoStatus.IN_PROGRESS.value
        })
    
    def get_todos(self, status: TodoStatus = None, 
                 priority: TodoPriority = None,
                 category: str = None) -> List[Dict[str, Any]]:
        """Get TODOs with filters"""
        todos = list(self.todos.values())
        
        if status:
            todos = [t for t in todos if t['status'] == status.value]
        
        if priority:
            todos = [t for t in todos if t['priority'] == priority.value]
        
        if category:
            todos = [t for t in todos if t['category'] == category]
        
        # Sort by priority and created date
        priority_order = {
            TodoPriority.CRITICAL.value: 0,
            TodoPriority.HIGH.value: 1,
            TodoPriority.MEDIUM.value: 2,
            TodoPriority.LOW.value: 3
        }
        
        todos.sort(key=lambda x: (
            priority_order.get(x['priority'], 99),
            x['created_at']
        ))
        
        return todos
    
    def get_todo_statistics(self) -> Dict[str, Any]:
        """Get TODO statistics"""
        total = len(self.todos)
        
        by_status = {}
        for status in TodoStatus:
            by_status[status.value] = len([
                t for t in self.todos.values()
                if t['status'] == status.value
            ])
        
        by_priority = {}
        for priority in TodoPriority:
            by_priority[priority.value] = len([
                t for t in self.todos.values()
                if t['priority'] == priority.value
            ])
        
        by_category = {}
        for category in self.categories:
            by_category[category] = len([
                t for t in self.todos.values()
                if t['category'] == category
            ])
        
        completed = by_status.get(TodoStatus.COMPLETED.value, 0)
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'by_status': by_status,
            'by_priority': by_priority,
            'by_category': by_category,
            'completion_rate': round(completion_rate, 2),
            'pending': by_status.get(TodoStatus.PENDING.value, 0),
            'in_progress': by_status.get(TodoStatus.IN_PROGRESS.value, 0),
            'completed': completed
        }
    
    def _save_todos(self):
        """Save TODOs to file"""
        try:
            file_path = os.path.join(self.storage_path, 'todos.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'todos': self.todos,
                    'categories': self.categories,
                    'updated_at': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving TODOs: {e}")
    
    def _load_todos(self):
        """Load TODOs from file"""
        try:
            file_path = os.path.join(self.storage_path, 'todos.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.todos = data.get('todos', {})
                    self.categories = data.get('categories', self.categories)
        except Exception as e:
            print(f"Error loading TODOs: {e}")
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'todos'
        )
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.todos = {}
        self.categories = {
            'integration': [],
            'testing': [],
            'features': [],
            'enhancements': [],
            'bug_fixes': [],
            'documentation': []
        }
        self._load_todos()

# Global instance
todo_system_manager = TodoSystemManager()

