"""
Generation Tracker - Integrates XP and Trophy systems with video generation
Tracks user actions and awards XP/trophies when videos are generated
"""
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

# Import systems with error handling
try:
    from src.services.behavioral_tracking.xp_system import XPSystem
    xp_system = XPSystem()
except ImportError:
    print("[GenerationTracker] Warning: XPSystem not available")
    xp_system = None

try:
    from src.services.behavioral_tracking.trophy_system import TrophySystem
    trophy_system = TrophySystem()
except ImportError:
    print("[GenerationTracker] Warning: TrophySystem not available")
    trophy_system = None


def get_user_id_from_request(request) -> str:
    """Extract user ID from Flask request"""
    try:
        from flask import session
        if 'user_id' in session:
            return session['user_id']
    except:
        pass
    
    # Fallback: use IP or generate ID
    try:
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        if not client_ip:
            client_ip = request.remote_addr or 'unknown'
        return f"user_{client_ip.replace('.', '_').replace(':', '_')}"
    except:
        return "user_anonymous"


def track_generation_start(user_id: str, doc_id: str, prompt: str, metadata: Dict = None) -> None:
    """Track when generation starts"""
    if not xp_system:
        return
    
    try:
        if metadata is None:
            metadata = {}
        
        metadata['doc_id'] = doc_id
        metadata['prompt_length'] = len(prompt) if prompt else 0
        
        xp_system.track_action(
            user_id=user_id,
            action_type='generate_video',
            metadata=metadata
        )
        print(f"[GenerationTracker] Tracked generation start for user {user_id}, doc {doc_id}")
    except Exception as e:
        print(f"[GenerationTracker] Error tracking generation start: {e}")
        traceback.print_exc()


def track_generation_complete(
    user_id: str,
    doc_id: str,
    success: bool,
    video_path: str = None,
    duration: int = None,
    quality_score: float = None,
    metadata: Dict = None
) -> Dict[str, Any]:
    """Track when generation completes and award XP/trophies"""
    if not xp_system:
        return {'xp_awarded': 0, 'trophies_awarded': []}
    
    if metadata is None:
        metadata = {}
    
    result = {
        'xp_awarded': 0,
        'trophies_awarded': [],
        'level_up': False,
        'new_title': None
    }
    
    try:
        if success:
            # Award XP for completing generation
            xp_metadata = {
                'doc_id': doc_id,
                'duration': duration or 0,
                'quality_score': quality_score or 0.0,
                'video_path': video_path or '',
                **metadata
            }
            
            xp_awarded = xp_system.track_action(
                user_id=user_id,
                action_type='complete_generation',
                metadata=xp_metadata
            )
            result['xp_awarded'] = xp_awarded
            
            # Get user profile to check for level up
            profile = xp_system.get_user_profile(user_id)
            old_level = metadata.get('old_level', profile.get('level', 1))
            new_level = profile.get('level', 1)
            
            if new_level > old_level:
                result['level_up'] = True
                result['new_level'] = new_level
                # Get new title if available
                title_info = profile.get('title', {})
                result['new_title'] = title_info.get('current', 'Novice')
                print(f"[GenerationTracker] User {user_id} leveled up to {new_level}!")
                
                # Check for graduation points at milestone
                try:
                    from src.services.behavioral_tracking.graduation_points import graduation_points_system
                    graduation_result = graduation_points_system.check_milestone_graduation(user_id, new_level)
                    if graduation_result:
                        result['graduation_points'] = graduation_result
                        print(f"[GenerationTracker] User {user_id} earned {graduation_result['graduation_points_awarded']} graduation points!")
                except Exception as grad_error:
                    print(f"[GenerationTracker] Error checking graduation points: {grad_error}")
            
            # Check and award trophies
            if trophy_system:
                try:
                    # Get generation count from profile
                    behavioral = profile.get('behavioral', {})
                    total_generations = behavioral.get('total_generations', 0)
                    
                    trophy_metadata = {
                        'total_generations': total_generations,
                        'quality_score': quality_score or 0.0,
                        'duration': duration or 0,
                        'video_path': video_path or ''
                    }
                    
                    newly_awarded = trophy_system.check_and_award_trophies(
                        user_id=user_id,
                        action_type='complete_generation',
                        metadata=trophy_metadata
                    )
                    
                    result['trophies_awarded'] = newly_awarded
                    
                    if newly_awarded:
                        print(f"[GenerationTracker] User {user_id} earned {len(newly_awarded)} trophies!")
                        for trophy in newly_awarded:
                            print(f"  - {trophy.get('name', 'Unknown')} ({trophy.get('points', 0)} points)")
                except Exception as trophy_error:
                    print(f"[GenerationTracker] Error awarding trophies: {trophy_error}")
                    traceback.print_exc()
        else:
            # Award smaller XP for attempting (even if failed)
            xp_system.track_action(
                user_id=user_id,
                action_type='retry_generation',
                metadata={'doc_id': doc_id, **metadata}
            )
        
        print(f"[GenerationTracker] Tracked generation complete for user {user_id}, doc {doc_id}, success={success}")
        
    except Exception as e:
        print(f"[GenerationTracker] Error tracking generation complete: {e}")
        traceback.print_exc()
    
    return result


def get_user_generation_stats(user_id: str) -> Dict[str, Any]:
    """Get user's generation statistics"""
    if not xp_system:
        return {
            'total_xp': 0,
            'level': 1,
            'total_generations': 0,
            'total_trophies': 0
        }
    
    try:
        profile = xp_system.get_user_profile(user_id)
        behavioral = profile.get('behavioral', {})
        
        total_trophies = 0
        if trophy_system:
            trophies = trophy_system.get_user_trophies(user_id)
            total_trophies = len([t for t in trophies if t.get('earned', False)])
        
        return {
            'total_xp': behavioral.get('total_xp', 0),
            'level': behavioral.get('level', 1),
            'total_generations': behavioral.get('total_generations', 0),
            'total_trophies': total_trophies,
            'engagement_score': behavioral.get('engagement_score', 0.0),
            'title': profile.get('title', {}).get('current', 'Novice')
        }
    except Exception as e:
        print(f"[GenerationTracker] Error getting user stats: {e}")
        return {
            'total_xp': 0,
            'level': 1,
            'total_generations': 0,
            'total_trophies': 0
        }

