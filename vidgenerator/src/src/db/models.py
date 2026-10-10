"""Database models for documentaries and viewer data"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from typing import Optional
from sqlalchemy.sql import func

db = SQLAlchemy()


class Documentary(db.Model):
    """Main documentary model"""
    __tablename__ = 'documentaries'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)  # Indexed for search
    prompt = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    video_path = db.Column(db.String(500))
    thumbnail_path = db.Column(db.String(500))
    duration = db.Column(db.Integer)  # Duration in seconds
    
    # Status - indexed for filtering
    status = db.Column(db.String(20), default='pending', index=True)  # pending, generating, completed, failed
    progress = db.Column(db.Integer, default=0)  # 0-100
    
    # Metadata - indexed for sorting
    created_at = db.Column(db.DateTime, default=func.now(), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now(), nullable=True, index=True)
    completed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Relationships
    clips = db.relationship('MovieClip', backref='documentary', lazy=True, cascade='all, delete-orphan')
    viewer_sessions = db.relationship('ViewerSession', backref='documentary', lazy=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'prompt': self.prompt,
            'description': self.description,
            'video_path': self.video_path,
            'thumbnail_path': self.thumbnail_path,
            'duration': self.duration,
            'status': self.status,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


class MovieClip(db.Model):
    """5-minute movie clips for embedding"""
    __tablename__ = 'movie_clips'
    
    id = db.Column(db.String(36), primary_key=True)
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'), nullable=False, index=True)  # Indexed for joins
    
    title = db.Column(db.String(200))
    clip_path = db.Column(db.String(500), nullable=False)  # Combined video path (legacy)
    video_path = db.Column(db.String(500))  # Separated video-only path
    audio_path = db.Column(db.String(500))  # Separated audio-only path
    thumbnail_path = db.Column(db.String(500))
    duration = db.Column(db.Integer)  # Duration in seconds (typically 300 for 5 minutes)
    
    # Quality metrics
    quality_score = db.Column(db.Float, default=0.0)  # Quality score 0.0-1.0
    order_index = db.Column(db.Integer, default=0)  # Order in documentary
    
    segment_start = db.Column(db.Integer, default=0)  # Start time in documentary
    segment_end = db.Column(db.Integer)  # End time in documentary
    
    # Metadata - indexed for sorting
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    clip_metadata = db.Column(db.JSON)  # Additional metadata (JSON) - renamed from 'metadata' (reserved)
    
    # Relationships
    viewer_sessions = db.relationship('ViewerSession', backref='clip', lazy=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'documentary_id': self.documentary_id,
            'title': self.title,
            'clip_path': self.clip_path,
            'video_path': self.video_path,
            'audio_path': self.audio_path,
            'thumbnail_path': self.thumbnail_path,
            'duration': self.duration,
            'quality_score': self.quality_score,
            'order_index': self.order_index,
            'segment_start': self.segment_start,
            'segment_end': self.segment_end,
            'metadata': self.clip_metadata,  # Map clip_metadata to 'metadata' in dict
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ViewerSession(db.Model):
    """Viewer session tracking for data collection"""
    __tablename__ = 'viewer_sessions'
    
    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    viewer_id = db.Column(db.String(100), index=True)  # Optional for anonymous tracking
    
    # Content references
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'))
    clip_id = db.Column(db.String(36), db.ForeignKey('movie_clips.id'))
    
    # Viewing data
    start_time = db.Column(db.DateTime, default=func.now())
    end_time = db.Column(db.DateTime, nullable=True)
    watch_time = db.Column(db.Integer, default=0)  # Total watch time in seconds
    completion_rate = db.Column(db.Float, default=0.0)  # 0.0-1.0
    
    # Device information
    device_type = db.Column(db.String(50))  # desktop, mobile, tablet
    browser = db.Column(db.String(100))
    location = db.Column(db.String(200))  # Country, city
    referrer = db.Column(db.String(500))  # Where they came from
    
    # Status
    completed = db.Column(db.Boolean, default=False)
    
    # Relationships
    interactions = db.relationship('ViewerInteraction', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'viewer_id': self.viewer_id,
            'documentary_id': self.documentary_id,
            'clip_id': self.clip_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'watch_time': self.watch_time,
            'completion_rate': self.completion_rate,
            'device_type': self.device_type,
            'browser': self.browser,
            'location': self.location,
            'referrer': self.referrer,
            'completed': self.completed,
        }


class ViewerInteraction(db.Model):
    """Individual viewer interactions (play, pause, seek, etc.)"""
    __tablename__ = 'viewer_interactions'
    
    id = db.Column(db.String(36), primary_key=True)
    session_id = db.Column(db.String(36), db.ForeignKey('viewer_sessions.id'), nullable=False)
    
    # Interaction data
    interaction_type = db.Column(db.String(50), nullable=False)  # play, pause, seek, skip, complete
    timestamp = db.Column(db.DateTime, default=func.now())
    clip_position = db.Column(db.Integer, nullable=True)  # Position in clip (seconds)
    segment_id = db.Column(db.String(36), nullable=True)
    
    # Additional data (note: 'metadata' is reserved by SQLAlchemy, using 'interaction_metadata')
    interaction_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'interaction_type': self.interaction_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'clip_position': self.clip_position,
            'segment_id': self.segment_id,
            'metadata': self.interaction_metadata,
        }


class AIModel(db.Model):
    """AI Models for theme generation and video creation"""
    __tablename__ = 'ai_models'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    model_type = db.Column(db.String(50), nullable=False)  # theme_generator, video_generator, image_generator, etc.
    
    # Model configuration
    provider = db.Column(db.String(100))  # openai, anthropic, stability, custom
    model_identifier = db.Column(db.String(200))  # gpt-4, claude-3, etc.
    api_endpoint = db.Column(db.String(500))
    api_key_required = db.Column(db.Boolean, default=True)
    
    # Model capabilities
    supported_themes = db.Column(db.Text)  # JSON array of theme names
    capabilities = db.Column(db.Text)  # JSON array of capabilities
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)  # Higher priority = used first
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    addons = db.relationship('ModelAddon', backref='model', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('ModelFavorite', backref='model', lazy=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'model_type': self.model_type,
            'provider': self.provider,
            'model_identifier': self.model_identifier,
            'api_endpoint': self.api_endpoint,
            'api_key_required': self.api_key_required,
            'supported_themes': json.loads(self.supported_themes) if self.supported_themes else [],
            'capabilities': json.loads(self.capabilities) if self.capabilities else [],
            'is_active': self.is_active,
            'is_default': self.is_default,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ModelAddon(db.Model):
    """Addons/plugins for AI models (special effects, enhancements, etc.)"""
    __tablename__ = 'model_addons'
    
    id = db.Column(db.String(36), primary_key=True)
    model_id = db.Column(db.String(36), db.ForeignKey('ai_models.id'), nullable=False)
    
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    addon_type = db.Column(db.String(50), nullable=False)  # special_effect, enhancement, filter, etc.
    
    # Addon configuration
    config = db.Column(db.Text)  # JSON configuration
    script_path = db.Column(db.String(500))  # Path to addon script/module
    
    # Settings
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    priority = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'model_id': self.model_id,
            'name': self.name,
            'description': self.description,
            'addon_type': self.addon_type,
            'config': json.loads(self.config) if self.config else {},
            'script_path': self.script_path,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ModelFavorite(db.Model):
    """User favorite models"""
    __tablename__ = 'model_favorites'
    
    id = db.Column(db.String(36), primary_key=True)
    model_id = db.Column(db.String(36), db.ForeignKey('ai_models.id'), nullable=False)
    user_id = db.Column(db.String(100), nullable=False, index=True)  # Can be session_id or user account
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'model_id': self.model_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ChatRoom(db.Model):
    """Tema-based chat rooms"""
    __tablename__ = 'chat_rooms'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    theme = db.Column(db.String(50), nullable=False)  # matrix, disney, stargate, etc.
    description = db.Column(db.Text)
    
    # Room settings
    is_public = db.Column(db.Boolean, default=True)
    max_users = db.Column(db.Integer, default=50)
    is_active = db.Column(db.Boolean, default=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    messages = db.relationship('ChatMessage', backref='room', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('ChatRoomMember', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'theme': self.theme,
            'description': self.description,
            'is_public': self.is_public,
            'max_users': self.max_users,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatMessage(db.Model):
    """Messages in chat rooms"""
    __tablename__ = 'chat_messages'
    
    id = db.Column(db.String(36), primary_key=True)
    room_id = db.Column(db.String(36), db.ForeignKey('chat_rooms.id'), nullable=False)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    username = db.Column(db.String(200))
    
    message = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='text')  # text, system, action, etc.
    
    # Metadata
    timestamp = db.Column(db.DateTime, default=func.now(), nullable=False, index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'username': self.username,
            'message': self.message,
            'message_type': self.message_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


class ChatRoomMember(db.Model):
    """Members in chat rooms"""
    __tablename__ = 'chat_room_members'
    
    id = db.Column(db.String(36), primary_key=True)
    room_id = db.Column(db.String(36), db.ForeignKey('chat_rooms.id'), nullable=False)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    username = db.Column(db.String(200))
    
    # Member status
    joined_at = db.Column(db.DateTime, default=func.now())
    last_active = db.Column(db.DateTime, default=func.now())
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'username': self.username,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'is_active': self.is_active,
        }


class ThemeUsageTracking(db.Model):
    """Track theme usage for learning and intelligence"""
    __tablename__ = 'theme_usage_tracking'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    theme = db.Column(db.String(50), nullable=False, index=True)
    
    # Usage statistics
    usage_count = db.Column(db.Integer, default=0)
    total_duration = db.Column(db.Integer, default=0)  # Total seconds of videos generated
    last_used = db.Column(db.DateTime, default=func.now())
    
    # Theme attributes (increase with usage)
    attribute_level = db.Column(db.Integer, default=1)  # Levels 1-10
    unlocked_features = db.Column(db.Text)  # JSON array of unlocked features
    preferences = db.Column(db.Text)  # JSON object of user preferences
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'theme': self.theme,
            'usage_count': self.usage_count,
            'total_duration': self.total_duration,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'attribute_level': self.attribute_level,
            'unlocked_features': json.loads(self.unlocked_features) if self.unlocked_features else [],
            'preferences': json.loads(self.preferences) if self.preferences else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class RandomImageInjection(db.Model):
    """Track random images injected into video frames"""
    __tablename__ = 'random_image_injections'
    
    id = db.Column(db.String(36), primary_key=True)
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'), nullable=False)
    
    # Image source
    image_source = db.Column(db.String(50), nullable=False)  # user_pictures, movie_clips, web_history, secrets
    image_path = db.Column(db.String(500), nullable=False)
    
    # Frame position
    frame_number = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.Float, nullable=False)  # Time in seconds
    fps = db.Column(db.Float, default=35.0)  # Frames per second
    
    # Metadata
    injection_type = db.Column(db.String(50), default='random')  # random, secrets, engagement
    created_at = db.Column(db.DateTime, default=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'documentary_id': self.documentary_id,
            'image_source': self.image_source,
            'image_path': self.image_path,
            'frame_number': self.frame_number,
            'timestamp': self.timestamp,
            'fps': self.fps,
            'injection_type': self.injection_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SidebarMonetization(db.Model):
    """Track sidebar monetization clicks and revenue"""
    __tablename__ = 'sidebar_monetization'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Sidebar identification
    sidebar_position = db.Column(db.String(20), nullable=False)  # left, right
    frame_id = db.Column(db.String(36), nullable=False)
    
    # Click tracking
    click_count = db.Column(db.Integer, default=0)
    impression_count = db.Column(db.Integer, default=0)
    last_click = db.Column(db.DateTime, nullable=True)
    
    # Revenue data
    revenue_generated = db.Column(db.Float, default=0.0)
    conversion_rate = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'sidebar_position': self.sidebar_position,
            'frame_id': self.frame_id,
            'click_count': self.click_count,
            'impression_count': self.impression_count,
            'last_click': self.last_click.isoformat() if self.last_click else None,
            'revenue_generated': self.revenue_generated,
            'conversion_rate': self.conversion_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ClipAnalysis(db.Model):
    """Full analysis of video clips for Perspectives tab"""
    __tablename__ = 'clip_analyses'
    
    id = db.Column(db.String(36), primary_key=True)
    clip_id = db.Column(db.String(36), db.ForeignKey('movie_clips.id'), nullable=False)
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'), nullable=False)
    
    # Analysis data (JSON)
    visual_analysis = db.Column(db.Text)  # Scene composition, colors, objects detected
    audio_analysis = db.Column(db.Text)  # Music, speech, sound effects
    text_analysis = db.Column(db.Text)  # OCR, captions, subtitles
    sentiment_analysis = db.Column(db.Text)  # Emotional tone, mood
    object_detection = db.Column(db.Text)  # Objects, people, places detected
    scene_segmentation = db.Column(db.Text)  # Scene boundaries and transitions
    
    # Perspectives data
    perspectives = db.Column(db.Text)  # Multiple perspective views/interpretations
    
    # Metadata
    analysis_version = db.Column(db.String(20), default='1.0')
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'clip_id': self.clip_id,
            'documentary_id': self.documentary_id,
            'visual_analysis': json.loads(self.visual_analysis) if self.visual_analysis else {},
            'audio_analysis': json.loads(self.audio_analysis) if self.audio_analysis else {},
            'text_analysis': json.loads(self.text_analysis) if self.text_analysis else {},
            'sentiment_analysis': json.loads(self.sentiment_analysis) if self.sentiment_analysis else {},
            'object_detection': json.loads(self.object_detection) if self.object_detection else {},
            'scene_segmentation': json.loads(self.scene_segmentation) if self.scene_segmentation else {},
            'perspectives': json.loads(self.perspectives) if self.perspectives else [],
            'analysis_version': self.analysis_version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Agent(db.Model):
    """AI Agents with user profiles"""
    __tablename__ = 'agents'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    agent_type = db.Column(db.String(50), default='assistant')  # assistant, generator, analyzer, etc.
    
    # User Profile
    profile_data = db.Column(db.Text)  # JSON: full user profile
    personality = db.Column(db.Text)  # JSON: personality traits, preferences
    expertise = db.Column(db.Text)  # JSON: areas of expertise
    behavior_patterns = db.Column(db.Text)  # JSON: behavioral patterns
    
    # Agent capabilities
    capabilities = db.Column(db.Text)  # JSON array of capabilities
    specializations = db.Column(db.Text)  # JSON array of specializations
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_available = db.Column(db.Boolean, default=True)
    current_task = db.Column(db.String(200))
    
    # Performance metrics
    tasks_completed = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Float, default=0.0)
    average_response_time = db.Column(db.Float, default=0.0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    last_active = db.Column(db.DateTime, default=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'name': self.name,
            'agent_type': self.agent_type,
            'profile_data': json.loads(self.profile_data) if self.profile_data else {},
            'personality': json.loads(self.personality) if self.personality else {},
            'expertise': json.loads(self.expertise) if self.expertise else {},
            'behavior_patterns': json.loads(self.behavior_patterns) if self.behavior_patterns else {},
            'capabilities': json.loads(self.capabilities) if self.capabilities else [],
            'specializations': json.loads(self.specializations) if self.specializations else [],
            'is_active': self.is_active,
            'is_available': self.is_available,
            'current_task': self.current_task,
            'tasks_completed': self.tasks_completed,
            'success_rate': self.success_rate,
            'average_response_time': self.average_response_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
        }


class UserProfile(db.Model):
    """Enhanced user profile with picture, username, trophy profiling, time tracking"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    username = db.Column(db.String(200), nullable=False, index=True)
    
    # Profile picture
    profile_picture_path = db.Column(db.String(500))  # Path to uploaded profile picture
    profile_picture_url = db.Column(db.String(500))  # URL if external storage
    
    # Trophy profiling
    trophy_profile = db.Column(db.Text)  # JSON: trophy achievements, categories, levels
    trophy_points = db.Column(db.Integer, default=0)
    trophy_level = db.Column(db.Integer, default=1)
    favorite_trophies = db.Column(db.Text)  # JSON array of favorite trophy IDs
    
    # Time tracking
    total_time_spent = db.Column(db.Integer, default=0)  # Total seconds spent on site
    session_time_today = db.Column(db.Integer, default=0)  # Seconds today
    session_time_week = db.Column(db.Integer, default=0)  # Seconds this week
    session_time_month = db.Column(db.Integer, default=0)  # Seconds this month
    last_active = db.Column(db.DateTime, default=func.now(), index=True)
    first_seen = db.Column(db.DateTime, default=func.now())
    
    # Catch stats (behavioral and interaction data)
    catch_stats = db.Column(db.Text)  # JSON: comprehensive catch statistics
    interaction_count = db.Column(db.Integer, default=0)
    generation_count = db.Column(db.Integer, default=0)
    watch_count = db.Column(db.Integer, default=0)
    share_count = db.Column(db.Integer, default=0)
    
    # Gameplay elements
    level = db.Column(db.Integer, default=1)
    xp = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=0)  # Virtual currency
    achievements = db.Column(db.Text)  # JSON array of achievement IDs
    badges = db.Column(db.Text)  # JSON array of badge IDs
    
    # Preferences and settings
    preferences = db.Column(db.Text)  # JSON: user preferences
    settings = db.Column(db.Text)  # JSON: user settings
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'profile_picture_path': self.profile_picture_path,
            'profile_picture_url': self.profile_picture_url,
            'trophy_profile': json.loads(self.trophy_profile) if self.trophy_profile else {},
            'trophy_points': self.trophy_points,
            'trophy_level': self.trophy_level,
            'favorite_trophies': json.loads(self.favorite_trophies) if self.favorite_trophies else [],
            'total_time_spent': self.total_time_spent,
            'session_time_today': self.session_time_today,
            'session_time_week': self.session_time_week,
            'session_time_month': self.session_time_month,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'catch_stats': json.loads(self.catch_stats) if self.catch_stats else {},
            'interaction_count': self.interaction_count,
            'generation_count': self.generation_count,
            'watch_count': self.watch_count,
            'share_count': self.share_count,
            'level': self.level,
            'xp': self.xp,
            'coins': self.coins,
            'achievements': json.loads(self.achievements) if self.achievements else [],
            'badges': json.loads(self.badges) if self.badges else [],
            'preferences': json.loads(self.preferences) if self.preferences else {},
            'settings': json.loads(self.settings) if self.settings else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class GenerationStats(db.Model):
    """Enhanced generation statistics tracking"""
    __tablename__ = 'generation_stats'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'), nullable=True)
    
    # Generation metrics
    generation_time = db.Column(db.Float)  # Time in seconds
    quality_score = db.Column(db.Float, default=0.0)
    duration_achieved = db.Column(db.Integer)  # Actual duration in seconds
    target_duration = db.Column(db.Integer)  # Target duration
    clips_generated = db.Column(db.Integer, default=0)
    
    # Performance metrics
    data_gathering_time = db.Column(db.Float)  # Time spent gathering data
    clip_generation_time = db.Column(db.Float)  # Time spent generating clips
    processing_time = db.Column(db.Float)  # Time spent processing
    
    # Resource usage
    memory_used = db.Column(db.Float)  # MB
    cpu_usage = db.Column(db.Float)  # Percentage
    disk_usage = db.Column(db.Float)  # MB
    
    # Quality metrics
    video_quality = db.Column(db.Float)  # 0.0-1.0
    audio_quality = db.Column(db.Float)  # 0.0-1.0
    coherence_score = db.Column(db.Float)  # 0.0-1.0
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'documentary_id': self.documentary_id,
            'generation_time': self.generation_time,
            'quality_score': self.quality_score,
            'duration_achieved': self.duration_achieved,
            'target_duration': self.target_duration,
            'clips_generated': self.clips_generated,
            'data_gathering_time': self.data_gathering_time,
            'clip_generation_time': self.clip_generation_time,
            'processing_time': self.processing_time,
            'memory_used': self.memory_used,
            'cpu_usage': self.cpu_usage,
            'disk_usage': self.disk_usage,
            'video_quality': self.video_quality,
            'audio_quality': self.audio_quality,
            'coherence_score': self.coherence_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
