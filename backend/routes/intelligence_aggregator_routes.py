"""
Intelligence Aggregator Routes
Routes for intelligence aggregation (research, news, trending)
"""
from flask import Blueprint, jsonify, request
from backend.services.aggregators.intelligence_aggregator import intelligence_aggregator

intelligence_aggregator_bp = Blueprint('intelligence_aggregator', __name__)

@intelligence_aggregator_bp.route('/api/aggregators/intelligence/research')
def get_research():
    """Get research papers"""
    try:
        limit = int(request.args.get('limit', 10))
        category = request.args.get('category', 'all')
        
        result = intelligence_aggregator.get_research_papers(limit=limit, category=category)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intelligence_aggregator_bp.route('/api/aggregators/intelligence/news')
def get_news():
    """Get news from multiple sources"""
    try:
        limit = int(request.args.get('limit', 10))
        source = request.args.get('source', 'all')
        
        result = intelligence_aggregator.get_news(limit=limit, source=source)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intelligence_aggregator_bp.route('/api/aggregators/intelligence/trending')
def get_trending():
    """Get trending intelligence topics"""
    try:
        limit = int(request.args.get('limit', 10))
        
        result = intelligence_aggregator.get_trending(limit=limit)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intelligence_aggregator_bp.route('/api/aggregators/intelligence/all')
def get_all_intelligence():
    """Get all intelligence data combined"""
    try:
        research_limit = int(request.args.get('research_limit', 5))
        news_limit = int(request.args.get('news_limit', 5))
        trending_limit = int(request.args.get('trending_limit', 5))
        
        result = intelligence_aggregator.get_all_intelligence(
            research_limit=research_limit,
            news_limit=news_limit,
            trending_limit=trending_limit
        )
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('aggregator')
        except Exception:
            pass
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intelligence_aggregator_bp.route('/api/aggregators/intelligence/sources')
def get_intelligence_sources():
    """List configured intelligence sources and status (enabled, has_api_key)."""
    try:
        result = intelligence_aggregator.get_sources()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_aggregator_bp.route('/api/aggregators/intelligence/weather')
def get_intelligence_weather():
    """Get current weather from Open-Meteo (optional context for content)."""
    try:
        result = intelligence_aggregator.get_weather()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _resolve_uid_agg() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')


# Small unified-point grants for monitor / encoder / explorer (caps per call)
_AGG_ACTION_POINTS = {
    'monitor_move': ('activity_points', 0.25),
    'explorer_chat': ('game_points', 1.0),
    'link_encode': ('game_points', 1.5),
    'link_decode': ('game_points', 1.0),
    'progress_refresh': ('activity_points', 0.5),
    'intel_loaded': ('knowledge_points', 0.5),
    'battle_overlay_enter': ('activity_points', 0.5),
    'monitor_battle_complete': ('activity_points', 1.0),
}


@intelligence_aggregator_bp.route('/api/aggregators/engagement/award', methods=['POST'])
def aggregator_engagement_award():
    """Award tiny unified points for aggregator UI actions (activity/game/knowledge)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get('user_id') or _resolve_uid_agg()) or 'default_user'
        raw = (data.get('action') or 'interaction').strip().lower()
        action = raw.replace(' ', '_').replace('-', '_')
        pt, base = _AGG_ACTION_POINTS.get(action, ('activity_points', 0.2))
        amt = min(float(base), 5.0)
        from backend.services.unified_points_database import unified_points_db
        if not unified_points_db:
            return jsonify({'success': False, 'error': 'points unavailable'}), 503
        meta = {'action': action, 'source': 'aggregator_engagement'}
        r = unified_points_db.add_points(user_id, pt, amt, 'aggregator_engagement', meta)
        ok = isinstance(r, dict) and r.get('success', True)
        mn2_result = {}
        mn2_awarded = 0.0
        try:
            from backend.services.aggregator_mn2_service import award_for_action
            mn2_result = award_for_action(user_id, action, meta)
            if mn2_result.get('success'):
                mn2_awarded = float(mn2_result.get('mn2_awarded') or 0)
        except Exception:
            pass
        return jsonify({
            'success': ok,
            'user_id': user_id,
            'action': action,
            'point_type': pt,
            'awarded': amt,
            'mn2_awarded': mn2_awarded,
            'mn2': mn2_result,
            'result': r,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_aggregator_bp.route('/api/aggregators/mn2/stats', methods=['GET'])
def aggregator_mn2_stats():
    """User or platform aggregator MN2 generation stats for HUD."""
    try:
        from backend.services.aggregator_mn2_service import get_public_stats, get_user_stats
        scope = (request.args.get('scope') or '').strip().lower()
        if scope == 'platform':
            return jsonify(get_public_stats()), 200
        user_id = request.args.get('user_id') or _resolve_uid_agg()
        stats = get_user_stats(user_id)
        stats['platform'] = get_public_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


        return jsonify({"success": False, "error": str(e)}), 500


@intelligence_aggregator_bp.route('/api/aggregators/callback/bet', methods=['POST'])
def aggregator_callback_bet():
    """External aggregator bet — debit user MN2. Requires MN2_CALLBACK_SECRET."""
    from backend.services.mn2_callback_auth import callback_authorized
    if not callback_authorized():
        return jsonify({'success': False, 'error': 'Unauthorized callback'}), 403
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get('user_id') or '').strip()
        amount = float(data.get('amount') or data.get('bet') or 0)
        if not user_id or amount <= 0:
            return jsonify({'success': False, 'error': 'user_id and positive amount required'}), 400
        from backend.services.aggregator_mn2_service import process_external_bet
        meta = {'game': data.get('game'), 'aggregator_id': data.get('aggregator_id'), **(data.get('meta') or {})}
        result = process_external_bet(user_id, amount, meta)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_aggregator_bp.route('/api/aggregators/callback/win', methods=['POST'])
def aggregator_callback_win():
    """External aggregator win — credit user MN2 (daily-capped). Requires MN2_CALLBACK_SECRET."""
    from backend.services.mn2_callback_auth import callback_authorized
    if not callback_authorized():
        return jsonify({'success': False, 'error': 'Unauthorized callback'}), 403
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get('user_id') or '').strip()
        amount = float(data.get('amount') or data.get('payout') or 0)
        if not user_id or amount <= 0:
            return jsonify({'success': False, 'error': 'user_id and positive amount required'}), 400
        from backend.services.aggregator_mn2_service import process_external_win
        meta = {'game': data.get('game'), 'aggregator_id': data.get('aggregator_id'), **(data.get('meta') or {})}
        result = process_external_win(user_id, amount, meta)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@intelligence_aggregator_bp.route('/api/aggregators/hub/links')
def aggregator_hub_links():
    """Curated default links for the aggregator page list-encoder and deep links."""
    return jsonify({
        'success': True,
        'panels': [
            {'id': 'monitor', 'label': '4D monitor playfield', 'href': '/aggregator#agg-monitor-anchor'},
            {'id': 'encoder', 'label': 'List encoder', 'href': '/aggregator#agg-encoder-block'},
            {'id': 'intel_all', 'label': 'Intelligence API (combined JSON)', 'href': '/api/aggregators/intelligence/all', 'external': True},
            {'id': 'battle_stats', 'label': 'Battle stats (JSON)', 'href': '/api/battle/stats', 'external': True},
            {'id': 'shop_boosters', 'label': 'Shop — boosters & events', 'href': '/shop#shop-boosters'},
            {'id': 'mn2_market', 'label': 'MN2 P2P market', 'href': '/market'},
        ],
    }), 200


@intelligence_aggregator_bp.route('/api/aggregators/intelligence/test')
def test_intelligence():
    """Test intelligence aggregator"""
    return jsonify({
        'success': True,
        'message': 'Intelligence aggregator is working',
        'endpoints': {
            'research': '/api/aggregators/intelligence/research',
            'news': '/api/aggregators/intelligence/news',
            'trending': '/api/aggregators/intelligence/trending',
            'all': '/api/aggregators/intelligence/all',
            'sources': '/api/aggregators/intelligence/sources',
            'weather': '/api/aggregators/intelligence/weather',
            'hub_links': '/api/aggregators/hub/links',
            'engagement_award': '/api/aggregators/engagement/award',
        },
        'sources': {
            'research': ['arXiv (real API)', 'fallback mock'],
            'news': ['Hacker News (real API)', 'NewsAPI (if key set)', 'fallback mock'],
            'weather': ['Open-Meteo (real API)'],
        }
    }), 200
