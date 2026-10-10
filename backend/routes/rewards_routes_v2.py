"""
Rewards System v2.0 API Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.rewards_system_v2 import rewards_system_v2

rewards_v2_bp = Blueprint('rewards_v2', __name__, url_prefix='/api/rewards/v2')


@rewards_v2_bp.route('/user/<user_id>', methods=['GET'])
def get_user_rewards(user_id: str):
    """Get user's rewards"""
    try:
        include_history = request.args.get('include_history', 'true').lower() == 'true'
        result = rewards_system_v2.get_user_rewards(user_id, include_history=include_history)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/claim/<user_id>/<reward_id>', methods=['POST'])
def claim_reward(user_id: str, reward_id: str):
    """Claim a specific reward"""
    try:
        result = rewards_system_v2.claim_reward(user_id, reward_id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/claim-all/<user_id>', methods=['POST'])
def claim_all_rewards(user_id: str):
    """Claim all pending rewards"""
    try:
        result = rewards_system_v2.claim_all_rewards(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/daily/<user_id>', methods=['GET', 'POST'])
def daily_reward(user_id: str):
    """Get or claim daily reward"""
    try:
        result = rewards_system_v2.get_daily_reward(user_id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/weekly/<user_id>', methods=['GET', 'POST'])
def weekly_reward(user_id: str):
    """Get or claim weekly reward"""
    try:
        result = rewards_system_v2.get_weekly_reward(user_id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/monthly/<user_id>', methods=['GET', 'POST'])
def monthly_reward(user_id: str):
    """Get or claim monthly reward"""
    try:
        result = rewards_system_v2.get_monthly_reward(user_id)
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/battle/<user_id>', methods=['POST'])
def add_battle_reward(user_id: str):
    """Add battle reward"""
    try:
        battle_result = request.get_json() or {}
        result = rewards_system_v2.add_battle_reward(user_id, battle_result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/generation/<user_id>', methods=['POST'])
def add_generation_reward(user_id: str):
    """Add video generation reward"""
    try:
        generation_result = request.get_json() or {}
        result = rewards_system_v2.add_generation_reward(user_id, generation_result)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/level-up/<user_id>/<int:level>', methods=['POST'])
def add_level_up_reward(user_id: str, level: int):
    """Add level up reward"""
    try:
        result = rewards_system_v2.add_level_up_reward(user_id, level)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/achievement/<user_id>', methods=['POST'])
def add_achievement_reward(user_id: str):
    """Add achievement reward"""
    try:
        data = request.get_json() or {}
        achievement_id = data.get('achievement_id', '')
        achievement_data = data.get('achievement_data', {})
        result = rewards_system_v2.add_achievement_reward(user_id, achievement_id, achievement_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/streak/<user_id>', methods=['POST'])
def add_streak_reward(user_id: str):
    """Add streak reward"""
    try:
        data = request.get_json() or {}
        streak_type = data.get('streak_type', 'daily')
        streak_count = data.get('streak_count', 1)
        result = rewards_system_v2.add_streak_reward(user_id, streak_type, streak_count)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/activity/<user_id>', methods=['POST'])
def trigger_activity_reward(user_id: str):
    """Trigger activity-based reward"""
    try:
        data = request.get_json() or {}
        activity_type = data.get('activity_type', '')
        activity_data = data.get('activity_data', {})
        
        result = rewards_v2.trigger_activity_reward(user_id, activity_type, activity_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/discovery/<user_id>', methods=['POST'])
def trigger_discovery_reward(user_id: str):
    """Trigger discovery reward"""
    try:
        data = request.get_json() or {}
        discovery_type = data.get('discovery_type', '')
        discovery_data = data.get('discovery_data', {})
        
        result = rewards_v2.trigger_discovery_reward(user_id, discovery_type, discovery_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/milestone/<user_id>', methods=['POST'])
def trigger_milestone_reward(user_id: str):
    """Trigger milestone reward"""
    try:
        data = request.get_json() or {}
        milestone_type = data.get('milestone_type', '')
        milestone_value = data.get('milestone_value', 0)
        
        result = rewards_v2.trigger_milestone_reward(user_id, milestone_type, milestone_value)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/referral/<user_id>', methods=['POST'])
def trigger_referral_reward(user_id: str):
    """Trigger referral reward"""
    try:
        data = request.get_json() or {}
        referred_user_id = data.get('referred_user_id', '')
        
        result = rewards_v2.trigger_referral_reward(user_id, referred_user_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/quality/<user_id>', methods=['POST'])
def trigger_quality_reward(user_id: str):
    """Trigger quality-based reward"""
    try:
        data = request.get_json() or {}
        quality_score = data.get('quality_score', 0.0)
        
        result = rewards_v2.trigger_quality_reward(user_id, quality_score)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/speed/<user_id>', methods=['POST'])
def trigger_speed_reward(user_id: str):
    """Trigger speed-based reward"""
    try:
        data = request.get_json() or {}
        completion_time = data.get('completion_time', 0.0)
        target_time = data.get('target_time', 0.0)
        
        result = rewards_v2.trigger_speed_reward(user_id, completion_time, target_time)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/collection/<user_id>', methods=['POST'])
def trigger_collection_reward(user_id: str):
    """Trigger collection milestone reward"""
    try:
        data = request.get_json() or {}
        collection_type = data.get('collection_type', '')
        collection_count = data.get('collection_count', 0)
        
        result = rewards_v2.trigger_collection_reward(user_id, collection_type, collection_count)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/first-time/<user_id>', methods=['POST'])
def trigger_first_time_reward(user_id: str):
    """Trigger first-time action reward"""
    try:
        data = request.get_json() or {}
        action_type = data.get('action_type', '')
        
        result = rewards_v2.trigger_first_time_reward(user_id, action_type)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/combo/<user_id>', methods=['POST'])
def trigger_combo_reward(user_id: str):
    """Trigger combo reward"""
    try:
        data = request.get_json() or {}
        combo_type = data.get('combo_type', '')
        combo_count = data.get('combo_count', 0)
        
        result = rewards_v2.trigger_combo_reward(user_id, combo_type, combo_count)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/trigger/lucky/<user_id>', methods=['POST'])
def trigger_lucky_reward(user_id: str):
    """Trigger lucky reward"""
    try:
        data = request.get_json() or {}
        luck_score = data.get('luck_score', 0.0)
        
        result = rewards_v2.trigger_lucky_reward(user_id, luck_score)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/bundle/<user_id>', methods=['POST'])
def create_reward_bundle(user_id: str):
    """Create a reward bundle"""
    try:
        data = request.get_json() or {}
        bundle_name = data.get('bundle_name', '')
        bundle_items = data.get('bundle_items', [])
        
        result = rewards_v2.create_reward_bundle(user_id, bundle_name, bundle_items)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/create/<user_id>', methods=['POST'])
def create_reward(user_id: str):
    """Create a custom reward"""
    try:
        data = request.get_json() or {}
        result = rewards_system_v2.create_reward(
            user_id=user_id,
            category=data.get('category', 'event'),
            reward_type=data.get('reward_type', 'points'),
            amount=data.get('amount'),
            rarity=data.get('rarity', 'common'),
            description=data.get('description', ''),
            source=data.get('source', ''),
            metadata=data.get('metadata'),
            expires_at=None  # Can be added if needed
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get reward categories"""
    try:
        return jsonify({
            'success': True,
            'categories': rewards_system_v2.reward_categories
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/types', methods=['GET'])
def get_types():
    """Get reward types"""
    try:
        types_info = {
            k: {'name': v['name'], 'icon': v['icon']}
            for k, v in rewards_system_v2.reward_types.items()
        }
        return jsonify({
            'success': True,
            'types': types_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@rewards_v2_bp.route('/rarities', methods=['GET'])
def get_rarities():
    """Get reward rarities"""
    try:
        return jsonify({
            'success': True,
            'rarities': rewards_system_v2.reward_rarities
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

