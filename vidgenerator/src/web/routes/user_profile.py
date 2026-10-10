"""
User Profile Routes
Handles username, picture upload, trophy profiling, gameplay
"""
from flask import Blueprint, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from pathlib import Path
from datetime import datetime
from src.db.models import db
from src.db.models_user_profile import UserProfile, UserTimeTracking, CatchStats, GenerationStats
from src.services.behavioral_tracking.trophy_system import TrophySystem

user_profile_bp = Blueprint('user_profile', __name__)
trophy_system = TrophySystem()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
UPLOAD_FOLDER = 'static/uploads/profiles'


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_user_id():
    """Get user ID from session or generate one"""
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


@user_profile_bp.route('/api/user/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = get_user_id()
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if not profile:
            # Create default profile
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                username=None,
                display_name='User',
                level=1,
                total_xp=0
            )
            db.session.add(profile)
            db.session.commit()
        
        # Get XP data
        try:
            from src.services.behavioral_tracking.xp_system import XPSystem
            xp_sys = XPSystem()
            xp_profile = xp_sys.get_user_profile(user_id)
            xp_history = xp_sys.get_xp_history(user_id)
            
            profile_dict = profile.to_dict()
            profile_dict['xp'] = {
                'total': xp_profile.get('total_xp', 0) or xp_profile.get('xp_total', 0),
                'level': xp_profile.get('level', 1),
                'recent_history': xp_history[-10:] if xp_history else [],
                'breakdown': {
                    'from_generations': sum(e.get('xp_awarded', 0) for e in xp_history if 'generation' in str(e.get('action_type', ''))),
                    'from_trophies': sum(e.get('xp_awarded', 0) for e in xp_history if 'trophy' in str(e.get('action_type', ''))),
                    'from_calendar': sum(e.get('xp_awarded', 0) for e in xp_history if 'calendar' in str(e.get('action_type', ''))),
                    'from_war_plan': sum(e.get('xp_awarded', 0) for e in xp_history if 'war_plan' in str(e.get('action_type', '')))
                }
            }
        except Exception as e:
            profile_dict = profile.to_dict()
            profile_dict['xp'] = {
                'total': profile.total_xp if hasattr(profile, 'total_xp') else 0,
                'level': profile.level if hasattr(profile, 'level') else 1,
                'recent_history': [],
                'breakdown': {}
            }
        
        return jsonify({
            'success': True,
            'profile': profile_dict
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/profile', methods=['POST'])
def update_profile():
    """Update user profile (username, display name, etc.)"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            db.session.add(profile)
        
        if 'username' in data:
            profile.username = data['username']
        if 'display_name' in data:
            profile.display_name = data['display_name']
        
        profile.last_active = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'profile': profile.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/profile/picture', methods=['POST'])
def upload_picture():
    """Upload profile picture"""
    try:
        user_id = get_user_id()
        
        if 'picture' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['picture']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
        # Create upload directory
        upload_path = Path(UPLOAD_FOLDER)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        filename = f"{user_id}_{uuid.uuid4().hex[:8]}.{file.filename.rsplit('.', 1)[1].lower()}"
        filepath = upload_path / filename
        
        # Save file
        file.save(str(filepath))
        
        # Update profile
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            db.session.add(profile)
        
        profile.profile_picture_path = str(filepath)
        profile.profile_picture_url = f'/static/uploads/profiles/{filename}'
        profile.last_active = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'picture_url': profile.profile_picture_url,
            'profile': profile.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/trophy-profile', methods=['GET'])
def get_trophy_profile():
    """Get trophy profile for user"""
    try:
        user_id = get_user_id()
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if not profile:
            return jsonify({
                'success': True,
                'trophy_profile': {},
                'trophies_earned': 0,
                'trophy_hunter_level': 1
            })
        
        trophy_profile = json.loads(profile.trophy_profile) if profile.trophy_profile else {}
        trophies = trophy_system.get_user_trophies(user_id)
        
        return jsonify({
            'success': True,
            'trophy_profile': trophy_profile,
            'trophies': trophies,
            'trophies_earned': profile.trophies_earned,
            'trophy_hunter_level': profile.trophy_hunter_level
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/catch-stats', methods=['GET'])
def get_catch_stats():
    """Get comprehensive catch stats"""
    try:
        user_id = get_user_id()
        stats = CatchStats.query.filter_by(user_id=user_id).first()
        
        if not stats:
            stats = CatchStats(
                id=str(uuid.uuid4()),
                user_id=user_id
            )
            db.session.add(stats)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'stats': stats.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/time-tracking', methods=['POST'])
def track_time():
    """Track user time spent"""
    try:
        user_id = get_user_id()
        data = request.get_json()
        
        activity_type = data.get('activity_type', 'browsing')  # generating, watching, browsing, stats, chat
        duration = data.get('duration', 0)  # seconds
        
        # Get or create time tracking
        tracking = UserTimeTracking.query.filter_by(
            user_id=user_id,
            session_end=None
        ).first()
        
        if not tracking:
            tracking = UserTimeTracking(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_start=datetime.utcnow()
            )
            db.session.add(tracking)
        
        # Update time based on activity
        if activity_type == 'generating':
            tracking.time_generating += duration
        elif activity_type == 'watching':
            tracking.time_watching += duration
        elif activity_type == 'browsing':
            tracking.time_browsing += duration
        elif activity_type == 'stats':
            tracking.time_in_stats += duration
        elif activity_type == 'chat':
            tracking.time_in_chat += duration
        
        tracking.session_duration += duration
        tracking.last_active = datetime.utcnow()
        
        # Update profile total time
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        if profile:
            profile.total_time_spent += duration
            profile.last_active = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'tracking': tracking.to_dict() if tracking else {}
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_user_profile_routes(app):
    """Register user profile routes"""
    app.register_blueprint(user_profile_bp)
    print("[Routes] User profile routes registered")

