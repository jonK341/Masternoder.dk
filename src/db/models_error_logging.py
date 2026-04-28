"""
Database Models for Error Logging
Stores all frontend and backend errors for analysis and debugging
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Index
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

# Import db from models
try:
    from src.db.models import db
    Base = db.Model
except ImportError:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()


class ErrorLog(Base):
    """Stores all application errors (frontend and backend)"""
    __tablename__ = 'error_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Error identification
    error_type = Column(String(50), nullable=False, index=True)  # 'javascript', 'api', 'network', 'database', etc.
    error_level = Column(String(20), nullable=False, index=True)  # 'error', 'warning', 'critical', 'info'
    error_code = Column(String(50), nullable=True, index=True)  # HTTP status, error code, etc.
    
    # Error details
    error_message = Column(Text, nullable=False)
    error_stack = Column(Text, nullable=True)  # Stack trace
    error_source = Column(String(200), nullable=True)  # File, URL, endpoint, etc.
    error_line = Column(Integer, nullable=True)  # Line number if available
    error_column = Column(Integer, nullable=True)  # Column number if available
    
    # Context information
    user_id = Column(String(100), nullable=True, index=True)  # User who encountered error
    session_id = Column(String(100), nullable=True, index=True)  # Session ID
    page_url = Column(String(500), nullable=True)  # Page where error occurred
    user_agent = Column(String(500), nullable=True)  # Browser info
    
    # Request/Response context (for API errors)
    request_method = Column(String(10), nullable=True)  # GET, POST, etc.
    request_url = Column(String(500), nullable=True)  # Full request URL
    request_headers = Column(JSON, nullable=True)  # Request headers
    request_body = Column(Text, nullable=True)  # Request body
    response_status = Column(Integer, nullable=True)  # HTTP status code
    response_body = Column(Text, nullable=True)  # Response body
    
    # Additional context
    context_data = Column(JSON, nullable=True)  # Additional context (variables, state, etc.)
    tags = Column(JSON, nullable=True)  # Tags for filtering (['api', 'points', 'battle'], etc.)
    
    # Error resolution
    is_resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)  # User/admin who resolved
    resolution_notes = Column(Text, nullable=True)
    
    # Error grouping (for similar errors)
    error_group = Column(String(100), nullable=True, index=True)  # Group similar errors
    occurrence_count = Column(Integer, default=1, nullable=False)  # How many times this error occurred
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_error_type_level', 'error_type', 'error_level'),
        Index('idx_user_error', 'user_id', 'error_type'),
        Index('idx_created_resolved', 'created_at', 'is_resolved'),
        Index('idx_error_group', 'error_group', 'created_at'),
        Index('idx_page_url', 'page_url', 'created_at'),
    )
    
    def to_dict(self):
        """Convert error log to dictionary"""
        return {
            'id': self.id,
            'error_type': self.error_type,
            'error_level': self.error_level,
            'error_code': self.error_code,
            'error_message': self.error_message,
            'error_stack': self.error_stack,
            'error_source': self.error_source,
            'error_line': self.error_line,
            'error_column': self.error_column,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'page_url': self.page_url,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_url': self.request_url,
            'response_status': self.response_status,
            'context_data': self.context_data,
            'tags': self.tags,
            'is_resolved': self.is_resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'error_group': self.error_group,
            'occurrence_count': self.occurrence_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ErrorSummary(Base):
    """Aggregated error statistics for quick analysis"""
    __tablename__ = 'error_summaries'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Summary period
    summary_date = Column(DateTime, nullable=False, index=True)  # Date for this summary
    summary_type = Column(String(20), nullable=False, index=True)  # 'daily', 'hourly', 'weekly'
    
    # Error counts by type
    total_errors = Column(Integer, default=0, nullable=False)
    critical_errors = Column(Integer, default=0, nullable=False)
    api_errors = Column(Integer, default=0, nullable=False)
    javascript_errors = Column(Integer, default=0, nullable=False)
    network_errors = Column(Integer, default=0, nullable=False)
    
    # Error counts by level
    error_count = Column(Integer, default=0, nullable=False)
    warning_count = Column(Integer, default=0, nullable=False)
    info_count = Column(Integer, default=0, nullable=False)
    
    # Top errors
    top_errors = Column(JSON, nullable=True)  # List of most common errors
    top_pages = Column(JSON, nullable=True)  # Pages with most errors
    top_users = Column(JSON, nullable=True)  # Users with most errors
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_summary_date_type', 'summary_date', 'summary_type'),
    )
