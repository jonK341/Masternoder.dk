"""
Content Category Models - Extending Documentary model with categories
Categories: underholdning (entertainment), porn, rettigheder (rights)
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func
import json

# Import existing db instance
from src.db.models import db

# Import Documentary model
from src.db.models import Documentary


class ContentCategory(db.Model):
    """Content categories for documentaries"""
    __tablename__ = 'content_categories'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name_da = db.Column(db.String(100))  # Danish name
    description = db.Column(db.Text)
    description_da = db.Column(db.Text)  # Danish description
    
    # Category metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    sort_order = db.Column(db.Integer, default=0, index=True)
    
    # Category statistics
    total_documentaries = db.Column(db.Integer, default=0)
    total_views = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Integer, default=0)  # seconds
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    # Note: Documentary.category_id foreign key is defined in Documentary model
    # documentaries = db.relationship('Documentary', backref='content_category', lazy=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'name_da': self.name_da,
            'description': self.description,
            'description_da': self.description_da,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'total_documentaries': self.total_documentaries,
            'total_views': self.total_views,
            'total_duration': self.total_duration,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CategoryStats(db.Model):
    """Statistics for each content category"""
    __tablename__ = 'category_stats'
    
    id = db.Column(db.String(36), primary_key=True)
    category_id = db.Column(db.String(36), db.ForeignKey('content_categories.id'), nullable=False, index=True)
    user_id = db.Column(db.String(100), nullable=True, index=True)  # Optional: per-user stats
    
    # Generation stats
    documentaries_created = db.Column(db.Integer, default=0)
    documentaries_completed = db.Column(db.Integer, default=0)
    documentaries_failed = db.Column(db.Integer, default=0)
    
    # Viewing stats
    total_views = db.Column(db.Integer, default=0)
    total_watch_time = db.Column(db.Integer, default=0)  # seconds
    average_watch_time = db.Column(db.Float, default=0.0)  # seconds
    
    # Engagement stats
    total_shares = db.Column(db.Integer, default=0)
    total_likes = db.Column(db.Integer, default=0)
    total_comments = db.Column(db.Integer, default=0)
    
    # Quality stats
    average_quality = db.Column(db.Float, default=0.0)
    high_quality_count = db.Column(db.Integer, default=0)  # quality >= 0.8
    
    # Time period (for aggregated stats)
    period_start = db.Column(db.DateTime, nullable=True)  # For daily/weekly/monthly stats
    period_end = db.Column(db.DateTime, nullable=True)
    period_type = db.Column(db.String(20), default='all')  # all, daily, weekly, monthly
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    category = db.relationship('ContentCategory', backref='statistics')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'category_id': self.category_id,
            'user_id': self.user_id,
            'documentaries_created': self.documentaries_created,
            'documentaries_completed': self.documentaries_completed,
            'documentaries_failed': self.documentaries_failed,
            'total_views': self.total_views,
            'total_watch_time': self.total_watch_time,
            'average_watch_time': self.average_watch_time,
            'total_shares': self.total_shares,
            'total_likes': self.total_likes,
            'total_comments': self.total_comments,
            'average_quality': self.average_quality,
            'high_quality_count': self.high_quality_count,
            'period_type': self.period_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


# Add category_id to Documentary model (migration)
# This will be done via ALTER TABLE in a migration script

