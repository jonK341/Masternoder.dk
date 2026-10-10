"""
Enhanced User Profile Models
Includes username, picture upload, trophy profiling, time tracking, catch stats
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from typing import Optional
from sqlalchemy.sql import func
import json

# Import existing db instance
from src.db.models import db


class UserProfile(db.Model):
    """Enhanced user profile with gameplay, trophies, and stats"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    username = db.Column(db.String(100), nullable=True, index=True)
    display_name = db.Column(db.String(200))
    
    # Profile picture
    profile_picture_path = db.Column(db.String(500))
    profile_picture_url = db.Column(db.String(500))
    
    # Gameplay stats
    level = db.Column(db.Integer, default=1, index=True)
    total_xp = db.Column(db.Integer, default=0, index=True)
    high_score = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # Total seconds
    
    # Trophy profiling
    trophies_earned = db.Column(db.Integer, default=0)
    trophy_profile = db.Column(db.Text)  # JSON: detailed trophy data
    trophy_hunter_level = db.Column(db.Integer, default=1)
    
    # Catch stats (comprehensive tracking)
    catch_stats = db.Column(db.Text)  # JSON: all catch statistics
    generation_stats = db.Column(db.Text)  # JSON: generation statistics
    engagement_stats = db.Column(db.Text)  # JSON: engagement statistics
    
    # Time tracking
    first_seen = db.Column(db.DateTime, default=func.now())
    last_active = db.Column(db.DateTime, default=func.now(), onupdate=func.now(), index=True)
    total_sessions = db.Column(db.Integer, default=0)
    average_session_duration = db.Column(db.Integer, default=0)  # seconds
    
    # Preferences and settings
    preferences = db.Column(db.Text)  # JSON: user preferences
    settings = db.Column(db.Text)  # JSON: user settings
    
    # Gay Metal AI's / Jons ass ID = 1.00.000 Stats
    gay_metal_ai_id = db.Column(db.String(50), default='1.00.000')
    new_paragraphs = db.Column(db.Text)  # JSON: new paragraphs
    agenda = db.Column(db.Text)  # JSON: agenda items
    science_stats = db.Column(db.Text)  # JSON: science statistics
    vm_titles = db.Column(db.Text)  # JSON: VM titles
    ak_titles = db.Column(db.Text)  # JSON: AK titles
    
    # Magi Metal Fan usernames
    magi_metal_fans = db.Column(db.Text)  # JSON: list of fan usernames
    
    # Special events
    special_events = db.Column(db.Text)  # JSON: special events (bunny pussy christmas hardcore fest, etc.)
    
    # Jons VoldsRøv ID = Ny §
    voldsrov_id = db.Column(db.String(100), default='Ny §')
    voldsrov_stats = db.Column(db.Text)  # JSON: VoldsRøv battle statistics
    voldsrov_points = db.Column(db.Integer, default=0)
    voldsrov_items = db.Column(db.Text)  # JSON: VoldsRøv items collected
    voldsrov_wars = db.Column(db.Text)  # JSON: VoldsRøv war participation
    
    # Guild vs Clan War Stats
    guild_war_points = db.Column(db.Integer, default=0)
    clan_war_points = db.Column(db.Integer, default=0)
    guild_war_items = db.Column(db.Text)  # JSON: items from guild wars
    clan_war_items = db.Column(db.Text)  # JSON: items from clan wars
    war_stats = db.Column(db.Text)  # JSON: comprehensive war statistics
    
    # Theme-based stats
    theme_war_stats = db.Column(db.Text)  # JSON: stats per theme in wars
    theme_points = db.Column(db.Text)  # JSON: points earned per theme
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'display_name': self.display_name,
            'profile_picture_path': self.profile_picture_path,
            'profile_picture_url': self.profile_picture_url,
            'level': self.level,
            'total_xp': self.total_xp,
            'high_score': self.high_score,
            'total_time_spent': self.total_time_spent,
            'trophies_earned': self.trophies_earned,
            'trophy_profile': json.loads(self.trophy_profile) if self.trophy_profile else {},
            'trophy_hunter_level': self.trophy_hunter_level,
            'catch_stats': json.loads(self.catch_stats) if self.catch_stats else {},
            'generation_stats': json.loads(self.generation_stats) if self.generation_stats else {},
            'engagement_stats': json.loads(self.engagement_stats) if self.engagement_stats else {},
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'total_sessions': self.total_sessions,
            'average_session_duration': self.average_session_duration,
            'preferences': json.loads(self.preferences) if self.preferences else {},
            'settings': json.loads(self.settings) if self.settings else {},
            'gay_metal_ai_id': self.gay_metal_ai_id,
            'new_paragraphs': json.loads(self.new_paragraphs) if self.new_paragraphs else [],
            'agenda': json.loads(self.agenda) if self.agenda else [],
            'science_stats': json.loads(self.science_stats) if self.science_stats else {},
            'vm_titles': json.loads(self.vm_titles) if self.vm_titles else [],
            'ak_titles': json.loads(self.ak_titles) if self.ak_titles else [],
            'magi_metal_fans': json.loads(self.magi_metal_fans) if self.magi_metal_fans else [],
            'special_events': json.loads(self.special_events) if self.special_events else [],
            'voldsrov_id': self.voldsrov_id,
            'voldsrov_stats': json.loads(self.voldsrov_stats) if self.voldsrov_stats else {},
            'voldsrov_points': self.voldsrov_points,
            'voldsrov_items': json.loads(self.voldsrov_items) if self.voldsrov_items else [],
            'voldsrov_wars': json.loads(self.voldsrov_wars) if self.voldsrov_wars else [],
            'guild_war_points': self.guild_war_points,
            'clan_war_points': self.clan_war_points,
            'guild_war_items': json.loads(self.guild_war_items) if self.guild_war_items else [],
            'clan_war_items': json.loads(self.clan_war_items) if self.clan_war_items else [],
            'war_stats': json.loads(self.war_stats) if self.war_stats else {},
            'theme_war_stats': json.loads(self.theme_war_stats) if self.theme_war_stats else {},
            'theme_points': json.loads(self.theme_points) if self.theme_points else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class UserTimeTracking(db.Model):
    """Detailed time tracking for users"""
    __tablename__ = 'user_time_tracking'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Time tracking
    session_start = db.Column(db.DateTime, default=func.now(), index=True)
    session_end = db.Column(db.DateTime, nullable=True)
    session_duration = db.Column(db.Integer, default=0)  # seconds
    
    # Activity breakdown
    time_generating = db.Column(db.Integer, default=0)  # seconds spent generating
    time_watching = db.Column(db.Integer, default=0)  # seconds spent watching
    time_browsing = db.Column(db.Integer, default=0)  # seconds spent browsing
    time_in_stats = db.Column(db.Integer, default=0)  # seconds in stats page
    time_in_chat = db.Column(db.Integer, default=0)  # seconds in chat
    
    # Page visits
    pages_visited = db.Column(db.Text)  # JSON: list of pages visited
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'session_end': self.session_end.isoformat() if self.session_end else None,
            'session_duration': self.session_duration,
            'time_generating': self.time_generating,
            'time_watching': self.time_watching,
            'time_browsing': self.time_browsing,
            'time_in_stats': self.time_in_stats,
            'time_in_chat': self.time_in_chat,
            'pages_visited': json.loads(self.pages_visited) if self.pages_visited else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CatchStats(db.Model):
    """Comprehensive catch statistics tracking"""
    __tablename__ = 'catch_stats'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Generation catches
    generations_completed = db.Column(db.Integer, default=0)
    generations_started = db.Column(db.Integer, default=0)
    generations_failed = db.Column(db.Integer, default=0)
    
    # Quality catches
    high_quality_generations = db.Column(db.Integer, default=0)  # quality > 0.8
    medium_quality_generations = db.Column(db.Integer, default=0)  # 0.5-0.8
    low_quality_generations = db.Column(db.Integer, default=0)  # < 0.5
    
    # Duration catches
    short_videos = db.Column(db.Integer, default=0)  # < 2 min
    medium_videos = db.Column(db.Integer, default=0)  # 2-5 min
    long_videos = db.Column(db.Integer, default=0)  # > 5 min
    
    # Theme catches
    theme_usage = db.Column(db.Text)  # JSON: {theme: count}
    
    # Engagement catches
    videos_watched = db.Column(db.Integer, default=0)
    videos_shared = db.Column(db.Integer, default=0)
    videos_liked = db.Column(db.Integer, default=0)
    
    # Trophy catches
    trophies_earned = db.Column(db.Integer, default=0)
    milestones_reached = db.Column(db.Integer, default=0)
    
    # Time catches
    total_generation_time = db.Column(db.Integer, default=0)  # seconds
    total_watch_time = db.Column(db.Integer, default=0)  # seconds
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'user_id': self.user_id,
            'generations_completed': self.generations_completed,
            'generations_started': self.generations_started,
            'generations_failed': self.generations_failed,
            'high_quality_generations': self.high_quality_generations,
            'medium_quality_generations': self.medium_quality_generations,
            'low_quality_generations': self.low_quality_generations,
            'short_videos': self.short_videos,
            'medium_videos': self.medium_videos,
            'long_videos': self.long_videos,
            'theme_usage': json.loads(self.theme_usage) if self.theme_usage else {},
            'videos_watched': self.videos_watched,
            'videos_shared': self.videos_shared,
            'videos_liked': self.videos_liked,
            'trophies_earned': self.trophies_earned,
            'milestones_reached': self.milestones_reached,
            'total_generation_time': self.total_generation_time,
            'total_watch_time': self.total_watch_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class GenerationStats(db.Model):
    """Enhanced generation statistics"""
    __tablename__ = 'generation_stats'
    
    id = db.Column(db.String(36), primary_key=True)
    documentary_id = db.Column(db.String(36), db.ForeignKey('documentaries.id'), nullable=False, index=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Generation metrics
    generation_time = db.Column(db.Float)  # seconds
    quality_score = db.Column(db.Float, default=0.0)
    duration_achieved = db.Column(db.Integer)  # seconds
    target_duration = db.Column(db.Integer)  # seconds
    
    # Resource usage
    memory_used = db.Column(db.Float)  # MB
    cpu_usage_avg = db.Column(db.Float)  # percentage
    disk_usage = db.Column(db.Float)  # MB
    
    # Data collection
    images_collected = db.Column(db.Integer, default=0)
    scripts_collected = db.Column(db.Integer, default=0)
    data_sources_used = db.Column(db.Integer, default=0)  # Number of data sources
    
    # AI generation
    clips_generated = db.Column(db.Integer, default=0)
    ai_providers_used = db.Column(db.Text)  # JSON: list of providers
    fallback_used = db.Column(db.Boolean, default=False)
    
    # Performance
    progress_jumps = db.Column(db.Integer, default=0)  # Number of progress jumps
    errors_encountered = db.Column(db.Integer, default=0)
    retries_needed = db.Column(db.Integer, default=0)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=func.now(), index=True)
    
    def to_dict(self):
        """Convert to dictionary"""
        import json
        return {
            'id': self.id,
            'documentary_id': self.documentary_id,
            'user_id': self.user_id,
            'generation_time': self.generation_time,
            'quality_score': self.quality_score,
            'duration_achieved': self.duration_achieved,
            'target_duration': self.target_duration,
            'memory_used': self.memory_used,
            'cpu_usage_avg': self.cpu_usage_avg,
            'disk_usage': self.disk_usage,
            'images_collected': self.images_collected,
            'scripts_collected': self.scripts_collected,
            'data_sources_used': self.data_sources_used,
            'clips_generated': self.clips_generated,
            'ai_providers_used': json.loads(self.ai_providers_used) if self.ai_providers_used else [],
            'fallback_used': self.fallback_used,
            'progress_jumps': self.progress_jumps,
            'errors_encountered': self.errors_encountered,
            'retries_needed': self.retries_needed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

