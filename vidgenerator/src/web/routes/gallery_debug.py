"""
Debug endpoint to check gallery database state
"""
from flask import Blueprint, jsonify
from src.db.models import db, Documentary
from datetime import datetime, timedelta

gallery_debug_bp = Blueprint('gallery_debug', __name__)


@gallery_debug_bp.route('/api/gallery/debug', methods=['GET'])
@gallery_debug_bp.route('/vidgenerator/api/gallery/debug', methods=['GET'])
def gallery_debug():
    """Debug endpoint to check gallery database state"""
    try:
        # Get all documentaries
        all_docs = Documentary.query.all()
        
        # Get docs with video_path
        docs_with_video = Documentary.query.filter(
            Documentary.video_path.isnot(None),
            Documentary.video_path != ''
        ).all()
        
        # Get completed docs
        completed_docs = Documentary.query.filter(
            Documentary.status == 'completed'
        ).all()
        
        # Get recent docs (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_docs = Documentary.query.filter(
            Documentary.created_at >= yesterday
        ).all()
        
        # Get recent with video
        recent_with_video = Documentary.query.filter(
            Documentary.created_at >= yesterday,
            Documentary.video_path.isnot(None),
            Documentary.video_path != ''
        ).all()
        
        return jsonify({
            'total_documentaries': len(all_docs),
            'with_video_path': len(docs_with_video),
            'completed': len(completed_docs),
            'recent_24h': len(recent_docs),
            'recent_with_video': len(recent_with_video),
            'sample_recent': [
                {
                    'id': doc.id,
                    'title': doc.title,
                    'status': doc.status,
                    'progress': doc.progress,
                    'video_path': doc.video_path[:100] if doc.video_path else None,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                    'completed_at': doc.completed_at.isoformat() if doc.completed_at else None
                }
                for doc in recent_with_video[:10]
            ],
            'status_breakdown': {
                status: len([d for d in all_docs if d.status == status])
                for status in ['pending', 'generating', 'completed', 'failed']
            }
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

