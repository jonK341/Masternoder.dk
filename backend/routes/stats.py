"""
Stats and Analytics Routes
Includes frame extraction tools moved from generator page
Enhanced with Trophy Hunter, Calendar, Milestones, XP, High Scores
"""
from flask import Blueprint, render_template, jsonify, request, session
from typing import Dict, Any
import os
from datetime import datetime, timedelta
from src.db.models import db, Documentary, MovieClip

# Import caching utility for performance optimization
try:
    from src.utils.query_cache import cached_query
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    def cached_query(ttl=None):
        """Dummy decorator if cache not available"""
        def decorator(func):
            return func
        return decorator

# Import systems with error handling
# Try backend.services first (Micro integration), then src.services (original)
try:
    from backend.services.xp_system import XPSystem
    xp_system = XPSystem()
    print("[Stats] XPSystem loaded successfully from backend.services")
except ImportError:
    try:
        from src.services.behavioral_tracking.xp_system import XPSystem
        xp_system = XPSystem()
        print("[Stats] XPSystem loaded successfully from src.services")
    except ImportError as e:
        print(f"[Stats] Warning: XPSystem not available: {e}")
        # Create dummy XPSystem
        class XPSystem:
            def get_user_profile(self, user_id): return {'level': 1, 'total_xp': 0, 'xp_total': 0}
            def get_xp_history(self, user_id): return []
        xp_system = XPSystem()

# Import defense mechanisms system
try:
    from src.services.defense_mechanisms.defense_engine import DefenseMechanismsEngine
    defense_engine = DefenseMechanismsEngine()
    print("[Stats] DefenseMechanismsEngine loaded successfully")
except ImportError as e:
    print(f"[Stats] Warning: DefenseMechanismsEngine not available: {e}")
    defense_engine = None

try:
    from backend.services.trophy_system import TrophySystem
    trophy_system = TrophySystem()
    print("[Stats] TrophySystem loaded successfully from backend.services")
except ImportError:
    try:
        from src.services.behavioral_tracking.trophy_system import TrophySystem
        trophy_system = TrophySystem()
        print("[Stats] TrophySystem loaded successfully from src.services")
    except ImportError as e:
        print(f"[Stats] Warning: TrophySystem not available: {e}")
        # Create dummy TrophySystem
        class TrophySystem:
            def get_user_trophies(self, user_id): return []
            def get_leveling_milestones(self, user_id): return []
        trophy_system = TrophySystem()

stats_bp = Blueprint('stats', __name__)


# Profile route removed - handled by direct route in app.py to avoid conflicts


def get_user_id():
    """Get user ID from session or generate one"""
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


@stats_bp.route('/stats')
@stats_bp.route('/stats/')
def stats_index():
    """Stats and analytics page with frame extraction"""
    from flask import send_from_directory, Response
    import os
    
    # Try serving from vidgenerator directory first (direct file serve)
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        vidgen_path = os.path.join(base_path, 'vidgenerator', 'stats')
        index_file = os.path.join(vidgen_path, 'index.html')
        
        if os.path.exists(index_file):
            # Read file and return as response
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/html'), 200
    except Exception as file_error:
        print(f"[Stats] File serve error: {file_error}")
    
    # Try template rendering as fallback
    try:
        return render_template('stats/enhanced_stats.html')
    except Exception as template_error:
        print(f"[Stats] Enhanced template error: {template_error}")
    
    try:
        return render_template('stats/index.html')
    except Exception as template_error2:
        print(f"[Stats] Template error: {template_error2}")
    
    # Final fallback HTML
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stats - masternoder.dk</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Statistics & Analytics</h1>
        <p>Stats page - loading...</p>
        <p><a href="/vidgenerator">Back to main page</a></p>
    </body>
    </html>
    """, 200


@stats_bp.route('/api/statistics')
def get_statistics():
    """Get generation statistics including worker skills"""
    try:
        from src.utils.query_cache import cached_query
        
        user_id = get_user_id()
        
        # Cache expensive queries - statistics don't change frequently
        @cached_query(ttl=300)  # Cache for 5 minutes
        def _get_stats_data():
            """Cached function to get statistics data"""
            stats_data = {}
            
            # Get documentaries count - handle database errors gracefully
            try:
                stats_data['total_docs'] = Documentary.query.filter_by(status='completed').count()
            except Exception as e:
                print(f"[Stats] Error getting documentaries count: {e}")
                stats_data['total_docs'] = 0
            
            # Get total duration - handle database errors gracefully
            try:
                stats_data['total_duration'] = db.session.query(db.func.sum(Documentary.duration)).filter_by(status='completed').scalar() or 0
            except Exception as e:
                print(f"[Stats] Error getting total duration: {e}")
                stats_data['total_duration'] = 0
            
            # Get average quality - handle database errors gracefully
            try:
                stats_data['avg_quality'] = db.session.query(db.func.avg(MovieClip.quality_score)).scalar() or 0.0
            except Exception as e:
                print(f"[Stats] Error getting average quality: {e}")
                stats_data['avg_quality'] = 0.0
            
            return stats_data
        
        # Get cached statistics
        stats_data = _get_stats_data()
        total_docs = stats_data['total_docs']
        total_duration = stats_data['total_duration']
        avg_quality = stats_data['avg_quality']
        
        # Get trophies count
        user_trophies = trophy_system.get_user_trophies(user_id)
        total_trophies = len([t for t in user_trophies if t.get('earned', False)])
        
        # Get XP data
        user_profile = xp_system.get_user_profile(user_id)
        total_xp = user_profile.get('total_xp', 0) or user_profile.get('xp_total', 0)
        level = user_profile.get('level', 1)
        xp_history = xp_system.get_xp_history(user_id)
        
        # Calculate XP breakdown
        xp_from_generations = sum(e.get('xp_awarded', 0) for e in xp_history if 'generation' in str(e.get('action_type', '')))
        xp_from_trophies = sum(e.get('xp_awarded', 0) for e in xp_history if 'trophy' in str(e.get('action_type', '')))
        xp_from_milestones = sum(e.get('xp_awarded', 0) for e in xp_history if 'milestone' in str(e.get('action_type', '')))
        xp_from_calendar = sum(e.get('xp_awarded', 0) for e in xp_history if 'calendar' in str(e.get('action_type', '')))
        xp_from_war_plan = sum(e.get('xp_awarded', 0) for e in xp_history if 'war_plan' in str(e.get('action_type', '')))
        
        # Defense mechanisms data
        defense_data = {}
        if defense_engine:
            try:
                # Get defense mechanisms info
                mechanisms = [
                    {'value': mech.value, 'name': mech.value.replace('_', ' ').title(), 
                     'multiplier': defense_engine.base_multipliers.get(mech, 1.0)}
                    for mech in defense_engine.base_multipliers.keys()
                ]
                
                # Get enemy websites
                enemies = defense_engine.get_enemy_websites()
                
                # Get available hacks
                hacks = defense_engine.get_available_hacks()
                
                # Calculate defense points from history (if available)
                defense_actions = [e for e in xp_history if 'defense' in str(e.get('action_type', '')).lower()]
                hack_actions = [e for e in xp_history if 'hack' in str(e.get('action_type', '')).lower()]
                
                # Recalculate total points if we have defense/hack actions
                if defense_actions or hack_actions:
                    total_points_result = defense_engine.calculate_total_user_points(
                        defense_actions=defense_actions,
                        hack_actions=hack_actions,
                        base_xp=total_xp
                    )
                    defense_data = {
                        'mechanisms': mechanisms,
                        'enemies': enemies,
                        'hacks': hacks,
                        'defense_actions_count': len(defense_actions),
                        'hack_actions_count': len(hack_actions),
                        'total_points_breakdown': total_points_result,
                        'defense_points': total_points_result.get('defense_points', 0),
                        'hack_points': total_points_result.get('hack_points', 0),
                        'activity_bonus': total_points_result.get('activity_bonus', 0),
                        'diversity_bonus': total_points_result.get('diversity_bonus', 0),
                    }
                else:
                    defense_data = {
                        'mechanisms': mechanisms,
                        'enemies': enemies,
                        'hacks': hacks,
                        'defense_actions_count': 0,
                        'hack_actions_count': 0,
                    }
            except Exception as e:
                print(f"[Stats] Error loading defense data: {e}")
                defense_data = {}
        
        # Get category statistics
        category_stats = {}
        try:
            from src.services.content_categories import content_category_service
            categories = content_category_service.get_all_categories()
            for category in categories:
                cat_id = category.get('id')
                cat_stats = content_category_service.get_category_stats(cat_id, user_id)
                category_stats[cat_id] = {
                    'name': category.get('name_da', category.get('name')),
                    'documentaries_created': cat_stats.get('documentaries_created', 0),
                    'documentaries_completed': cat_stats.get('documentaries_completed', 0),
                    'total_views': cat_stats.get('total_views', 0),
                    'average_quality': cat_stats.get('average_quality', 0.0)
                }
        except Exception as cat_err:
            print(f"[Stats] Error loading category stats: {cat_err}")
            category_stats = {}
        
        # Get game achievements stats points
        stats_points = 0
        achievements_count = 0
        milestones_count = 0
        game_stats = {}
        trophy_points = 0
        milestone_points = 0
        try:
            from backend.services.game_achievements import game_achievement_system
            if game_achievement_system:
                # Calculate user stats for achievements
                user_stats = _calculate_user_stats_for_achievements(user_id)
                result = game_achievement_system.update_user_stats(user_id, user_stats)
                stats_points = result.get('total_stats_points', 0)
                achievements_count = len([a for a in game_achievement_system.get_user_achievements(user_id) if a.get('earned', False)])
                milestones_count = len([m for m in game_achievement_system.get_user_milestones(user_id) if m.get('reached', False)])
                
                # Calculate trophy points from trophy system
                try:
                    trophy_points = trophy_system.get_user_trophy_points(user_id) if hasattr(trophy_system, 'get_user_trophy_points') else 0
                except Exception as e:
                    print(f"[Stats] Error getting trophy points: {e}")
                    trophy_points = 0
                
                # Calculate milestone points from milestones
                try:
                    user_milestones = game_achievement_system.get_user_milestones(user_id)
                    milestone_points = sum(
                        m.get('points', 0) for m in user_milestones if m.get('reached', False) or m.get('earned', False)
                    )
                except Exception as e:
                    print(f"[Stats] Error getting milestone points: {e}")
                    milestone_points = 0
                
                # Add trophy and milestone points to stats_points
                stats_points = stats_points + trophy_points + milestone_points
                
                # Get game stats from hunters leveling system
                try:
                    from backend.services.hunters_leveling_system import hunters_leveling_system
                    if hunters_leveling_system:
                        player_stats = hunters_leveling_system.get_player_stats(user_id)
                        game_stats = {
                            'creativity': player_stats.get('creativity', 0),
                            'efficiency': player_stats.get('efficiency', 0),
                            'quality': player_stats.get('quality', 0),
                            'social': player_stats.get('social', 0),
                            'knowledge': player_stats.get('knowledge', 0),
                            'total_stats_points': player_stats.get('total_stats_points', 0),
                            'available_points': player_stats.get('available_points', 0)
                        }
                except Exception as game_err:
                    print(f"[Stats] Error loading game stats: {game_err}")
                    game_stats = {}
        except Exception as ach_err:
            print(f"[Stats] Error loading achievements stats: {ach_err}")
        
        # Get event updates and participation
        event_data = {
            'active_events': [],
            'event_xp_bonus': 0,
            'events_participated': 0,
            'event_rewards_earned': 0
        }
        try:
            from backend.services.events_system import events_system
            if events_system:
                # Get active events
                active_events = events_system.get_active_events()
                event_data['active_events'] = [
                    {
                        'id': event.get('id'),
                        'name': event.get('name'),
                        'type': event.get('type'),
                        'xp_multiplier': event.get('xp_multiplier', 1.0),
                        'time_remaining': event.get('time_remaining', 0)
                    }
                    for event in active_events
                ]
                
                # Get user's event participation
                user_events = events_system.get_user_events(user_id)
                event_data['events_participated'] = len(user_events)
                
                # Calculate event XP bonus from active events
                for event in active_events:
                    if event.get('type') == 'double_xp':
                        event_data['event_xp_bonus'] = max(event_data['event_xp_bonus'], event.get('xp_multiplier', 1.0))
                
                # Calculate event rewards earned
                event_data['event_rewards_earned'] = sum(
                    event.get('rewards_earned', 0) for event in user_events
                )
                
                # Add event XP to breakdown
                xp_from_events = sum(
                    e.get('xp_awarded', 0) for e in xp_history 
                    if 'event' in str(e.get('action_type', '')).lower()
                )
        except Exception as event_err:
            print(f"[Stats] Error loading event data: {event_err}")
            event_data = {
                'active_events': [],
                'event_xp_bonus': 1.0,
                'events_participated': 0,
                'event_rewards_earned': 0
            }
            xp_from_events = 0
        
        # Update XP breakdown to include events
        xp_breakdown = {
            'from_generations': xp_from_generations,
            'from_trophies': xp_from_trophies,
            'from_milestones': xp_from_milestones,
            'from_calendar': xp_from_calendar,
            'from_war_plan': xp_from_war_plan,
            'from_events': xp_from_events
        }
        
        # Calculate balanced total stats points (combining game stats with achievements)
        balanced_stats_points = stats_points
        if game_stats:
            balanced_stats_points = max(
                stats_points,
                game_stats.get('total_stats_points', 0)
            )
        
        # Calculate streak tracking
        current_streak = 0
        longest_streak = 0
        try:
            from src.db.models import DailyActivity
            from datetime import date, timedelta
            today = date.today()
            activity = DailyActivity.query.filter_by(
                user_id=user_id,
                activity_date=today
            ).first()
            if activity:
                current_streak = activity.streak or 0
            else:
                # Check latest activity for streak
                latest_activity = DailyActivity.query.filter_by(
                    user_id=user_id
                ).order_by(DailyActivity.activity_date.desc()).first()
                if latest_activity:
                    yesterday = date.today() - timedelta(days=1)
                    if latest_activity.activity_date == yesterday:
                        current_streak = latest_activity.streak or 0
                    else:
                        current_streak = 0
            # Get longest streak from all activities
            all_activities = DailyActivity.query.filter_by(user_id=user_id).all()
            if all_activities:
                longest_streak = max((a.streak or 0) for a in all_activities)
        except Exception as streak_err:
            print(f"[Stats] Error calculating streak: {streak_err}")
            current_streak = 0
            longest_streak = 0
        
        # Calculate watch time tracking
        total_watch_time = 0
        try:
            from src.db.models import ViewerSession, ViewerInteraction
            # Get total watch time from ViewerSession
            watch_sessions = db.session.query(
                db.func.sum(ViewerSession.watch_time)
            ).join(
                Documentary, ViewerSession.documentary_id == Documentary.id
            ).filter(
                Documentary.status == 'completed'
            ).scalar()
            total_watch_time = int(watch_sessions) if watch_sessions else 0
            
            # Also check ViewerInteraction for additional watch time
            interactions = db.session.query(
                db.func.sum(ViewerInteraction.duration)
            ).join(
                Documentary, ViewerInteraction.documentary_id == Documentary.id
            ).filter(
                Documentary.status == 'completed'
            ).scalar()
            if interactions:
                total_watch_time += int(interactions)
        except Exception as watch_err:
            print(f"[Stats] Error calculating watch time: {watch_err}")
            total_watch_time = 0
        
        stats = {
            'total_documentaries': total_docs,
            'total_duration': int(total_duration),
            'avg_quality': float(avg_quality),
            'total_trophies': total_trophies,
            'xp': {
                'total': total_xp,
                'level': level,
                'breakdown': xp_breakdown,
                'event_bonus': event_data.get('event_xp_bonus', 1.0)
            },
            'categories': category_stats,
            'stats_points': balanced_stats_points,
            'game_stats': game_stats,
            'achievements_earned': achievements_count,
            'milestones_reached': milestones_count,
            'events': event_data,
            'streak': {
                'current': current_streak,
                'longest': longest_streak
            },
            'watch_time': {
                'total_seconds': total_watch_time,
                'total_minutes': total_watch_time // 60,
                'total_hours': total_watch_time // 3600
            },
            'trophy_points': trophy_points,
            'milestone_points': milestone_points
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[Stats] Error in get_statistics: {e}")
        print(f"[Stats] Traceback: {error_trace}")
        # Return success with default values instead of 500
        return jsonify({
            'success': True,
            'statistics': {
                'total_documentaries': 0,
                'total_duration': 0,
                'avg_quality': 0.0,
                'total_trophies': 0,
                'xp': {'total': 0, 'level': 1, 'breakdown': {}},
                'categories': {},
                'stats_points': 0,
                'achievements_earned': 0,
                'milestones_reached': 0
            },
            'error': str(e) if str(e) else None
        }), 200


@stats_bp.route('/api/worker-skills')
@stats_bp.route('/api/stats/worker-skills')
def get_worker_skills():
    """Get service worker skills and performance statistics"""
    try:
        # Note: Worker skills are stored client-side in localStorage
        # This endpoint provides a way to retrieve them if needed
        # In a real implementation, you might store this in the database
        
        return jsonify({
            'success': True,
            'message': 'Worker skills are tracked client-side. Use localStorage.getItem("worker_skills_stats") to retrieve.',
            'note': 'Worker skills include: web_research, search_intelligence, image_intelligence, sound_intelligence, etc.',
            'skills': {}  # Empty for now, would be populated from database in real implementation
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/api/stats/profile')
def get_profile():
    """Get user profile data"""
    try:
        user_id = get_user_id()
        profile = xp_system.get_user_profile(user_id)
        
        # Get user level and title
        level = profile.get('level', 1)
        total_xp = profile.get('total_xp', 0)
        
        # Calculate title based on level
        titles = {
            1: 'Novice Creator',
            5: 'Rising Star',
            10: 'Experienced Filmmaker',
            20: 'Master Creator',
            30: 'Legendary Director',
            50: 'Cinematic Genius'
        }
        title = 'Novice Creator'
        for threshold, t in sorted(titles.items(), reverse=True):
            if level >= threshold:
                title = t
                break
        
        profile_data = {
            'success': True,
            'name': 'User',
            'title': title,
            'level': level,
            'xp': total_xp,
            'highScores': {
                'total': total_xp
            }
        }
        
        # Enhance profile with future tech and calculator
        try:
            from backend.services.future_tech_integration_service import future_tech_integration_service
            profile_data = future_tech_integration_service.enhance_profile_data(user_id, profile_data)
        except Exception as e:
            print(f"[Stats] Error enhancing profile: {e}")
        
        return jsonify(profile_data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/api/stats/trophies')
def get_trophies():
    """Get trophies for current week and all time"""
    try:
        user_id = get_user_id()
        week_start = request.args.get('week')
        
        if week_start:
            week_date = datetime.fromisoformat(week_start.replace('Z', '+00:00'))
        else:
            week_date = datetime.utcnow()
            # Get Monday of current week
            days_since_monday = week_date.weekday()
            week_date = week_date - timedelta(days=days_since_monday)
        
        # Get all user trophies
        all_trophies = trophy_system.get_user_trophies(user_id)
        
        # Filter weekly trophies (earned this week)
        week_end = week_date + timedelta(days=7)
        weekly_trophies = [
            t for t in all_trophies
            if t.get('earned') and t.get('earnedDate')
            and week_date <= datetime.fromisoformat(t['earnedDate'].replace('Z', '+00:00')) < week_end
        ]
        
        return jsonify({
            'success': True,
            'weekly': weekly_trophies,
            'allTime': all_trophies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/api/stats/milestones')
def get_milestones():
    """Get milestones and progress"""
    try:
        user_id = get_user_id()
        profile = xp_system.get_user_profile(user_id)
        level = profile.get('level', 1)
        
        # Get milestones from trophy system
        milestones_data = trophy_system.get_leveling_milestones(user_id)
        
        # Calculate progress (percentage to next milestone)
        next_milestone = next((m for m in milestones_data if not m.get('completed', False)), None)
        if next_milestone:
            progress = (level / next_milestone.get('level_required', 100)) * 100
        else:
            progress = 100
        
        return jsonify({
            'success': True,
            'milestones': milestones_data,
            'progress': min(progress, 100)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/api/stats/xp-scores')
def get_xp_scores():
    """Get XP breakdown and high scores"""
    try:
        user_id = get_user_id()
        profile = xp_system.get_user_profile(user_id)
        
        # Get XP breakdown
        xp_history = xp_system.get_xp_history(user_id)
        
        # Calculate XP from trophies - check XP history for trophy-related entries
        from_trophies = sum(
            e.get('xp_awarded', 0) for e in xp_history 
            if 'trophy' in e.get('action_type', '').lower() or 'achievement' in e.get('action_type', '').lower()
        )
        
        # If no trophy XP in history, try to get from trophy system points
        if from_trophies == 0:
            try:
                from backend.services.trophy_system import trophy_system
                trophy_points = trophy_system.get_user_trophy_points(user_id)
                # Convert trophy points to XP (10 XP per trophy point)
                from_trophies = trophy_points * 10
            except Exception as e:
                print(f"[Stats] Error calculating trophy XP: {e}")
        
        # Calculate XP from milestones - check XP history for milestone-related entries
        from_milestones = sum(
            e.get('xp_awarded', 0) for e in xp_history 
            if 'milestone' in e.get('action_type', '').lower()
        )
        
        # If no milestone XP in history, try to get from game achievements system
        if from_milestones == 0:
            try:
                from backend.services.game_achievements import game_achievement_system
                user_milestones = game_achievement_system.get_user_milestones(user_id)
                # Sum points from earned milestones and convert to XP
                milestone_points = sum(
                    m.get('points', 0) for m in user_milestones if m.get('earned', False)
                )
                # Convert milestone points to XP (10 XP per point)
                from_milestones = milestone_points * 10
            except Exception as e:
                print(f"[Stats] Error calculating milestone XP: {e}")
        
        xp_breakdown = {
            'total': profile.get('total_xp', 0),
            'fromGenerations': sum(e.get('xp_awarded', 0) for e in xp_history if 'generation' in e.get('action_type', '')),
            'fromTrophies': from_trophies,
            'fromMilestones': from_milestones
        }
        
        # Get high scores
        high_scores = {
            'bestQuality': 0.0,
            'longestVideo': 0,
            'mostClips': 0,
            'fastestGeneration': None
        }
        
        # Query database for high scores
        best_quality_clip = MovieClip.query.order_by(MovieClip.quality_score.desc()).first()
        if best_quality_clip:
            high_scores['bestQuality'] = float(best_quality_clip.quality_score or 0.0)
        
        longest_doc = Documentary.query.filter_by(status='completed').order_by(Documentary.duration.desc()).first()
        if longest_doc:
            high_scores['longestVideo'] = int(longest_doc.duration or 0)
        
        # Count clips for user's documentaries
        user_docs = Documentary.query.filter_by(status='completed').all()
        if user_docs:
            doc_ids = [doc.id for doc in user_docs]
            clip_count = MovieClip.query.filter(MovieClip.documentary_id.in_(doc_ids)).count()
            high_scores['mostClips'] = clip_count
        
        return jsonify({
            'success': True,
            'xp': xp_breakdown,
            'highScores': high_scores
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@stats_bp.route('/api/stats/user')
def get_user():
    """Get user data for game mode"""
    try:
        user_id = get_user_id()
        profile = xp_system.get_user_profile(user_id)
        
        level = profile.get('level', 1)
        total_xp = profile.get('total_xp', 0)
        
        # Get game stats
        total_docs = Documentary.query.filter_by(status='completed').count()
        user_trophies = trophy_system.get_user_trophies(user_id)
        earned_trophies = len([t for t in user_trophies if t.get('earned', False)])
        
        # Calculate streaks from DailyActivity
        from src.db.models import DailyActivity
        from datetime import date, timedelta
        
        today = date.today()
        activity = DailyActivity.query.filter_by(
            user_id=user_id,
            activity_date=today
        ).first()
        
        if activity:
            streaks = activity.streak
        else:
            # Check if user has any activity
            latest_activity = DailyActivity.query.filter_by(
                user_id=user_id
            ).order_by(DailyActivity.activity_date.desc()).first()
            
            if latest_activity:
                # Check if streak is still valid (logged in yesterday)
                yesterday = date.today() - timedelta(days=1)
                if latest_activity.activity_date == yesterday:
                    streaks = latest_activity.streak
                else:
                    streaks = 0
            else:
                streaks = 0
        
        # Calculate perfect generations (high quality videos)
        perfect_generations = MovieClip.query.filter(MovieClip.quality_score >= 0.9).count()
        
        # Calculate total watch time from ViewerSession
        from src.db.models import ViewerSession
        total_watch_time = 0
        try:
            # Get all viewer sessions for completed documentaries
            # Note: In a real multi-user system, you'd filter by user_id
            # For now, we'll sum all watch time from all sessions
            watch_sessions = db.session.query(
                db.func.sum(ViewerSession.watch_time)
            ).join(
                Documentary, ViewerSession.documentary_id == Documentary.id
            ).filter(
                Documentary.status == 'completed'
            ).scalar()
            
            total_watch_time = int(watch_sessions) if watch_sessions else 0
        except Exception as e:
            print(f"[Stats] Error calculating watch time: {e}")
            total_watch_time = 0
        
        return jsonify({
            'success': True,
            'level': level,
            'xp': total_xp,
            'videos_created': total_docs,
            'trophies_earned': earned_trophies,
            'streaks': streaks,
            'perfect_generations': perfect_generations,
            'total_watch_time': total_watch_time
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _calculate_user_stats_for_achievements(user_id: str) -> dict:
    """Calculate user statistics for achievements system"""
    try:
        # Get all completed documentaries (simplified - assumes all are for this user)
        total_videos = Documentary.query.filter_by(status='completed').count()
        
        # Videos by category
        category_videos = {}
        categories = ['underholdning', 'porn', 'rettigheder']
        for cat in categories:
            count = Documentary.query.filter_by(
                status='completed',
                category_name=cat
            ).count()
            category_videos[cat] = count
        
        # Videos created today
        today = datetime.utcnow().date()
        videos_today = Documentary.query.filter(
            Documentary.status == 'completed',
            db.func.date(Documentary.created_at) == today
        ).count()
        
        # Quality stats (simplified - would need MovieClip for actual quality scores)
        from src.db.models import MovieClip
        high_quality_videos = MovieClip.query.filter(MovieClip.quality_score >= 0.8).count()
        has_perfect_quality = MovieClip.query.filter(MovieClip.quality_score >= 1.0).count() > 0
        
        # Average quality
        avg_quality_result = db.session.query(db.func.avg(MovieClip.quality_score)).scalar()
        avg_quality = float(avg_quality_result) if avg_quality_result else 0.0
        
        return {
            'total_videos': total_videos,
            'category_videos': category_videos,
            'videos_today': videos_today,
            'high_quality_videos': high_quality_videos,
            'has_perfect_quality': has_perfect_quality,
            'avg_quality': avg_quality
        }
    except Exception as e:
        print(f"[Stats] Error calculating user stats: {e}")
        return {
            'total_videos': 0,
            'category_videos': {},
            'videos_today': 0,
            'high_quality_videos': 0,
            'has_perfect_quality': False,
            'avg_quality': 0.0
        }


@stats_bp.route('/api/stats/frames')
def get_frames():
    """Get extracted frames for frames gallery"""
    try:
        user_id = get_user_id()
        
        # Get frames from documentaries
        frames = []
        
        # Query completed documentaries
        docs = Documentary.query.filter_by(status='completed').order_by(Documentary.created_at.desc()).limit(50).all()
        
        for doc in docs:
            # Check if documentary has frames extracted
            # In a real implementation, frames would be stored in a separate table
            # For now, we'll use thumbnail or video path to generate frame info
            
            if doc.thumbnail_path:
                frames.append({
                    'id': f"frame_{doc.id}",
                    'title': doc.title or 'Untitled',
                    'source': 'Documentary',
                    'url': f"/static/{doc.thumbnail_path}" if not doc.thumbnail_path.startswith('/') else doc.thumbnail_path,
                    'date': doc.created_at.strftime('%Y-%m-%d') if doc.created_at else 'Unknown',
                    'documentary_id': doc.id
                })
        
        return jsonify({
            'success': True,
            'frames': frames,
            'count': len(frames)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'frames': []
        }), 500


@stats_bp.route('/api/stats/leaderboard')
def get_leaderboard():
    """Get leaderboard data for game mode"""
    try:
        # Get all users with their stats
        # In a real implementation, this would query a user_stats table
        # For now, we'll use session-based user IDs and aggregate stats
        
        leaderboard = []
        
        # Get top users by XP (simplified - would need proper user tracking)
        # For now, return current user's position
        user_id = get_user_id()
        profile = xp_system.get_user_profile(user_id)
        
        # Get user's documentaries count
        total_docs = Documentary.query.filter_by(status='completed').count()
        
        # Calculate score (combination of level, XP, and videos)
        score = (profile.get('level', 1) * 1000) + profile.get('total_xp', 0) + (total_docs * 100)
        
        leaderboard.append({
            'name': 'You',
            'level': profile.get('level', 1),
            'xp': profile.get('total_xp', 0),
            'score': score,
            'videos': total_docs
        })
        
        # In a real implementation, you would:
        # 1. Query all users from database
        # 2. Calculate scores for each
        # 3. Sort by score
        # 4. Return top N users
        
        # Sort by score (descending)
        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'user_position': 1  # Current user's position
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 500


def register_stats_routes(app):
    """Register stats routes with Flask app"""
    app.register_blueprint(stats_bp)
    print("[Routes] Stats routes registered")
