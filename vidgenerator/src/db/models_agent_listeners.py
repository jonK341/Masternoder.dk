"""
Agent Event Listeners and Error Handlers Models
Licensed from Law Paragraph System
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func
import json

# Import existing db instance
from src.db.models import db


class AgentEventListener(db.Model):
    """
    Agent Event Listeners - Licensed from Law Paragraph System
    Tracks all event listeners attached to agent profiles
    """
    __tablename__ = 'agent_event_listeners'
    
    id = db.Column(db.String(36), primary_key=True)
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False, index=True)
    
    # Listener Information
    listener_name = db.Column(db.String(200), nullable=False)
    listener_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    listener_type = db.Column(db.String(50), nullable=False)  # task_completion, error_detection, point_update, etc.
    
    # Design and Model
    design_model = db.Column(db.String(200))  # Design pattern/model used
    design_version = db.Column(db.String(50), default='1.0.0')
    
    # Law Paragraph License
    law_paragraph_id = db.Column(db.String(100))  # Reference to law paragraph
    law_paragraph_category = db.Column(db.String(50))  # privacy, ip, rights, content, platform
    license_granted = db.Column(db.Boolean, default=True)
    license_date = db.Column(db.DateTime, default=func.now())
    license_terms = db.Column(db.Text)  # JSON: license terms and conditions
    
    # Listener Configuration
    event_pattern = db.Column(db.String(200))  # Event pattern to listen for
    callback_function = db.Column(db.String(200))  # Function to call
    priority = db.Column(db.Integer, default=5)  # 1-10, higher = more important
    is_active = db.Column(db.Boolean, default=True)
    
    # Statistics
    events_handled = db.Column(db.Integer, default=0)
    last_event_time = db.Column(db.DateTime)
    success_count = db.Column(db.Integer, default=0)
    failure_count = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'listener_name': self.listener_name,
            'listener_id': self.listener_id,
            'listener_type': self.listener_type,
            'design_model': self.design_model,
            'design_version': self.design_version,
            'law_paragraph_id': self.law_paragraph_id,
            'law_paragraph_category': self.law_paragraph_category,
            'license_granted': self.license_granted,
            'license_date': self.license_date.isoformat() if self.license_date else None,
            'license_terms': json.loads(self.license_terms) if self.license_terms else {},
            'event_pattern': self.event_pattern,
            'callback_function': self.callback_function,
            'priority': self.priority,
            'is_active': self.is_active,
            'events_handled': self.events_handled,
            'last_event_time': self.last_event_time.isoformat() if self.last_event_time else None,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class AgentErrorHandler(db.Model):
    """
    Agent Error Handlers - Licensed from Law Paragraph System
    Tracks all error handlers attached to agent profiles
    """
    __tablename__ = 'agent_error_handlers'
    
    id = db.Column(db.String(36), primary_key=True)
    agent_id = db.Column(db.String(36), db.ForeignKey('agents.id'), nullable=False, index=True)
    
    # Handler Information
    handler_name = db.Column(db.String(200), nullable=False)
    handler_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    handler_type = db.Column(db.String(50), nullable=False)  # exception_handler, validation_handler, recovery_handler, etc.
    
    # Design and Model
    design_model = db.Column(db.String(200))  # Design pattern/model used
    design_version = db.Column(db.String(50), default='1.0.0')
    
    # Law Paragraph License
    law_paragraph_id = db.Column(db.String(100))  # Reference to law paragraph
    law_paragraph_category = db.Column(db.String(50))  # privacy, ip, rights, content, platform
    license_granted = db.Column(db.Boolean, default=True)
    license_date = db.Column(db.DateTime, default=func.now())
    license_terms = db.Column(db.Text)  # JSON: license terms and conditions
    
    # Handler Configuration
    error_pattern = db.Column(db.String(200))  # Error pattern to handle
    error_types = db.Column(db.Text)  # JSON: list of error types
    recovery_strategy = db.Column(db.String(200))  # Recovery strategy
    priority = db.Column(db.Integer, default=5)  # 1-10, higher = more important
    is_active = db.Column(db.Boolean, default=True)
    
    # Statistics
    errors_handled = db.Column(db.Integer, default=0)
    last_error_time = db.Column(db.DateTime)
    recovery_success_count = db.Column(db.Integer, default=0)
    recovery_failure_count = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'handler_name': self.handler_name,
            'handler_id': self.handler_id,
            'handler_type': self.handler_type,
            'design_model': self.design_model,
            'design_version': self.design_version,
            'law_paragraph_id': self.law_paragraph_id,
            'law_paragraph_category': self.law_paragraph_category,
            'license_granted': self.license_granted,
            'license_date': self.license_date.isoformat() if self.license_date else None,
            'license_terms': json.loads(self.license_terms) if self.license_terms else {},
            'error_pattern': self.error_pattern,
            'error_types': json.loads(self.error_types) if self.error_types else [],
            'recovery_strategy': self.recovery_strategy,
            'priority': self.priority,
            'is_active': self.is_active,
            'errors_handled': self.errors_handled,
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'recovery_success_count': self.recovery_success_count,
            'recovery_failure_count': self.recovery_failure_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

