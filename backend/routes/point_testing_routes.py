"""
Point Testing Routes
Test URLs for each point skill and all POINT_VALUES
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
import json

logger = logging.getLogger(__name__)

point_testing_bp = Blueprint('point_testing', __name__, url_prefix='/api/test/points')

# All POINT_VALUES from 178_systems_calculator_code.py
POINT_VALUES = {
    'xp': 15,
    'activity': 1,
    'theme': 1,
    'chat': 1,
    'trophy': 1,
    'battle': 15,
    'achievement': 1,
    'stats': 1,
    'metal': 1,
    'graduation': 1,
    'generation': 15,
    'krimetime': 1,
    'guild': 1,
    'rewards': 1,
    'shop': 1,
    'social': 1,
    'champions_league': 1,
    'watch_time': 12,
    'scroll_depth': 1,
    'interaction_quality': 1,
    'return_visitor': 1,
    'session_duration': 1,
    'page_depth': 1,
    'content_consumption': 1,
    'search': 1,
    'filter': 1,
    'share': 1,
    'bookmark': 1,
    'comment': 1,
    'rating': 1,
    'pvp_battle': 240,
    'pve_battle': 240,
    'team_battle': 24,
    'guild_battle': 24,
    'arena_battle': 24,
    'tournament': 24,
    'ranked_battle': 24,
    'casual_battle': 24,
    'victory': 24,
    'defeat': 24,
    'perfect_victory': 24,
    'comeback': 24,
    'streak_battle': 24,
    'first_blood': 24,
    'multi_kill': 24,
    'assist': 24,
    'defense': 24,
    'offense': 24,
    'tactical': 24,
    'strategy': 24,
    'combo': 24,
    'ultimate': 24,
    'death_portal_teleport': 450,
    'production_10x': 3000,
    'skillset_mastery': 45,
    'video_generation': 600,
    'clip_generation': 600,
    'image_generation': 600,
    'audio_generation': 600,
    'text_generation': 60,
    'template_usage': 60,
    'custom_creation': 60,
    'quality': 60,
    'innovation': 75,
    'trending': 60,
    'viral': 60,
    'collaboration': 60,
    'remix': 60,
    'edit': 60,
    'publish': 60,
    'schedule': 60,
    'series': 60,
    'playlist': 60,
    'collection': 60,
    'production_mastery': 750,
    'friend': 18,
    'follow': 18,
    'follower': 18,
    'message': 18,
    'group': 18,
    'community': 18,
    'event': 18,
    'meetup': 18,
    'discussion': 18,
    'forum': 18,
    'help': 18,
    'mentor': 18,
    'apprentice': 18,
    'referral': 18,
    'invite': 18,
    'gift': 18,
    'thank_you': 18,
    'recognition': 18,
    'celebration': 50,
    'community_mastery': 18,
    'level_up': 120,
    'skill': 180,
    'mastery': 120,
    'prestige': 120,
    'rank': 120,
    'tier': 120,
    'badge': 120,
    'medal': 120,
    'title': 120,
    'achievement_chain': 120,
    'milestone': 120,
    'progress': 120,
    'completion': 120,
    'teleport_skillset': 225,
    'death_portal_mastery': 1500,
    'purchase': 30,
    'sale': 30,
    'trade': 30,
    'auction': 30,
    'market': 30,
    'currency': 30,
    'investment': 30,
    'profit': 30,
    'deal': 30,
    'negotiation': 30,
    'collection_value': 30,
    'asset': 30,
    'wealth': 30,
    'production_economy': 375,
    'teleport_trade': 55,
    'exploration': 30,
    'discovery': 30,
    'unlock': 30,
    'reveal': 30,
    'map': 30,
    'location': 30,
    'hidden': 30,
    'secret': 30,
    'easter_egg': 30,
    'landmark': 30,
    'path': 30,
    'route': 30,
    'learning': 40,
    'course': 40,
    'lesson': 40,
    'quiz': 40,
    'test': 40,
    'certification': 40,
    'knowledge': 40,
    'skill_development': 60,
    'practice': 40,
    'study': 40,
    'research': 40,
    'education': 40,
    'event_participation': 50,
    'holiday': 50,
    'seasonal': 50,
    'limited_time': 50,
    'special_event': 50,
    'anniversary': 50,
    'festival': 50,
    'competition': 50,
    'death_portal_event': 750,
    'customization': 10,
    'avatar': 10,
    'theme_custom': 10,
    'layout': 10,
    'style': 10,
    'personalization': 10,
    'preference': 10,
    'settings': 10,
    'design': 10,
    'aesthetic': 10,
    'creativity': 75,
    'experiment': 75,
    'invention': 75,
    'design_creative': 75,
    'artistic': 75,
    'originality': 75,
    'uniqueness': 75,
    'system': 20,
    'meta': 20,
    'feedback': 20,
    'bug_report': 20,
    'feature_request': 20,
    'beta_test': 20,
    'quality_assurance': 20,
    'system_contribution': 20,
}

@point_testing_bp.route('/list', methods=['GET'])
def list_all_point_types():
    """List all available point types with their values"""
    try:
        point_types = []
        for point_type, value in sorted(POINT_VALUES.items()):
            point_types.append({
                'point_type': point_type,
                'value': value,
                'test_url': f'/api/test/points/{point_type}/award',
                'description': get_point_type_description(point_type)
            })
        
        # Add category to each point type
        for pt in point_types:
            pt['category'] = get_point_type_category(pt['point_type'])
        
        return jsonify({
            'success': True,
            'total': len(point_types),
            'point_types': point_types
        })
    except Exception as e:
        logger.error(f"Error listing point types: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@point_testing_bp.route('/<point_type>/award', methods=['GET', 'POST'])
def award_points(point_type: str):
    """Award points for a specific point type"""
    try:
        if point_type not in POINT_VALUES:
            return jsonify({
                'success': False,
                'error': f'Point type "{point_type}" not found'
            }), 404
        
        # Get user_id from query params or request body
        user_id = request.args.get('user_id') or (request.get_json() or {}).get('user_id', 'test_user')
        amount = request.args.get('amount') or (request.get_json() or {}).get('amount', POINT_VALUES[point_type])
        
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = POINT_VALUES[point_type]
        
        # Add points using unified points database
        try:
            from backend.services.unified_points_database import unified_points_db
            result = unified_points_db.add_points(
                user_id,
                point_type,
                amount,
                source='point_testing'
            )
            
            # Get updated points
            user_points = unified_points_db.get_user_points(user_id)
            current_points = user_points.get(point_type, 0)
            
            return jsonify({
                'success': True,
                'message': f'Awarded {amount} {point_type} points to {user_id}',
                'point_type': point_type,
                'amount_awarded': amount,
                'current_total': current_points,
                'point_value': POINT_VALUES[point_type],
                'user_id': user_id
            })
        except Exception as points_error:
            logger.error(f"Error adding points: {points_error}")
            return jsonify({
                'success': False,
                'error': f'Failed to add points: {str(points_error)}',
                'point_type': point_type,
                'point_value': POINT_VALUES[point_type]
            }), 500
        
    except Exception as e:
        logger.error(f"Error awarding points: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@point_testing_bp.route('/batch', methods=['POST'])
def award_batch_points():
    """Award points for multiple point types at once"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'test_user')
        point_types = data.get('point_types', [])
        amount_multiplier = data.get('multiplier', 1.0)
        
        results = []
        
        for point_type in point_types:
            if point_type in POINT_VALUES:
                amount = POINT_VALUES[point_type] * amount_multiplier
                try:
                    from backend.services.unified_points_database import unified_points_db
                    unified_points_db.add_points(
                        user_id,
                        point_type,
                        amount,
                        source='point_testing_batch'
                    )
                    results.append({
                        'point_type': point_type,
                        'amount': amount,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'point_type': point_type,
                        'error': str(e),
                        'success': False
                    })
            else:
                results.append({
                    'point_type': point_type,
                    'error': 'Point type not found',
                    'success': False
                })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'results': results,
            'total_awarded': len([r for r in results if r.get('success')])
        })
    except Exception as e:
        logger.error(f"Error in batch award: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@point_testing_bp.route('/all/award', methods=['GET', 'POST'])
def award_all_points():
    """Award points for all point types"""
    try:
        user_id = request.args.get('user_id') or (request.get_json() or {}).get('user_id', 'test_user')
        amount_multiplier = float(request.args.get('multiplier', 1.0) or (request.get_json() or {}).get('multiplier', 1.0))
        
        results = []
        total_awarded = 0
        
        try:
            from backend.services.unified_points_database import unified_points_db
            
            for point_type, base_value in POINT_VALUES.items():
                amount = base_value * amount_multiplier
                try:
                    unified_points_db.add_points(
                        user_id,
                        point_type,
                        amount,
                        source='point_testing_all'
                    )
                    total_awarded += amount
                    results.append({
                        'point_type': point_type,
                        'amount': amount,
                        'success': True
                    })
                except Exception as e:
                    results.append({
                        'point_type': point_type,
                        'error': str(e),
                        'success': False
                    })
            
            return jsonify({
                'success': True,
                'message': f'Awarded points for all {len(POINT_VALUES)} point types',
                'user_id': user_id,
                'total_point_types': len(POINT_VALUES),
                'successful_awards': len([r for r in results if r.get('success')]),
                'total_points_awarded': total_awarded,
                'results': results
            })
        except Exception as e:
            logger.error(f"Error in all points award: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"Error awarding all points: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@point_testing_bp.route('/<point_type>/info', methods=['GET'])
def get_point_type_info(point_type: str):
    """Get information about a specific point type"""
    try:
        if point_type not in POINT_VALUES:
            return jsonify({
                'success': False,
                'error': f'Point type "{point_type}" not found'
            }), 404
        
        return jsonify({
            'success': True,
            'point_type': point_type,
            'point_value': POINT_VALUES[point_type],
            'test_url': f'/api/test/points/{point_type}/award',
            'description': get_point_type_description(point_type),
            'category': get_point_type_category(point_type)
        })
    except Exception as e:
        logger.error(f"Error getting point type info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@point_testing_bp.route('/dashboard', methods=['GET'])
def point_testing_dashboard():
    """Serve the point testing dashboard HTML"""
    from flask import send_from_directory
    from pathlib import Path
    dashboard_dir = Path(__file__).parent.parent.parent / 'vidgenerator' / 'static' / 'html'
    return send_from_directory(str(dashboard_dir), 'point-testing-dashboard.html')

@point_testing_bp.route('/categories', methods=['GET'])
def category_test_dashboard():
    """Serve the category test dashboard HTML"""
    from flask import send_from_directory
    from pathlib import Path
    dashboard_dir = Path(__file__).parent.parent.parent / 'vidgenerator' / 'static' / 'html'
    return send_from_directory(str(dashboard_dir), 'category-test-dashboard.html')

@point_testing_bp.route('/category/<category_name>', methods=['GET'])
def test_category_points(category_name: str):
    """Test all points in a specific category"""
    try:
        user_id = request.args.get('user_id', 'test_user')
        
        # Category to point types mapping
        category_map = {
            'core_engagement': ['xp', 'activity', 'theme', 'chat', 'trophy', 'achievement', 'stats', 'watch_time', 'scroll_depth', 'interaction_quality', 'return_visitor', 'session_duration', 'page_depth', 'content_consumption', 'search', 'filter', 'share', 'bookmark', 'comment', 'rating'],
            'battle_combat': ['battle', 'pvp_battle', 'pve_battle', 'team_battle', 'guild_battle', 'arena_battle', 'tournament', 'ranked_battle', 'casual_battle', 'victory', 'defeat', 'perfect_victory', 'comeback', 'streak_battle', 'first_blood', 'multi_kill', 'assist', 'defense', 'offense', 'tactical', 'strategy', 'combo', 'ultimate', 'death_portal_teleport'],
            'content_creation': ['generation', 'video_generation', 'clip_generation', 'image_generation', 'audio_generation', 'text_generation', 'template_usage', 'custom_creation', 'quality', 'innovation', 'trending', 'viral', 'collaboration', 'remix', 'edit', 'publish', 'schedule', 'series', 'playlist', 'collection', 'production_mastery', 'production_10x'],
            'social_community': ['social', 'friend', 'follow', 'follower', 'message', 'group', 'community', 'event', 'meetup', 'discussion', 'forum', 'help', 'mentor', 'apprentice', 'referral', 'invite', 'gift', 'thank_you', 'recognition', 'celebration', 'community_mastery'],
            'progression_leveling': ['level_up', 'skill', 'mastery', 'prestige', 'rank', 'tier', 'badge', 'medal', 'title', 'achievement_chain', 'milestone', 'progress', 'completion', 'teleport_skillset', 'skillset_mastery', 'death_portal_mastery'],
            'economy_trading': ['shop', 'rewards', 'purchase', 'sale', 'trade', 'auction', 'market', 'currency', 'investment', 'profit', 'deal', 'negotiation', 'collection_value', 'asset', 'wealth', 'production_economy', 'teleport_trade'],
            'exploration_discovery': ['exploration', 'discovery', 'unlock', 'reveal', 'map', 'location', 'hidden', 'secret', 'easter_egg', 'landmark', 'path', 'route'],
            'learning_education': ['learning', 'course', 'lesson', 'quiz', 'test', 'certification', 'knowledge', 'skill_development', 'practice', 'study', 'research', 'education'],
            'events_special': ['event_participation', 'holiday', 'seasonal', 'limited_time', 'special_event', 'anniversary', 'festival', 'competition', 'death_portal_event'],
            'customization_personalization': ['customization', 'avatar', 'theme_custom', 'layout', 'style', 'personalization', 'preference', 'settings', 'design', 'aesthetic'],
            'innovation_creativity': ['creativity', 'experiment', 'invention', 'design_creative', 'artistic', 'originality', 'uniqueness'],
            'meta_system': ['system', 'meta', 'feedback', 'bug_report', 'feature_request', 'beta_test', 'quality_assurance', 'system_contribution']
        }
        
        category_key = category_name.lower().replace(' ', '_').replace('&', '_')
        point_types = category_map.get(category_key, [])
        
        if not point_types:
            return jsonify({
                'success': False,
                'error': f'Category "{category_name}" not found'
            }), 404
        
        # Award points for all types in category
        results = []
        total_awarded = 0
        
        try:
            from backend.services.unified_points_database import unified_points_db
            
            for point_type in point_types:
                if point_type in POINT_VALUES:
                    amount = POINT_VALUES[point_type]
                    unified_points_db.add_points(
                        user_id,
                        point_type,
                        amount,
                        source='category_test'
                    )
                    total_awarded += amount
                    results.append({
                        'point_type': point_type,
                        'amount': amount,
                        'success': True
                    })
            
            return jsonify({
                'success': True,
                'category': category_name,
                'user_id': user_id,
                'point_types_tested': len(results),
                'total_points_awarded': total_awarded,
                'results': results
            })
        except Exception as e:
            logger.error(f"Error testing category: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"Error in category test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_point_type_description(point_type: str) -> str:
    """Get description for a point type"""
    descriptions = {
        'xp': 'Experience points for leveling up',
        'battle': 'Points earned from battles',
        'video_generation': 'Points for generating videos',
        'pvp_battle': 'Player vs Player battle points',
        'pve_battle': 'Player vs Environment battle points',
        'death_portal_teleport': 'Special teleport ability points',
        'production_10x': '10x production multiplier bonus',
        'level_up': 'Points for leveling up',
        'skill': 'Points for skill progression',
        'mastery': 'Points for mastery achievements',
        'exploration': 'Points for exploring new areas',
        'learning': 'Points for learning activities',
        'innovation': 'Points for innovative actions',
        'purchase': 'Points for making purchases',
        'friend': 'Points for adding friends',
        'event_participation': 'Points for event participation',
        'customization': 'Points for customizing profile',
        'system': 'Points for system interactions'
    }
    return descriptions.get(point_type, f'Points earned from {point_type.replace("_", " ")}')

def get_point_type_category(point_type: str) -> str:
    """Get category for a point type"""
    if point_type in ['xp', 'activity', 'theme', 'chat', 'trophy', 'achievement', 'stats', 'watch_time', 'scroll_depth', 'interaction_quality', 'return_visitor', 'session_duration', 'page_depth', 'content_consumption', 'search', 'filter', 'share', 'bookmark', 'comment', 'rating']:
        return 'Core Engagement'
    elif 'battle' in point_type or point_type in ['victory', 'defeat', 'perfect_victory', 'comeback', 'streak_battle', 'first_blood', 'multi_kill', 'assist', 'defense', 'offense', 'tactical', 'strategy', 'combo', 'ultimate']:
        return 'Battle & Combat'
    elif 'generation' in point_type or point_type in ['video_generation', 'clip_generation', 'image_generation', 'audio_generation', 'text_generation', 'template_usage', 'custom_creation', 'quality', 'innovation', 'trending', 'viral', 'collaboration', 'remix', 'edit', 'publish', 'schedule', 'series', 'playlist', 'collection', 'production_mastery', 'production_10x', 'production_economy']:
        return 'Content Creation'
    elif point_type in ['friend', 'follow', 'follower', 'message', 'group', 'community', 'event', 'meetup', 'discussion', 'forum', 'help', 'mentor', 'apprentice', 'referral', 'invite', 'gift', 'thank_you', 'recognition', 'celebration', 'community_mastery', 'social']:
        return 'Social & Community'
    elif point_type in ['level_up', 'skill', 'mastery', 'prestige', 'rank', 'tier', 'badge', 'medal', 'title', 'achievement_chain', 'milestone', 'progress', 'completion', 'skillset_mastery', 'teleport_skillset', 'death_portal_mastery']:
        return 'Progression & Leveling'
    elif point_type in ['purchase', 'sale', 'trade', 'auction', 'market', 'currency', 'investment', 'profit', 'deal', 'negotiation', 'collection_value', 'asset', 'wealth', 'production_economy', 'teleport_trade', 'shop', 'rewards']:
        return 'Economy & Trading'
    elif point_type in ['exploration', 'discovery', 'unlock', 'reveal', 'map', 'location', 'hidden', 'secret', 'easter_egg', 'landmark', 'path', 'route']:
        return 'Exploration & Discovery'
    elif point_type in ['learning', 'course', 'lesson', 'quiz', 'test', 'certification', 'knowledge', 'skill_development', 'practice', 'study', 'research', 'education']:
        return 'Learning & Education'
    elif point_type in ['event_participation', 'holiday', 'seasonal', 'limited_time', 'special_event', 'anniversary', 'festival', 'competition', 'death_portal_event']:
        return 'Events & Special Occasions'
    elif point_type in ['customization', 'avatar', 'theme_custom', 'layout', 'style', 'personalization', 'preference', 'settings', 'design', 'aesthetic']:
        return 'Customization & Personalization'
    elif point_type in ['creativity', 'experiment', 'invention', 'design_creative', 'artistic', 'originality', 'uniqueness', 'innovation']:
        return 'Innovation & Creativity'
    elif point_type in ['system', 'meta', 'feedback', 'bug_report', 'feature_request', 'beta_test', 'quality_assurance', 'system_contribution']:
        return 'Meta & System'
    else:
        return 'Other'
