"""
Enhanced Chat Routes with Notification Alarm and Screen Capture
"""

from flask import Blueprint, render_template, jsonify, request, session
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from typing import Dict, Any

chat_enhanced_bp = Blueprint('chat_enhanced', __name__)

# Import chat points system
try:
    from src.services.behavioral_tracking.chat_points import chat_points_system
except ImportError:
    chat_points_system = None


@chat_enhanced_bp.route('/vidgenerator/chat')
def chat_page():
    """Enhanced chat page with notification alarm"""
    try:
        return render_template('chat/index.html')
    except Exception as e:
        return f"Error loading chat page: {str(e)}", 500


@chat_enhanced_bp.route('/api/chat/upload-screenshot', methods=['POST'])
def upload_screenshot():
    """Upload screenshot from chat notification alarm"""
    try:
        if 'screenshot' not in request.files:
            return jsonify({'error': 'No screenshot file'}), 400
        
        file = request.files['screenshot']
        metadata = request.form.get('metadata', '{}')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save screenshot
        filename = secure_filename(f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        upload_dir = os.path.join('static', 'uploads', 'screenshots')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # Store metadata
        screenshot_data = {
            'filename': filename,
            'filepath': filepath,
            'metadata': metadata,
            'uploaded_at': datetime.now().isoformat(),
            'user_id': session.get('user_id', 'anonymous')
        }
        
        return jsonify({
            'success': True,
            'screenshot': screenshot_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_enhanced_bp.route('/api/chat/notifications/settings', methods=['GET', 'POST'])
def notification_settings():
    """Get or update notification settings"""
    try:
        user_id = session.get('user_id', 'anonymous')
        
        if request.method == 'POST':
            data = request.get_json()
            # Save notification settings
            settings = {
                'enabled': data.get('enabled', True),
                'screen_capture': data.get('screen_capture', False),
                'sound_enabled': data.get('sound_enabled', True),
                'mention_notifications': data.get('mention_notifications', True),
                'alert_notifications': data.get('alert_notifications', True)
            }
            
            return jsonify({
                'success': True,
                'settings': settings
            })
        else:
            # Get notification settings
            settings = {
                'enabled': True,
                'screen_capture': False,
                'sound_enabled': True,
                'mention_notifications': True,
                'alert_notifications': True
            }
            
            return jsonify({
                'success': True,
                'settings': settings
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_chat_enhanced_routes(app):
    """Register enhanced chat routes"""
    app.register_blueprint(chat_enhanced_bp, url_prefix='/vidgenerator')
    print("[Routes] Enhanced chat routes registered")
