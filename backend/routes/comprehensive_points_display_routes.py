"""
Comprehensive Points Display Routes
Returns all points from all unified categories in structured format for tables and grids
"""
from flask import Blueprint, request, jsonify
from backend.services.unified_point_system_reconstructed import unified_point_system
from src.utils.rate_limiter import rate_limit
import sys

comprehensive_points_display_bp = Blueprint('comprehensive_points_display', __name__)


@comprehensive_points_display_bp.route('/api/points/comprehensive', methods=['GET'])
@comprehensive_points_display_bp.route('/vidgenerator/api/points/comprehensive', methods=['GET'])
@rate_limit()
def get_comprehensive_points():
    """Get comprehensive points from all categories structured for tables and grids"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Get all points from unified system
        all_points = unified_point_system.get_user_points(user_id, force_refresh=force_refresh)
        
        # Structure points by category for easy display in tables/grids
        structured_points = {
            'CORE': {
                'name': 'Core Points',
                'icon': '⭐',
                'description': 'Fundamental progression points',
                'points': {
                    'xp': {
                        'label': 'XP',
                        'value': all_points.get('xp', 0),
                        'icon': '💚',
                        'category': 'CORE'
                    },
                    'level': {
                        'label': 'Level',
                        'value': all_points.get('level', 1),
                        'icon': '📈',
                        'category': 'CORE'
                    },
                    'level_progress': {
                        'label': 'Level Progress',
                        'value': all_points.get('level_progress', 0.0) * 100,
                        'icon': '📊',
                        'category': 'CORE',
                        'format': 'percentage'
                    },
                    'prestige': {
                        'label': 'Prestige',
                        'value': all_points.get('prestige', 0),
                        'icon': '👑',
                        'category': 'CORE'
                    }
                },
                'total': sum([
                    all_points.get('xp', 0),
                    all_points.get('level', 0) * 1000,
                    all_points.get('prestige', 0) * 5000
                ])
            },
            'ECONOMY': {
                'name': 'Economy',
                'icon': '💰',
                'description': 'Currency and economic resources',
                'points': {
                    'coins': {
                        'label': 'Coins',
                        'value': all_points.get('coins', 0),
                        'icon': '🪙',
                        'category': 'ECONOMY'
                    },
                    'credits': {
                        'label': 'Credits',
                        'value': all_points.get('credits', 0),
                        'icon': '💳',
                        'category': 'ECONOMY'
                    },
                    'tokens': {
                        'label': 'Tokens',
                        'value': all_points.get('tokens', 0),
                        'icon': '🎫',
                        'category': 'ECONOMY'
                    },
                    'total_earned': {
                        'label': 'Total Earned',
                        'value': all_points.get('total_earned', 0),
                        'icon': '📈',
                        'category': 'ECONOMY'
                    },
                    'total_spent': {
                        'label': 'Total Spent',
                        'value': all_points.get('total_spent', 0),
                        'icon': '📉',
                        'category': 'ECONOMY'
                    }
                },
                'total': all_points.get('total_earned', 0)
            },
            'STATS': {
                'name': 'Character Stats',
                'icon': '💎',
                'description': 'Character attribute points',
                'points': {
                    'creativity': {
                        'label': 'Creativity',
                        'value': all_points.get('creativity', 0),
                        'icon': '🎨',
                        'category': 'STATS'
                    },
                    'efficiency': {
                        'label': 'Efficiency',
                        'value': all_points.get('efficiency', 0),
                        'icon': '⚡',
                        'category': 'STATS'
                    },
                    'quality': {
                        'label': 'Quality',
                        'value': all_points.get('quality', 0),
                        'icon': '✨',
                        'category': 'STATS'
                    },
                    'knowledge': {
                        'label': 'Knowledge',
                        'value': all_points.get('knowledge', 0),
                        'icon': '📚',
                        'category': 'STATS'
                    },
                    'social': {
                        'label': 'Social',
                        'value': all_points.get('social', 0),
                        'icon': '👥',
                        'category': 'STATS'
                    },
                    'stats_total': {
                        'label': 'Total Stats',
                        'value': all_points.get('stats_total', 0),
                        'icon': '📊',
                        'category': 'STATS'
                    },
                    'stats_available': {
                        'label': 'Available Points',
                        'value': all_points.get('stats_available', 0),
                        'icon': '➕',
                        'category': 'STATS'
                    }
                },
                'total': sum([
                    all_points.get('creativity', 0),
                    all_points.get('efficiency', 0),
                    all_points.get('quality', 0),
                    all_points.get('knowledge', 0),
                    all_points.get('social', 0)
                ])
            },
            'ACHIEVEMENTS': {
                'name': 'Achievements',
                'icon': '🏆',
                'description': 'Achievement and milestone points',
                'points': {
                    'achievements': {
                        'label': 'Achievements',
                        'value': all_points.get('achievements', 0),
                        'icon': '🏅',
                        'category': 'ACHIEVEMENTS'
                    },
                    'achievement_points': {
                        'label': 'Achievement Points',
                        'value': all_points.get('achievement_points', 0),
                        'icon': '⭐',
                        'category': 'ACHIEVEMENTS'
                    },
                    'trophies': {
                        'label': 'Trophies',
                        'value': all_points.get('trophies', 0),
                        'icon': '🏆',
                        'category': 'ACHIEVEMENTS'
                    },
                    'trophy_points': {
                        'label': 'Trophy Points',
                        'value': all_points.get('trophy_points', 0),
                        'icon': '💎',
                        'category': 'ACHIEVEMENTS'
                    },
                    'milestones': {
                        'label': 'Milestones',
                        'value': all_points.get('milestones', 0),
                        'icon': '🎯',
                        'category': 'ACHIEVEMENTS'
                    },
                    'milestone_points': {
                        'label': 'Milestone Points',
                        'value': all_points.get('milestone_points', 0),
                        'icon': '📈',
                        'category': 'ACHIEVEMENTS'
                    }
                },
                'total': sum([
                    all_points.get('achievement_points', 0),
                    all_points.get('trophy_points', 0),
                    all_points.get('milestone_points', 0)
                ])
            },
            'ACTIVITY': {
                'name': 'Activity',
                'icon': '📅',
                'description': 'Activity-based points',
                'points': {
                    'videos_created': {
                        'label': 'Videos Created',
                        'value': all_points.get('videos_created', 0),
                        'icon': '🎬',
                        'category': 'ACTIVITY'
                    },
                    'videos_watched': {
                        'label': 'Videos Watched',
                        'value': all_points.get('videos_watched', 0),
                        'icon': '👁️',
                        'category': 'ACTIVITY'
                    },
                    'videos_shared': {
                        'label': 'Videos Shared',
                        'value': all_points.get('videos_shared', 0),
                        'icon': '📤',
                        'category': 'ACTIVITY'
                    },
                    'generations': {
                        'label': 'Generations',
                        'value': all_points.get('generations', 0),
                        'icon': '🎨',
                        'category': 'ACTIVITY'
                    },
                    'time_played': {
                        'label': 'Time Played (minutes)',
                        'value': all_points.get('time_played', 0),
                        'icon': '⏱️',
                        'category': 'ACTIVITY',
                        'format': 'duration'
                    },
                    'login_streak': {
                        'label': 'Login Streak',
                        'value': all_points.get('login_streak', 0),
                        'icon': '🔥',
                        'category': 'ACTIVITY'
                    },
                    'daily_logins': {
                        'label': 'Daily Logins',
                        'value': all_points.get('daily_logins', 0),
                        'icon': '📆',
                        'category': 'ACTIVITY'
                    }
                },
                'total': all_points.get('generations', 0) * 10 + all_points.get('videos_created', 0) * 5
            },
            'BATTLE': {
                'name': 'Battle',
                'icon': '⚔️',
                'description': 'Battle and combat points',
                'points': {
                    'battle_wins': {
                        'label': 'Battle Wins',
                        'value': all_points.get('battle_wins', 0),
                        'icon': '✅',
                        'category': 'BATTLE'
                    },
                    'battle_losses': {
                        'label': 'Battle Losses',
                        'value': all_points.get('battle_losses', 0),
                        'icon': '❌',
                        'category': 'BATTLE'
                    },
                    'battle_draws': {
                        'label': 'Battle Draws',
                        'value': all_points.get('battle_draws', 0),
                        'icon': '⚖️',
                        'category': 'BATTLE'
                    },
                    'battle_points': {
                        'label': 'Battle Points',
                        'value': all_points.get('battle_points', 0),
                        'icon': '⚔️',
                        'category': 'BATTLE'
                    },
                    'battle_streak': {
                        'label': 'Battle Streak',
                        'value': all_points.get('battle_streak', 0),
                        'icon': '🔥',
                        'category': 'BATTLE'
                    },
                    'total_battles': {
                        'label': 'Total Battles',
                        'value': (
                            all_points.get('battle_wins', 0) +
                            all_points.get('battle_losses', 0) +
                            all_points.get('battle_draws', 0)
                        ),
                        'icon': '🎯',
                        'category': 'BATTLE'
                    }
                },
                'total': all_points.get('battle_points', 0)
            },
            'SOCIAL': {
                'name': 'Social',
                'icon': '👥',
                'description': 'Social interaction points',
                'points': {
                    'friends': {
                        'label': 'Friends',
                        'value': all_points.get('friends', 0),
                        'icon': '🤝',
                        'category': 'SOCIAL'
                    },
                    'followers': {
                        'label': 'Followers',
                        'value': all_points.get('followers', 0),
                        'icon': '👀',
                        'category': 'SOCIAL'
                    },
                    'following': {
                        'label': 'Following',
                        'value': all_points.get('following', 0),
                        'icon': '👤',
                        'category': 'SOCIAL'
                    },
                    'chat_points': {
                        'label': 'Chat Points',
                        'value': all_points.get('chat_points', 0),
                        'icon': '💬',
                        'category': 'SOCIAL'
                    },
                    'chat_messages': {
                        'label': 'Chat Messages',
                        'value': all_points.get('chat_messages', 0),
                        'icon': '📨',
                        'category': 'SOCIAL'
                    },
                    'social_interactions': {
                        'label': 'Social Interactions',
                        'value': all_points.get('social_interactions', 0),
                        'icon': '🔄',
                        'category': 'SOCIAL'
                    }
                },
                'total': all_points.get('chat_points', 0) + all_points.get('social_interactions', 0) * 2
            },
            'METAL': {
                'name': 'Metal Systems',
                'icon': '🔩',
                'description': 'Metal system points',
                'points': {
                    'territory_points': {
                        'label': 'Territory Points',
                        'value': all_points.get('territory_points', 0),
                        'icon': '🗺️',
                        'category': 'METAL'
                    },
                    'territory_level': {
                        'label': 'Territory Level',
                        'value': all_points.get('territory_level', 1),
                        'icon': '📊',
                        'category': 'METAL'
                    },
                    'trophy_hunt_points': {
                        'label': 'Trophy Hunt Points',
                        'value': all_points.get('trophy_hunt_points', 0),
                        'icon': '🏹',
                        'category': 'METAL'
                    }
                },
                'total': all_points.get('territory_points', 0) + all_points.get('trophy_hunt_points', 0)
            },
            'RESOURCES': {
                'name': 'Resources',
                'icon': '⚙️',
                'description': 'Resource generation points',
                'points': {
                    'energy': {
                        'label': 'Energy',
                        'value': all_points.get('resource_energy', 0),
                        'icon': '⚡',
                        'category': 'RESOURCES',
                        'format': 'decimal'
                    },
                    'materials': {
                        'label': 'Materials',
                        'value': all_points.get('resource_materials', 0),
                        'icon': '🔧',
                        'category': 'RESOURCES',
                        'format': 'decimal'
                    },
                    'knowledge': {
                        'label': 'Knowledge Resources',
                        'value': all_points.get('resource_knowledge', 0),
                        'icon': '📖',
                        'category': 'RESOURCES',
                        'format': 'decimal'
                    },
                    'technology': {
                        'label': 'Technology',
                        'value': all_points.get('resource_technology', 0),
                        'icon': '💻',
                        'category': 'RESOURCES',
                        'format': 'decimal'
                    }
                },
                'total': sum([
                    all_points.get('resource_energy', 0),
                    all_points.get('resource_materials', 0),
                    all_points.get('resource_knowledge', 0),
                    all_points.get('resource_technology', 0)
                ])
            }
        }
        
        # Calculate grand total
        grand_total = sum(category['total'] for category in structured_points.values())
        
        # Create flat list for tables
        flat_points_list = []
        for category_key, category_data in structured_points.items():
            for point_key, point_data in category_data['points'].items():
                flat_points_list.append({
                    'id': f"{category_key}_{point_key}",
                    'category': category_key,
                    'category_name': category_data['name'],
                    'category_icon': category_data['icon'],
                    'type': point_key,
                    'label': point_data['label'],
                    'icon': point_data['icon'],
                    'value': point_data['value'],
                    'format': point_data.get('format', 'number')
                })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'categories': structured_points,
            'flat_list': flat_points_list,
            'grand_total': grand_total,
            'total_categories': len(structured_points),
            'total_points': len(flat_points_list),
            'timestamp': all_points.get('last_updated', '')
        }), 200
    except Exception as e:
        print(f"[Comprehensive Points Display] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'categories': {},
            'flat_list': [],
            'grand_total': 0
        }), 200


@comprehensive_points_display_bp.route('/api/points/category/<category>', methods=['GET'])
@comprehensive_points_display_bp.route('/vidgenerator/api/points/category/<category>', methods=['GET'])
@rate_limit()
def get_category_points(category: str):
    """Get points for a specific category"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        # Get category points from unified system
        category_data = unified_point_system.get_category_points(user_id, category)
        
        if not category_data.get('success'):
            return jsonify({
                'success': False,
                'error': category_data.get('error', 'Category not found'),
                'category': category,
                'points': {}
            }), 200
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'category': category,
            'category_data': category_data,
            'timestamp': unified_point_system.get_user_points(user_id).get('last_updated', '')
        }), 200
    except Exception as e:
        print(f"[Comprehensive Points Display Category] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'category': category,
            'points': {}
        }), 200
