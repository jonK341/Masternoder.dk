"""Game Hub API — unified frontpage + cross-system tabs."""
from flask import Blueprint, jsonify, request

game_hub_bp = Blueprint('game_hub', __name__)

_AGENT_TOOLS = [
    {
        'action': 'overview',
        'method': 'GET',
        'path': '/api/game-hub/overview',
        'mutating': False,
        'description': 'Unified hub snapshot: trophies, quests, game, battle, story tabs.',
    },
    {
        'action': 'quests',
        'method': 'GET',
        'path': '/api/game-hub/quests',
        'mutating': False,
        'description': 'All unified quests (trophy, platform, AI daily, casino).',
    },
    {
        'action': 'quest_claim',
        'method': 'POST',
        'path': '/api/game-hub/quests/claim',
        'mutating': True,
        'params': ['quest_id'],
        'description': 'Claim or complete a unified quest; awards streak MN2 at 7-day streak.',
    },
    {
        'action': 'story_read',
        'method': 'POST',
        'path': '/api/game-hub/stories/read',
        'mutating': True,
        'params': ['story_id'],
        'description': 'Mark a hunter story as read; updates Story tab progress.',
    },
    {
        'action': 'story_progress',
        'method': 'GET',
        'path': '/api/game-hub/stories/progress',
        'mutating': False,
        'description': 'Get hunter story read progress for the user.',
    },
]


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True, use_session=True, use_identification=True)
    except Exception:
        return (request.args.get('user_id') or 'default_user').strip()


@game_hub_bp.route('/api/game-hub/overview')
def game_hub_overview():
    try:
        from backend.services.game_hub_service import get_overview
        return jsonify(get_overview(_resolve_uid())), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@game_hub_bp.route('/api/game-hub/quests')
def game_hub_quests():
    try:
        from backend.services.trophy_quest_service import get_unified_quests
        return jsonify(get_unified_quests(_resolve_uid())), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@game_hub_bp.route('/api/game-hub/quests/claim', methods=['POST'])
def game_hub_quest_claim():
    try:
        data = request.get_json() or {}
        quest_id = data.get('quest_id') or request.args.get('quest_id')
        from backend.services.trophy_quest_service import claim_quest
        return jsonify(claim_quest(_resolve_uid(), str(quest_id or ''))), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@game_hub_bp.route('/api/game-hub/stories/progress', methods=['GET'])
def game_hub_story_progress():
    try:
        from backend.services.game_hub_service import get_story_progress
        return jsonify({'success': True, 'user_id': _resolve_uid(), **get_story_progress(_resolve_uid())}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@game_hub_bp.route('/api/game-hub/stories/read', methods=['POST'])
def game_hub_story_read():
    try:
        data = request.get_json() or {}
        story_id = data.get('story_id') or request.args.get('story_id')
        from backend.services.game_hub_service import mark_story_read
        return jsonify(mark_story_read(_resolve_uid(), str(story_id or ''))), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@game_hub_bp.route('/api/game-hub/agent-tools', methods=['GET'])
def game_hub_agent_tools():
    """Capability map for agents (Game Hub #25)."""
    return jsonify({
        'success': True,
        'tools': _AGENT_TOOLS,
        'note': 'Mutating actions via /api/game-hub/agent-action require approved=true.',
    }), 200


@game_hub_bp.route('/api/game-hub/agent-action', methods=['POST'])
def game_hub_agent_action():
    """Execute a game-hub action as an agent (#25)."""
    try:
        data = request.get_json() or {}
        action = data.get('action')
        tool = next((t for t in _AGENT_TOOLS if t['action'] == action), None)
        if not tool:
            return jsonify({
                'success': False,
                'error': 'Unknown action',
                'available': [t['action'] for t in _AGENT_TOOLS],
            }), 400
        if tool['mutating'] and not data.get('approved'):
            return jsonify({
                'success': False,
                'error': 'Mutating action requires approved=true',
                'action': action,
            }), 403

        user_id = _resolve_uid()
        if action == 'overview':
            from backend.services.game_hub_service import get_overview
            return jsonify(get_overview(user_id)), 200
        if action == 'quests':
            from backend.services.trophy_quest_service import get_unified_quests
            return jsonify(get_unified_quests(user_id)), 200
        if action == 'quest_claim':
            quest_id = data.get('quest_id') or ''
            from backend.services.trophy_quest_service import claim_quest
            return jsonify(claim_quest(user_id, str(quest_id))), 200
        if action == 'story_progress':
            from backend.services.game_hub_service import get_story_progress
            return jsonify({'success': True, 'user_id': user_id, **get_story_progress(user_id)}), 200
        if action == 'story_read':
            story_id = data.get('story_id') or ''
            from backend.services.game_hub_service import mark_story_read
            return jsonify(mark_story_read(user_id, str(story_id))), 200
        return jsonify({'success': False, 'error': 'Unhandled action'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
