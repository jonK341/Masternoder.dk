"""
Debugging Database Service
Comprehensive database access for debugging system
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import text
from src.db.models import db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class DebuggingDatabase:
    """Comprehensive debugging database service"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure all debugging tables exist"""
        tables = [
            ('debug_sessions', """
                CREATE TABLE debug_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(200) UNIQUE NOT NULL,
                    profile_id VARCHAR(200),
                    user_id VARCHAR(100),
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER,
                    actions_count INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'active',
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ('debug_actions', """
                CREATE TABLE debug_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id VARCHAR(200) UNIQUE NOT NULL,
                    session_id VARCHAR(200),
                    profile_id VARCHAR(200),
                    action_type VARCHAR(100) NOT NULL,
                    action_name VARCHAR(200),
                    target_tab VARCHAR(100),
                    target_element VARCHAR(200),
                    result TEXT,
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ('debug_errors', """
                CREATE TABLE debug_errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id VARCHAR(200) UNIQUE NOT NULL,
                    session_id VARCHAR(200),
                    profile_id VARCHAR(200),
                    error_type VARCHAR(100),
                    error_message TEXT,
                    error_stack TEXT,
                    file_path VARCHAR(500),
                    line_number INTEGER,
                    severity VARCHAR(50) DEFAULT 'error',
                    resolved BOOLEAN DEFAULT 0,
                    resolved_at TIMESTAMP,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """),
            ('debug_performance', """
                CREATE TABLE debug_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    performance_id VARCHAR(200) UNIQUE NOT NULL,
                    session_id VARCHAR(200),
                    profile_id VARCHAR(200),
                    metric_name VARCHAR(100),
                    metric_value DECIMAL(15,2),
                    unit VARCHAR(50),
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        ]
        
        for table_name, create_sql in tables:
            try:
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                if table_name not in inspector.get_table_names():
                    db.session.execute(text(create_sql))
                    # Create indexes
                    db.session.execute(text(f"""
                        CREATE INDEX idx_{table_name}_session_id ON {table_name}(session_id)
                    """))
                    if 'profile_id' in create_sql:
                        db.session.execute(text(f"""
                            CREATE INDEX idx_{table_name}_profile_id ON {table_name}(profile_id)
                        """))
                    db.session.commit()
            except Exception as e:
                print(f"Error ensuring {table_name} table exists: {e}")
                db.session.rollback()
    
    def create_session(self, profile_id: Optional[str] = None, user_id: Optional[str] = None,
                      metadata: Optional[Dict] = None) -> Dict:
        """Create a new debug session"""
        session_id = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        try:
            db.session.execute(
                text("""
                    INSERT INTO debug_sessions
                    (session_id, profile_id, user_id, metadata, status)
                    VALUES (:session_id, :profile_id, :user_id, :metadata, 'active')
                """),
                {
                    "session_id": session_id,
                    "profile_id": profile_id,
                    "user_id": user_id,
                    "metadata": json.dumps(metadata or {})
                }
            )
            db.session.commit()
            
            return self.get_session(session_id)
        except Exception as e:
            print(f"Error creating session: {e}")
            db.session.rollback()
            return {}
    
    def end_session(self, session_id: str) -> bool:
        """End a debug session"""
        try:
            # Calculate duration
            session = self.get_session(session_id)
            if session:
                start_time = datetime.fromisoformat(session['start_time'])
                end_time = datetime.now()
                duration = int((end_time - start_time).total_seconds())
                
                db.session.execute(
                    text("""
                        UPDATE debug_sessions
                        SET end_time = CURRENT_TIMESTAMP,
                            duration_seconds = :duration,
                            status = 'completed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE session_id = :session_id
                    """),
                    {
                        "session_id": session_id,
                        "duration": duration
                    }
                )
                db.session.commit()
                return True
        except Exception as e:
            print(f"Error ending session: {e}")
            db.session.rollback()
        return False
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a debug session"""
        try:
            result = db.session.execute(
                text("SELECT * FROM debug_sessions WHERE session_id = :session_id"),
                {"session_id": session_id}
            ).fetchone()
            
            if result:
                return {
                    'id': result[0],
                    'session_id': result[1],
                    'profile_id': result[2],
                    'user_id': result[3],
                    'start_time': result[4],
                    'end_time': result[5],
                    'duration_seconds': result[6],
                    'actions_count': result[7],
                    'errors_count': result[8],
                    'status': result[9],
                    'metadata': json.loads(result[10]) if result[10] else {},
                    'created_at': result[11],
                    'updated_at': result[12]
                }
        except Exception as e:
            print(f"Error getting session: {e}")
        
        return None
    
    def log_action(self, session_id: str, action_type: str, action_name: str,
                   target_tab: Optional[str] = None, target_element: Optional[str] = None,
                   result: Optional[Dict] = None, success: bool = True,
                   error_message: Optional[str] = None, execution_time_ms: Optional[int] = None,
                   metadata: Optional[Dict] = None) -> Dict:
        """Log a debug action"""
        action_id = f"action_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Get profile_id from session
        session = self.get_session(session_id)
        profile_id = session.get('profile_id') if session else None
        
        try:
            db.session.execute(
                text("""
                    INSERT INTO debug_actions
                    (action_id, session_id, profile_id, action_type, action_name,
                     target_tab, target_element, result, success, error_message,
                     execution_time_ms, metadata)
                    VALUES (:action_id, :session_id, :profile_id, :action_type, :action_name,
                            :target_tab, :target_element, :result, :success, :error_message,
                            :execution_time_ms, :metadata)
                """),
                {
                    "action_id": action_id,
                    "session_id": session_id,
                    "profile_id": profile_id,
                    "action_type": action_type,
                    "action_name": action_name,
                    "target_tab": target_tab,
                    "target_element": target_element,
                    "result": json.dumps(result) if result else None,
                    "success": 1 if success else 0,
                    "error_message": error_message,
                    "execution_time_ms": execution_time_ms,
                    "metadata": json.dumps(metadata or {})
                }
            )
            
            # Update session action count
            db.session.execute(
                text("""
                    UPDATE debug_sessions
                    SET actions_count = actions_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = :session_id
                """),
                {"session_id": session_id}
            )
            
            db.session.commit()
            
            return {'action_id': action_id, 'success': True}
        except Exception as e:
            print(f"Error logging action: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def log_error(self, session_id: str, error_type: str, error_message: str,
                  error_stack: Optional[str] = None, file_path: Optional[str] = None,
                  line_number: Optional[int] = None, severity: str = 'error',
                  metadata: Optional[Dict] = None) -> Dict:
        """Log a debug error"""
        error_id = f"error_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Get profile_id from session
        session = self.get_session(session_id)
        profile_id = session.get('profile_id') if session else None
        
        try:
            db.session.execute(
                text("""
                    INSERT INTO debug_errors
                    (error_id, session_id, profile_id, error_type, error_message,
                     error_stack, file_path, line_number, severity, metadata)
                    VALUES (:error_id, :session_id, :profile_id, :error_type, :error_message,
                            :error_stack, :file_path, :line_number, :severity, :metadata)
                """),
                {
                    "error_id": error_id,
                    "session_id": session_id,
                    "profile_id": profile_id,
                    "error_type": error_type,
                    "error_message": error_message,
                    "error_stack": error_stack,
                    "file_path": file_path,
                    "line_number": line_number,
                    "severity": severity,
                    "metadata": json.dumps(metadata or {})
                }
            )
            
            # Update session error count
            db.session.execute(
                text("""
                    UPDATE debug_sessions
                    SET errors_count = errors_count + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE session_id = :session_id
                """),
                {"session_id": session_id}
            )
            
            db.session.commit()
            
            return {'error_id': error_id, 'success': True}
        except Exception as e:
            print(f"Error logging error: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def log_performance(self, session_id: str, metric_name: str, metric_value: float,
                       unit: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """Log performance metric"""
        performance_id = f"perf_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Get profile_id from session
        session = self.get_session(session_id)
        profile_id = session.get('profile_id') if session else None
        
        try:
            db.session.execute(
                text("""
                    INSERT INTO debug_performance
                    (performance_id, session_id, profile_id, metric_name, metric_value, unit, context)
                    VALUES (:performance_id, :session_id, :profile_id, :metric_name, :metric_value, :unit, :context)
                """),
                {
                    "performance_id": performance_id,
                    "session_id": session_id,
                    "profile_id": profile_id,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "unit": unit,
                    "context": json.dumps(context or {})
                }
            )
            db.session.commit()
            
            return {'performance_id': performance_id, 'success': True}
        except Exception as e:
            print(f"Error logging performance: {e}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_session_actions(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get actions for a session"""
        try:
            results = db.session.execute(
                text("""
                    SELECT * FROM debug_actions
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"session_id": session_id, "limit": limit}
            ).fetchall()
            
            actions = []
            for row in results:
                actions.append({
                    'id': row[0],
                    'action_id': row[1],
                    'session_id': row[2],
                    'profile_id': row[3],
                    'action_type': row[4],
                    'action_name': row[5],
                    'target_tab': row[6],
                    'target_element': row[7],
                    'result': json.loads(row[8]) if row[8] else {},
                    'success': bool(row[9]),
                    'error_message': row[10],
                    'execution_time_ms': row[11],
                    'metadata': json.loads(row[12]) if row[12] else {},
                    'created_at': row[13]
                })
            return actions
        except Exception as e:
            print(f"Error getting session actions: {e}")
            return []
    
    def get_session_errors(self, session_id: str, limit: int = 100) -> List[Dict]:
        """Get errors for a session"""
        try:
            results = db.session.execute(
                text("""
                    SELECT * FROM debug_errors
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"session_id": session_id, "limit": limit}
            ).fetchall()
            
            errors = []
            for row in results:
                errors.append({
                    'id': row[0],
                    'error_id': row[1],
                    'session_id': row[2],
                    'profile_id': row[3],
                    'error_type': row[4],
                    'error_message': row[5],
                    'error_stack': row[6],
                    'file_path': row[7],
                    'line_number': row[8],
                    'severity': row[9],
                    'resolved': bool(row[10]),
                    'resolved_at': row[11],
                    'metadata': json.loads(row[12]) if row[12] else {},
                    'created_at': row[13]
                })
            return errors
        except Exception as e:
            print(f"Error getting session errors: {e}")
            return []
    
    def get_debugging_stats(self) -> Dict:
        """Get comprehensive debugging statistics"""
        try:
            total_sessions = db.session.execute(
                text("SELECT COUNT(*) FROM debug_sessions")
            ).scalar()
            
            active_sessions = db.session.execute(
                text("SELECT COUNT(*) FROM debug_sessions WHERE status = 'active'")
            ).scalar()
            
            total_actions = db.session.execute(
                text("SELECT COUNT(*) FROM debug_actions")
            ).scalar()
            
            total_errors = db.session.execute(
                text("SELECT COUNT(*) FROM debug_errors WHERE resolved = 0")
            ).scalar()
            
            avg_duration = db.session.execute(
                text("SELECT AVG(duration_seconds) FROM debug_sessions WHERE duration_seconds IS NOT NULL")
            ).scalar() or 0
            
            return {
                'total_sessions': total_sessions,
                'active_sessions': active_sessions,
                'total_actions': total_actions,
                'total_errors': total_errors,
                'average_session_duration_seconds': round(avg_duration, 2)
            }
        except Exception as e:
            print(f"Error getting debugging stats: {e}")
            return {}


# Global instance
debugging_database = DebuggingDatabase()
