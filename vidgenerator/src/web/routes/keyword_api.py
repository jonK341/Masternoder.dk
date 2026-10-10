"""
Keyword Foundation API Routes
Handles keyword translation, activation, and integration
"""

from flask import Blueprint, jsonify, request
from src.services.game.keyword_foundation import (
    PROCESSED_KEYWORDS,
    translate_keyword,
    get_keyword_category,
    get_keyword_power_level,
    process_keyword_list
)
from src.services.game.keyword_integration import (
    keyword_worker_integrator,
    keyword_ai_integrator
)

keyword_api_bp = Blueprint('keyword_api', __name__)

@keyword_api_bp.route('/api/keywords/all')
def get_all_keywords():
    """Get all keywords (translated and processed)"""
    return jsonify({
        'success': True,
        'keywords': PROCESSED_KEYWORDS,
        'total': len(PROCESSED_KEYWORDS),
        'categories': list(set(kw['category'] for kw in PROCESSED_KEYWORDS))
    })

@keyword_api_bp.route('/api/keywords/active')
def get_active_keywords():
    """Get currently active keywords"""
    active = [kw for kw in PROCESSED_KEYWORDS if kw.get('active', False)]
    return jsonify({
        'success': True,
        'keywords': active,
        'count': len(active),
        'total_power': sum(kw.get('power_level', 0) for kw in active),
        'categories': list(set(kw['category'] for kw in active))
    })

@keyword_api_bp.route('/api/keywords/activate', methods=['POST'])
def activate_keyword():
    """Activate a keyword for use"""
    data = request.get_json()
    keyword_english = data.get('keyword')
    
    if not keyword_english:
        return jsonify({'success': False, 'error': 'Keyword required'}), 400
    
    # Find and activate keyword
    activated = keyword_worker_integrator.activate_keyword(keyword_english)
    
    if activated:
        return jsonify({
            'success': True,
            'keyword': activated,
            'message': f'Keyword "{keyword_english}" activated'
        })
    else:
        return jsonify({
            'success': False,
            'error': f'Keyword "{keyword_english}" not found'
        }), 404

@keyword_api_bp.route('/api/keywords/translate', methods=['POST'])
def translate_keyword_endpoint():
    """Translate Danish keyword to English"""
    data = request.get_json()
    danish_keyword = data.get('keyword')
    
    if not danish_keyword:
        return jsonify({'success': False, 'error': 'Keyword required'}), 400
    
    english = translate_keyword(danish_keyword)
    category = get_keyword_category(english)
    power_level = get_keyword_power_level(english)
    
    return jsonify({
        'success': True,
        'original': danish_keyword,
        'english': english,
        'category': category,
        'power_level': power_level
    })

@keyword_api_bp.route('/api/keywords/stats')
def get_keyword_stats():
    """Get keyword statistics"""
    active = [kw for kw in PROCESSED_KEYWORDS if kw.get('active', False)]
    category_counts = {}
    total_power = 0
    
    for kw in active:
        category = kw['category']
        category_counts[category] = category_counts.get(category, 0) + 1
        total_power += kw.get('power_level', 0)
    
    return jsonify({
        'success': True,
        'stats': {
            'total_keywords': len(PROCESSED_KEYWORDS),
            'active_keywords': len(active),
            'total_power': total_power,
            'category_distribution': category_counts,
            'categories': list(set(kw['category'] for kw in PROCESSED_KEYWORDS))
        }
    })

