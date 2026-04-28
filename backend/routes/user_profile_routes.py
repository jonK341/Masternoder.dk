"""
User Profile Routes
API endpoints for user profiles, onboarding, and agent skills
"""
from flask import Blueprint, jsonify, request, session
from backend.services.user_onboarding import user_onboarding
from backend.services.account_resolution_service import set_session_user
from backend.services.user_agent_skills import user_agent_skills
from backend.services.user_info_scraper import user_info_scraper
from backend.services.user_profile import user_profile
from backend.services.user_location_service import user_location_service

user_profile_bp = Blueprint('user_profile', __name__)


def _resolve_user_id_for_request():
    """Resolve user_id from session, body, or query (for location and similar endpoints)."""
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        data = request.get_json(silent=True) or {}
        return data.get('user_id') or request.args.get('user_id', 'default_user')

# ========== USER CREATION & ONBOARDING ==========

@user_profile_bp.route('/api/user/create', methods=['POST'])
def create_user():
    """Create new user with onboarding"""
    try:
        data = request.get_json() or {}
        
        # Extract request information
        request_data = {
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'language': request.headers.get('Accept-Language', ''),
            'device_fingerprint': data.get('device_fingerprint'),
            'mac_address': data.get('mac_address'),
            'screen_width': data.get('screen_width'),
            'screen_height': data.get('screen_height'),
            'timezone': data.get('timezone'),
            'referral_source': data.get('referral_source', 'direct'),
            'referral_url': data.get('referral_url', ''),
            'landing_page': data.get('landing_page', ''),
            'initial_actions': data.get('initial_actions', []),
            'pages_visited': data.get('pages_visited', []),
            'preferences': data.get('preferences', {})
        }
        
        # Optional user_id override
        user_id = data.get('user_id')
        
        result = user_onboarding.create_new_user(request_data, user_id)
        
        if result.get('success'):
            uid = result.get('user_id') or user_id
            if uid:
                set_session_user(uid)
                # Insert into user_accounts + user_profiles DB tables
                try:
                    from backend.services.user_db_service import ensure_user_account, ensure_user_profile
                    uname = data.get('preferences', {}).get('username', '')
                    db_result = ensure_user_account(
                        uid, username=uname or uid,
                        ip_address=request.remote_addr,
                        device_fingerprint=data.get('device_fingerprint'),
                    )
                    ensure_user_profile(uid, username=uname or uid, preferences=data.get('preferences'))
                    result['db_account'] = db_result
                except Exception:
                    pass
                try:
                    from backend.services.ai_user_controller import on_user_created
                    ai_result = on_user_created(uid, data.get('preferences', {}).get('username', ''))
                    result['ai_onboarding'] = ai_result
                except Exception:
                    pass
            return jsonify(result), 201
        return jsonify(result), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@user_profile_bp.route('/api/user/login', methods=['POST'])
def login_user():
    """Login with user_id in same window. Optional auto-create if missing."""
    try:
        data = request.get_json() or {}
        user_id = (data.get('user_id') or '').strip()
        auto_create = bool(data.get('auto_create', False))

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400

        profile = user_onboarding.get_user_profile(user_id)
        created = False
        if not profile and auto_create:
            create_result = user_onboarding.create_new_user({
                'user_agent': request.headers.get('User-Agent', ''),
                'ip_address': request.remote_addr,
                'language': request.headers.get('Accept-Language', ''),
                'referral_source': data.get('referral_source', 'login_auto_create'),
                'preferences': data.get('preferences', {}),
            }, user_id)
            if not create_result.get('success'):
                return jsonify(create_result), 400
            profile = create_result.get('profile')
            created = True

        if not profile:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        set_session_user(user_id)

        # Ensure user exists in DB (creates on first login, updates last_login on return)
        db_result = {}
        try:
            from backend.services.user_db_service import ensure_user_account, ensure_user_profile
            uname = data.get('preferences', {}).get('username', '')
            db_result = ensure_user_account(
                user_id, username=uname or user_id,
                ip_address=request.remote_addr,
                device_fingerprint=data.get('device_fingerprint'),
            )
            ensure_user_profile(user_id, username=uname or user_id, preferences=data.get('preferences'))
        except Exception:
            pass

        ai_data = {}
        try:
            from backend.services.ai_user_controller import on_user_created, on_user_activity
            if created or db_result.get('created'):
                ai_data = on_user_created(user_id, data.get('preferences', {}).get('username', ''))
            else:
                on_user_activity(user_id, "login")
        except Exception:
            pass

        return jsonify({
            'success': True,
            'user_id': user_id,
            'created': created or db_result.get('created', False),
            'profile': profile,
            'db_account': db_result.get('account'),
            'ai_onboarding': ai_data if (created or db_result.get('created')) else None,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@user_profile_bp.route('/api/user/bind-session', methods=['POST'])
def bind_session():
    """Bind user_id to server session (e.g. when user sets ID via 'Use ID')."""
    try:
        data = request.get_json() or {}
        user_id = (data.get('user_id') or '').strip()
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400
        set_session_user(user_id)
        # Ensure user exists in DB on session bind
        db_result = {}
        try:
            from backend.services.user_db_service import ensure_user_account, ensure_user_profile
            db_result = ensure_user_account(user_id, username=user_id, ip_address=request.remote_addr)
            ensure_user_profile(user_id, username=user_id)
        except Exception:
            pass
        return jsonify({'success': True, 'user_id': user_id, 'db_created': db_result.get('created', False)}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_profile_bp.route('/api/user/profile/<user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get user profile"""
    try:
        profile = user_onboarding.get_user_profile(user_id)
        
        if profile:
            return jsonify({
                'success': True,
                'profile': profile
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'User not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/profile/<user_id>/display', methods=['GET'])
def get_profile_display(user_id):
    """Get profile data formatted for display"""
    try:
        result = user_profile.get_profile_display(user_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            # If user not found, try to create a default profile
            if result.get('error') == 'User not found':
                try:
                    # Create a basic profile for the user
                    create_result = user_onboarding.create_new_user({
                        'user_agent': request.headers.get('User-Agent', ''),
                        'ip_address': request.remote_addr,
                        'language': request.headers.get('Accept-Language', ''),
                        'referral_source': 'direct'
                    }, user_id)
                    
                    if create_result.get('success'):
                        # Retry getting the profile
                        result = user_profile.get_profile_display(user_id)
                        if result.get('success'):
                            return jsonify(result), 200
                
                except Exception as create_error:
                    print(f"Error creating default profile: {create_error}")
            
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/profile/<user_id>/aggregated', methods=['GET'])
def get_profile_aggregated(user_id):
    """Single-call profile: display + activity + agents + achievements + trophies. One request, one loading state."""
    try:
        result = user_profile.get_profile_display(user_id)
        if not result.get('success'):
            if result.get('error') == 'User not found':
                try:
                    create_result = user_onboarding.create_new_user({
                        'user_agent': request.headers.get('User-Agent', ''),
                        'ip_address': request.remote_addr,
                        'language': request.headers.get('Accept-Language', ''),
                        'referral_source': 'direct',
                    }, user_id)
                    if create_result.get('success'):
                        result = user_profile.get_profile_display(user_id)
                        if not result.get('success'):
                            return jsonify(result), 404
                    else:
                        return jsonify(result), 404
                except Exception:
                    return jsonify(result), 404
            return jsonify(result), 404

        # Add activity feed
        try:
            from backend.services.agent_db_service import agent_db_service
            activities = agent_db_service.get_activity_feed(user_id, limit=20)
            result['activity_feed'] = {'success': True, 'activities': activities}
        except Exception:
            result['activity_feed'] = {'success': False, 'activities': []}

        # Add my agents
        try:
            from backend.services.agent_db_service import agent_db_service
            agents = agent_db_service.get_user_agents(user_id)
            result['my_agents'] = {'success': True, 'agents': agents}
        except Exception:
            result['my_agents'] = {'success': False, 'agents': []}

        # Add achievements (profile service placeholder or user_engagement)
        try:
            result['achievements'] = user_profile.get_profile_achievements(user_id)
        except Exception:
            result['achievements'] = {'success': True, 'achievements': []}

        # Add trophies (list + definitions)
        try:
            from backend.services.trophies_db_service import get_trophy_definitions, get_user_trophies
            definitions_list = get_trophy_definitions()
            trophies = get_user_trophies(user_id)
            definitions = {d['id']: d for d in definitions_list} if definitions_list else {}
            result['trophies_list'] = {'success': True, 'trophies': trophies, 'definitions': definitions}
        except Exception:
            result['trophies_list'] = {'success': False, 'trophies': [], 'definitions': {}}

        # Add geo_ref (optional, avoid heavy imports)
        try:
            from backend.routes.hunters_game import _get_geo_ref
            result['geo_ref'] = _get_geo_ref(user_id)
        except Exception:
            result['geo_ref'] = None

        # Unified points (file + DB merged) + leaderboard strip (same store)
        try:
            from backend.services.unified_points_database import unified_points_db
            result['unified_points'] = unified_points_db.get_all_points(user_id)
            all_u = unified_points_db.get_all_users_points()
            ranked = sorted(
                ((uid, int(d.get('xp_total', 0) or 0)) for uid, d in all_u.items()),
                key=lambda x: -x[1],
            )[:10]
            result['leaderboard_snippet'] = [{'user_id': u, 'xp_total': x} for u, x in ranked]
        except Exception:
            result['unified_points'] = {'success': False, 'points': {}}
            result['leaderboard_snippet'] = []

        # Lab logbook: research progress, project cooldowns, and latest lab events for Profile.
        try:
            from backend.routes.lab_routes import lab_profile_logbook
            result['lab_logbook'] = lab_profile_logbook(user_id)
        except Exception:
            result['lab_logbook'] = {'success': False, 'summary': {}, 'events': [], 'projects': []}

        # Password protection status for profile setup checklist and account tab.
        try:
            from backend.services.password_protection_service import get_password_status
            result['password_status'] = {'success': True, **get_password_status(user_id)}
        except Exception:
            result['password_status'] = {'success': False, 'has_password': False, 'can_unlock': False}

        # Shop: purchases + inventory for profile tab (same APIs as /api/shop/*)
        try:
            from backend.services.shop_db_service import get_purchases, get_inventory
            result['shop_summary'] = {
                'purchases': get_purchases(user_id, limit=20),
                'inventory': get_inventory(user_id),
            }
        except Exception:
            result['shop_summary'] = {'purchases': [], 'inventory': []}

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_profile_bp.route('/api/user/profile/<user_id>/stats', methods=['GET'])
def get_profile_stats(user_id):
    """Get profile statistics"""
    try:
        result = user_profile.calculate_profile_stats(user_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/profile/<user_id>/activity', methods=['GET'])
def get_profile_activity(user_id):
    """Get profile activity"""
    try:
        limit = request.args.get('limit', 10, type=int)
        result = user_profile.get_profile_activity(user_id, limit)
        return jsonify(result), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/profile/<user_id>/achievements', methods=['GET'])
def get_profile_achievements(user_id):
    """Get profile achievements"""
    try:
        result = user_profile.get_profile_achievements(user_id)
        return jsonify(result), 200
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/enrich-profile', methods=['POST'])
def enrich_profile():
    """Enrich user profile with additional information"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        # Prepare additional data
        additional_data = {
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'language': request.headers.get('Accept-Language', ''),
            **data.get('additional_data', {})
        }
        
        result = user_onboarding.enrich_user_profile(user_id, additional_data)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========== USER LOCATION (GPS) ==========

@user_profile_bp.route('/api/user/location', methods=['GET'])
def get_user_location():
    """Get current user's GPS location (new system: file-backed, optional DB sync)."""
    try:
        user_id = _resolve_user_id_for_request()
        location = user_location_service.get_location(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'location': location,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_profile_bp.route('/api/user/location', methods=['POST'])
def update_user_location():
    """Update current user's GPS location. Accepts latitude, longitude, geo_ref, accuracy, source (browser|manual|api)."""
    try:
        user_id = _resolve_user_id_for_request()
        data = request.get_json() or {}
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        if latitude is not None:
            latitude = float(latitude)
        if longitude is not None:
            longitude = float(longitude)
        geo_ref = data.get('geo_ref', '')
        accuracy = data.get('accuracy')
        if accuracy is not None:
            accuracy = float(accuracy)
        source = data.get('source', 'manual')
        location = user_location_service.update_location(
            user_id,
            latitude=latitude,
            longitude=longitude,
            geo_ref=geo_ref or None,
            accuracy=accuracy,
            source=source,
        )
        return jsonify({
            'success': True,
            'user_id': user_id,
            'location': location,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ========== PROFILE UPDATE ==========

@user_profile_bp.route('/api/user/profile/update', methods=['POST'])
def update_profile():
    """Update user profile (preferences, bio, avatar, etc.)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        update_data = data.get('update_data') or {}

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400
        if not isinstance(update_data, dict) or not update_data:
            return jsonify({'success': False, 'error': 'update_data must be a non-empty object'}), 400

        result = user_onboarding.update_user_profile(user_id, update_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@user_profile_bp.route('/api/user/provision/full-access', methods=['POST'])
def provision_full_access():
    """Apply full agent + battle + AI package to an existing user."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id is required'}), 400

        profile = user_onboarding.get_user_profile(user_id)
        if not profile:
            # Create user first if missing, then provision.
            create_result = user_onboarding.create_new_user({
                'user_agent': request.headers.get('User-Agent', ''),
                'ip_address': request.remote_addr,
                'language': request.headers.get('Accept-Language', ''),
                'referral_source': data.get('referral_source', 'manual_provision'),
                'preferences': data.get('preferences', {}),
            }, user_id)
            if not create_result.get('success'):
                return jsonify(create_result), 400
            profile = create_result.get('profile', {})

        result = user_onboarding.provision_user_features(user_id, profile)
        return jsonify(result), 200 if result.get('success') else 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== ONBOARDING MANAGEMENT ==========

@user_profile_bp.route('/api/user/onboarding/start', methods=['POST'])
def start_onboarding():
    """Start onboarding process for a user"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        progress = user_onboarding.start_onboarding(user_id)
        
        return jsonify({
            'success': True,
            'progress': progress
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/onboarding/complete-step', methods=['POST'])
def complete_onboarding_step():
    """Complete an onboarding step"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        step_id = data.get('step_id')
        
        if not all([user_id, step_id]):
            return jsonify({
                'success': False,
                'error': 'user_id and step_id are required'
            }), 400
        
        progress = user_onboarding.complete_step(user_id, step_id)
        
        return jsonify({
            'success': True,
            'progress': progress
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/onboarding/skip', methods=['POST'])
def skip_onboarding_step():
    """Skip an onboarding step"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        step_id = data.get('step_id')
        
        if not all([user_id, step_id]):
            return jsonify({
                'success': False,
                'error': 'user_id and step_id are required'
            }), 400
        
        result = user_onboarding.skip_step(user_id, step_id)
        
        if result.get('success') is False:
            return jsonify(result), 400
        
        return jsonify({
            'success': True,
            'progress': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/onboarding/status', methods=['GET'])
@user_profile_bp.route('/api/user/onboarding/status/<user_id>', methods=['GET'])
def get_onboarding_status(user_id=None):
    """Get onboarding status for a user"""
    try:
        # Support both query parameter and path parameter
        if not user_id:
            user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        status = user_onboarding.get_onboarding_status(user_id)
        
        if status:
            return jsonify({
                'success': True,
                'status': status
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Onboarding status not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/onboarding/progress', methods=['GET'])
def get_onboarding_progress():
    """Get detailed onboarding progress"""
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        progress = user_onboarding.get_progress(user_id)
        
        if progress:
            return jsonify({
                'success': True,
                'progress': progress
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Onboarding not started for this user'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== AGENT SKILLS MANAGEMENT ==========

@user_profile_bp.route('/api/user/agent-skills/<user_id>', methods=['GET'])
def get_user_agent_skills(user_id):
    """Get user's agent skills"""
    try:
        skills = user_agent_skills.get_user_skills(user_id)
        stats = user_agent_skills.get_skill_stats(user_id)
        
        return jsonify({
            'success': True,
            'skills': skills,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/assign-skill', methods=['POST'])
def assign_skill():
    """Assign skill to user"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        agent_id = data.get('agent_id')
        skill_name = data.get('skill_name')
        level = data.get('level', 1)
        
        if not all([user_id, agent_id, skill_name]):
            return jsonify({
                'success': False,
                'error': 'user_id, agent_id, and skill_name are required'
            }), 400
        
        success = user_agent_skills.add_skill(user_id, agent_id, skill_name, level)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Skill assigned successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to assign skill'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/level-up-skill', methods=['POST'])
def level_up_skill():
    """Level up a skill"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        skill_name = data.get('skill_name')
        experience = data.get('experience', 100)
        
        if not all([user_id, skill_name]):
            return jsonify({
                'success': False,
                'error': 'user_id and skill_name are required'
            }), 400
        
        result = user_agent_skills.level_up_skill(user_id, skill_name, experience)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/skill-stats/<user_id>', methods=['GET'])
def get_skill_stats(user_id):
    """Get skill statistics for user"""
    try:
        stats = user_agent_skills.get_skill_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/recommend-skills', methods=['POST'])
def recommend_skills():
    """Get skill recommendations based on behavior"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        user_behavior = data.get('user_behavior', {})
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        recommendations = user_agent_skills.recommend_skills(user_id, user_behavior)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== SCRAPED INFO ==========

@user_profile_bp.route('/api/user/scraped-info/<user_id>', methods=['GET'])
def get_scraped_info(user_id):
    """Get scraped information for user"""
    try:
        info_type = request.args.get('info_type')  # Optional filter
        
        scraped_info = user_info_scraper.get_scraped_info(user_id, info_type)
        
        return jsonify({
            'success': True,
            'scraped_info': scraped_info
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_profile_bp.route('/api/user/scrape-info', methods=['POST'])
def scrape_info():
    """Trigger additional info scraping"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        scrape_type = data.get('scrape_type', 'all')  # all, browser, device, location, behavior
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        # Prepare request data
        request_data = {
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'language': request.headers.get('Accept-Language', ''),
            **data.get('additional_data', {})
        }
        
        # Scrape based on type
        if scrape_type == 'all':
            scraped_info = user_info_scraper.scrape_all_info(request_data)
            # Save all types
            for info_type, info_data in scraped_info.items():
                if info_type not in ['scraped_at', 'scraping_version', 'confidence_score']:
                    user_info_scraper.save_scraped_info(user_id, info_type, info_data)
        elif scrape_type == 'browser':
            info = user_info_scraper.scrape_browser_info(request_data)
            user_info_scraper.save_scraped_info(user_id, 'browser', info)
            scraped_info = {'browser': info}
        elif scrape_type == 'device':
            info = user_info_scraper.scrape_device_info(request_data)
            user_info_scraper.save_scraped_info(user_id, 'device', info)
            scraped_info = {'device': info}
        elif scrape_type == 'location':
            info = user_info_scraper.scrape_location_info(request_data)
            user_info_scraper.save_scraped_info(user_id, 'location', info)
            scraped_info = {'location': info}
        elif scrape_type == 'behavior':
            info = user_info_scraper.scrape_behavioral_info(request_data)
            user_info_scraper.save_scraped_info(user_id, 'behavior', info)
            scraped_info = {'behavior': info}
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown scrape_type: {scrape_type}'
            }), 400
        
        return jsonify({
            'success': True,
            'scraped_info': scraped_info
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# AI Profile Analysis — Gemini 1M context for deep personalisation
# ---------------------------------------------------------------------------

@user_profile_bp.route('/api/user/ai-analysis', methods=['GET', 'POST'])
def ai_profile_analysis():
    """
    Deep AI analysis of a user's platform activity using Gemini's 1M context window.

    GET  ?user_id=X
    POST {"user_id": "X", "focus": "recommendations|personality|next_steps|full"}

    Returns personality_type, top_interests, ai_bio, power_moves, content_recommendations.
    """
    try:
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
        else:
            data = request.args.to_dict()

        user_id = (data.get('user_id') or '').strip()
        focus   = (data.get('focus') or 'full').strip()

        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 200

        context_parts = []

        try:
            profile = user_profile.get_profile(user_id)
            if profile:
                context_parts.append("USER PROFILE: " + str(profile)[:3000])
        except Exception:
            pass

        try:
            scraped = user_info_scraper.get_scraped_info(user_id, 'all')
            if scraped:
                context_parts.append("SCRAPED SIGNALS: " + str(scraped)[:3000])
        except Exception:
            pass

        try:
            skills = user_agent_skills.get_skills(user_id)
            if skills:
                context_parts.append("AGENT SKILLS: " + str(skills)[:2000])
        except Exception:
            pass

        try:
            from backend.services.unified_points_database import unified_points_db
            pts = unified_points_db.get_user_points(user_id)
            if pts:
                context_parts.append("POINTS & ACTIVITY: " + str(pts)[:2000])
        except Exception:
            pass

        if not context_parts:
            context_parts.append("New user — no activity data yet.")

        user_context = "\n\n".join(context_parts)

        focus_instructions = {
            "recommendations": "Focus on what content, features, and video topics would excite this user most.",
            "personality":     "Focus on personality archetype, learning style, and engagement patterns.",
            "next_steps":      "Focus on the top 3 power moves this user should take right now.",
            "full":            "Provide a comprehensive analysis covering all dimensions.",
        }.get(focus, "Provide a comprehensive analysis.")

        system_prompt = (
            "You are an elite AI analyst for MasterNoder.dk — an AI video generation platform with game mechanics. "
            "Analyse the user data and return a JSON object with these exact keys:\n"
            "- personality_type: 2-3 word archetype (e.g. 'Creative Explorer')\n"
            "- engagement_score: integer 0-100\n"
            "- top_interests: list of 3-5 topic strings\n"
            "- ai_bio: 2 sentence personalised bio in second person\n"
            "- power_moves: list of exactly 3 objects each with {title, description, xp_reward}\n"
            "- content_recommendations: list of 3 video idea title strings\n"
            "- strengths: list of 2-3 strength strings\n"
            "- growth_opportunity: one sentence string\n"
            "Respond ONLY with valid JSON, no markdown."
        )

        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": focus_instructions + "\n\nUSER DATA:\n" + user_context},
            ],
            task_type="context",
            max_tokens=1200,
            temperature=0.7,
        )

        if not resp.success:
            return jsonify({'success': False, 'error': resp.error or 'LLM unavailable'}), 200

        import json as _json
        raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        try:
            analysis = _json.loads(raw)
        except Exception:
            analysis = {"raw": resp.content, "personality_type": "Explorer", "power_moves": []}

        return jsonify({
            'success':  True,
            'user_id':  user_id,
            'analysis': analysis,
            'provider': resp.provider,
            'model':    resp.model,
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
