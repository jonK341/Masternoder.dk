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

# Import systems with error handling
try:
    from src.services.behavioral_tracking.xp_system import XPSystem
    xp_system = XPSystem()
    print("[Stats] XPSystem loaded successfully")
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
    from src.services.behavioral_tracking.trophy_system import TrophySystem
    trophy_system = TrophySystem()
    print("[Stats] TrophySystem loaded successfully")
except ImportError as e:
    print(f"[Stats] Warning: TrophySystem not available: {e}")
    # Create dummy TrophySystem
    class TrophySystem:
        def get_user_trophies(self, user_id): return []
        def get_leveling_milestones(self, user_id): return []
    trophy_system = TrophySystem()

stats_bp = Blueprint('stats', __name__)


def get_user_id():
    """Get user ID from session or generate one"""
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']


@stats_bp.route('/stats')
@stats_bp.route('/stats/')
@stats_bp.route('/vidgenerator/stats')
@stats_bp.route('/vidgenerator/stats/')
def stats_index():
    """Stats and analytics page with frame extraction"""
    try:
        # Try enhanced stats first, fallback to basic
        try:
            return render_template('stats/enhanced_stats.html')
        except:
            return render_template('stats/index.html')
    except Exception as e:
        return f"Error loading stats page: {str(e)}", 500


@stats_bp.route('/api/statistics')
def get_statistics():
    """Get generation statistics including worker skills"""
    try:
        user_id = get_user_id()
        
        # Get documentaries count
        total_docs = Documentary.query.filter_by(status='completed').count()
        
        # Get total duration
        total_duration = db.session.query(db.func.sum(Documentary.duration)).filter_by(status='completed').scalar() or 0
        
        # Get average quality
        avg_quality = db.session.query(db.func.avg(MovieClip.quality_score)).scalar() or 0.0
        
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
        
        stats = {
            'total_documentaries': total_docs,
            'total_duration': int(total_duration),
            'avg_quality': float(avg_quality),
            'total_trophies': total_trophies,
            'xp': {
                'total': total_xp,
                'level': level,
                'breakdown': {
                    'from_generations': xp_from_generations,
                    'from_trophies': xp_from_trophies,
                    'from_milestones': xp_from_milestones,
                    'from_calendar': xp_from_calendar,
                    'from_war_plan': xp_from_war_plan
                }
            }
        }
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        
        return jsonify({
            'success': True,
            'name': 'User',
            'title': title,
            'level': level,
            'xp': total_xp,
            'highScores': {
                'total': total_xp
            }
        })
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
        xp_breakdown = {
            'total': profile.get('total_xp', 0),
            'fromGenerations': sum(e.get('xp_awarded', 0) for e in xp_history if 'generation' in e.get('action_type', '')),
            'fromTrophies': 0,  # TODO: Calculate from trophy awards
            'fromMilestones': 0  # TODO: Calculate from milestone awards
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
        
        # Calculate streaks (simplified - would need proper tracking)
        streaks = 0  # TODO: Implement streak tracking
        
        # Calculate perfect generations (high quality videos)
        perfect_generations = MovieClip.query.filter(MovieClip.quality_score >= 0.9).count()
        
        return jsonify({
            'success': True,
            'level': level,
            'xp': total_xp,
            'videos_created': total_docs,
            'trophies_earned': earned_trophies,
            'streaks': streaks,
            'perfect_generations': perfect_generations,
            'total_watch_time': 0  # TODO: Implement watch time tracking
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
