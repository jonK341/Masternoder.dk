"""
Agent Task Database Helper
Handles database operations for agent tasks
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import text
from src.db.models import db


def create_agent_tasks_table():
    """Create agent_tasks table if it doesn't exist"""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'agent_tasks' not in inspector.get_table_names():
            db.session.execute(text("""
                CREATE TABLE agent_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id VARCHAR(200) UNIQUE NOT NULL,
                    agent_id VARCHAR(100) NOT NULL,
                    task_type VARCHAR(50) NOT NULL,
                    tab VARCHAR(50),
                    action VARCHAR(100),
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'pending',
                    priority VARCHAR(20) DEFAULT 'medium',
                    points_reward TEXT,
                    points_awarded TEXT,
                    result_data TEXT,
                    assigned_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.execute(text("""
                CREATE INDEX idx_agent_tasks_task_id ON agent_tasks(task_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_agent_tasks_agent_id ON agent_tasks(agent_id)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_agent_tasks_status ON agent_tasks(status)
            """))
            db.session.execute(text("""
                CREATE INDEX idx_agent_tasks_tab ON agent_tasks(tab)
            """))
            db.session.commit()
            return True
    except Exception as e:
        print(f"Error creating agent_tasks table: {e}")
        db.session.rollback()
        return False


def save_agent_task(task_data: Dict) -> bool:
    """Save or update an agent task"""
    try:
        create_agent_tasks_table()  # Ensure table exists
        
        task_id = task_data.get('task_id')
        if not task_id:
            return False
        
        db.session.execute(
            text("""
                INSERT OR REPLACE INTO agent_tasks
                (task_id, agent_id, task_type, tab, action, description, status, priority,
                 points_reward, points_awarded, result_data, assigned_at, completed_at,
                 updated_at)
                VALUES (:task_id, :agent_id, :task_type, :tab, :action, :description, :status, :priority,
                        :points_reward, :points_awarded, :result_data, :assigned_at, :completed_at,
                        CURRENT_TIMESTAMP)
            """),
            {
                "task_id": task_id,
                "agent_id": task_data.get('agent_id', 'agent_manager'),
                "task_type": task_data.get('task_type', 'debugger_task'),
                "tab": task_data.get('tab'),
                "action": task_data.get('action'),
                "description": task_data.get('description', ''),
                "status": task_data.get('status', 'pending'),
                "priority": task_data.get('priority', 'medium'),
                "points_reward": json.dumps(task_data.get('points_reward', {})),
                "points_awarded": json.dumps(task_data.get('points_awarded', {})),
                "result_data": json.dumps(task_data.get('result_data', {})),
                "assigned_at": task_data.get('assigned_at'),
                "completed_at": task_data.get('completed_at'),
            }
        )
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error saving agent task: {e}")
        db.session.rollback()
        return False


def get_agent_task(task_id: str) -> Optional[Dict]:
    """Get an agent task by task_id"""
    try:
        result = db.session.execute(
            text("SELECT * FROM agent_tasks WHERE task_id = :task_id"),
            {"task_id": task_id}
        ).fetchone()
        
        if result:
            return {
                'id': result[0],
                'task_id': result[1],
                'agent_id': result[2],
                'task_type': result[3],
                'tab': result[4],
                'action': result[5],
                'description': result[6],
                'status': result[7],
                'priority': result[8],
                'points_reward': json.loads(result[9]) if result[9] else {},
                'points_awarded': json.loads(result[10]) if result[10] else {},
                'result_data': json.loads(result[11]) if result[11] else {},
                'assigned_at': result[12],
                'completed_at': result[13],
                'created_at': result[14],
                'updated_at': result[15]
            }
        return None
    except Exception as e:
        print(f"Error getting agent task: {e}")
        return None


def get_agent_tasks(agent_id: Optional[str] = None, status: Optional[str] = None, 
                    tab: Optional[str] = None) -> List[Dict]:
    """Get agent tasks with optional filters"""
    try:
        query = "SELECT * FROM agent_tasks WHERE 1=1"
        params = {}
        
        if agent_id:
            query += " AND agent_id = :agent_id"
            params['agent_id'] = agent_id
        
        if status:
            query += " AND status = :status"
            params['status'] = status
        
        if tab:
            query += " AND tab = :tab"
            params['tab'] = tab
        
        query += " ORDER BY created_at DESC"
        
        results = db.session.execute(text(query), params).fetchall()
        
        tasks = []
        for result in results:
            tasks.append({
                'id': result[0],
                'task_id': result[1],
                'agent_id': result[2],
                'task_type': result[3],
                'tab': result[4],
                'action': result[5],
                'description': result[6],
                'status': result[7],
                'priority': result[8],
                'points_reward': json.loads(result[9]) if result[9] else {},
                'points_awarded': json.loads(result[10]) if result[10] else {},
                'result_data': json.loads(result[11]) if result[11] else {},
                'assigned_at': result[12],
                'completed_at': result[13],
                'created_at': result[14],
                'updated_at': result[15]
            })
        return tasks
    except Exception as e:
        print(f"Error getting agent tasks: {e}")
        return []


def mark_task_completed(task_id: str, points_awarded: Dict = None, result_data: Dict = None) -> bool:
    """Mark a task as completed"""
    try:
        update_data = {
            "task_id": task_id,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }
        
        if points_awarded:
            update_data["points_awarded"] = json.dumps(points_awarded)
        
        if result_data:
            update_data["result_data"] = json.dumps(result_data)
        
        db.session.execute(
            text("""
                UPDATE agent_tasks
                SET status = :status,
                    completed_at = :completed_at,
                    points_awarded = COALESCE(:points_awarded, points_awarded),
                    result_data = COALESCE(:result_data, result_data),
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = :task_id
            """),
            {
                "task_id": task_id,
                "status": "completed",
                "completed_at": update_data["completed_at"],
                "points_awarded": update_data.get("points_awarded"),
                "result_data": update_data.get("result_data")
            }
        )
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error marking task as completed: {e}")
        db.session.rollback()
        return False
