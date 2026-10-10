"""
Enhanced Database Models - Valuable Content Structure
Redesigned to contain more valuable content than just small videos and test items
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()


class ValuableContent(db.Model):
    """Enhanced content model for valuable content"""
    __tablename__ = 'valuable_content'
    
    id = db.Column(db.String(36), primary_key=True)
    content_type = db.Column(db.String(50), nullable=False, index=True)  # video, documentary, tutorial, battle_replay, etc.
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    
    # Content paths
    primary_path = db.Column(db.String(500))  # Main content file
    thumbnail_path = db.Column(db.String(500))
    preview_path = db.Column(db.String(500))
    
    # Quality and value metrics
    quality_score = db.Column(db.Float, default=0.0, index=True)
    value_score = db.Column(db.Float, default=0.0, index=True)  # How valuable this content is
    engagement_score = db.Column(db.Float, default=0.0, index=True)
    
    # Content metadata
    duration = db.Column(db.Integer)  # Duration in seconds
    file_size = db.Column(db.BigInteger)  # File size in bytes
    resolution = db.Column(db.String(20))  # e.g., "1920x1080"
    
    # Content category and tags
    category = db.Column(db.String(100), index=True)
    tags = db.Column(db.JSON)  # Array of tags
    theme = db.Column(db.String(50), index=True)
    
    # Creator information
    creator_id = db.Column(db.String(100), index=True)
    creator_name = db.Column(db.String(200))
    
    # Engagement metrics
    view_count = db.Column(db.Integer, default=0, index=True)
    like_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    
    # Status
    status = db.Column(db.String(20), default='active', index=True)  # active, archived, deleted
    is_test_content = db.Column(db.Boolean, default=False, index=True)  # Mark test content for cleanup
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    published_at = db.Column(db.DateTime, index=True)
    
    # Additional metadata
    metadata = db.Column(JSON)  # Flexible JSON for additional data
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_type': self.content_type,
            'title': self.title,
            'description': self.description,
            'primary_path': self.primary_path,
            'thumbnail_path': self.thumbnail_path,
            'preview_path': self.preview_path,
            'quality_score': self.quality_score,
            'value_score': self.value_score,
            'engagement_score': self.engagement_score,
            'duration': self.duration,
            'file_size': self.file_size,
            'resolution': self.resolution,
            'category': self.category,
            'tags': self.tags,
            'theme': self.theme,
            'creator_id': self.creator_id,
            'creator_name': self.creator_name,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'share_count': self.share_count,
            'comment_count': self.comment_count,
            'status': self.status,
            'is_test_content': self.is_test_content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'metadata': self.metadata
        }


class ContentCollection(db.Model):
    """Collections of valuable content"""
    __tablename__ = 'content_collections'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    collection_type = db.Column(db.String(50), index=True)  # playlist, series, battle_replay, tutorial_series
    
    # Collection metadata
    content_ids = db.Column(db.JSON)  # Array of content IDs
    cover_image = db.Column(db.String(500))
    
    # Statistics
    total_items = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Integer, default=0)  # Total duration in seconds
    total_views = db.Column(db.Integer, default=0)
    
    # Creator
    creator_id = db.Column(db.String(100), index=True)
    
    # Status
    status = db.Column(db.String(20), default='active', index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'collection_type': self.collection_type,
            'content_ids': self.content_ids,
            'cover_image': self.cover_image,
            'total_items': self.total_items,
            'total_duration': self.total_duration,
            'total_views': self.total_views,
            'creator_id': self.creator_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ContentEngagement(db.Model):
    """Track engagement with valuable content"""
    __tablename__ = 'content_engagement'
    
    id = db.Column(db.String(36), primary_key=True)
    content_id = db.Column(db.String(36), nullable=False, index=True)
    user_id = db.Column(db.String(100), index=True)
    
    # Engagement type
    engagement_type = db.Column(db.String(50), nullable=False, index=True)  # view, like, share, comment, download
    
    # Engagement data
    duration_watched = db.Column(db.Integer, default=0)  # Seconds watched
    completion_rate = db.Column(db.Float, default=0.0)  # 0.0-1.0
    engagement_data = db.Column(JSON)  # Additional engagement data
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'user_id': self.user_id,
            'engagement_type': self.engagement_type,
            'duration_watched': self.duration_watched,
            'completion_rate': self.completion_rate,
            'engagement_data': self.engagement_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

