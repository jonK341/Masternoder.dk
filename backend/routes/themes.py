"""
Themes Routes — list/user endpoints delegate to missing_endpoints (Gate A / generator P0).
"""
from flask import Blueprint, jsonify, request

from backend.routes.missing_endpoints_routes import themes_list, themes_user

themes_bp = Blueprint('themes', __name__)

themes_bp.add_url_rule('/api/themes/list', view_func=themes_list, methods=['GET'])
themes_bp.add_url_rule('/api/themes/user', view_func=themes_user, methods=['GET'])


@themes_bp.route('/api/themes/<theme_id>', methods=['GET'])
def get_theme(theme_id: str):
    """Get one theme from the public catalog."""
    resp = themes_list()
    payload = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
    themes = (payload or {}).get('themes') or []
    theme = next(
        (t for t in themes if t.get('theme_id') == theme_id or t.get('id') == theme_id),
        None,
    )
    if not theme:
        return jsonify({'success': False, 'error': 'Theme not found'}), 404
    return jsonify({'success': True, 'theme': theme}), 200


@themes_bp.route('/api/themes/unlock', methods=['POST'])
def unlock_theme():
    return jsonify({'success': False, 'error': 'Use shop or level progression to unlock themes'}), 501


@themes_bp.route('/api/themes/use', methods=['POST'])
def use_theme():
    return jsonify({'success': True, 'recorded': False, 'note': 'Theme usage tracking not enabled'}), 200


@themes_bp.route('/api/themes/stats', methods=['GET'])
def get_theme_stats():
    user_id = request.args.get('user_id', 'default_user')
    resp = themes_user()
    data = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
    return jsonify({
        'success': True,
        'themes': (data or {}).get('themes', []),
        'stats': {},
    }), 200
