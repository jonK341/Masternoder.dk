"""
Generator routes for video generation functionality
"""
from flask import Blueprint, render_template, request, jsonify, make_response
from src.utils.rate_limiter import rate_limit
import time
import uuid
import logging

# Get logger for this module
logger = logging.getLogger('vidgenerator.generator')

generator_bp = Blueprint('generator', __name__)
_ai_clip_jobs = {}

# AI CLIPS ROUTES - Must be registered FIRST to avoid route conflicts
# Middleware strips /vidgenerator, so /api/generator/ai-clips matches /vidgenerator/api/generator/ai-clips
@generator_bp.route('/api/generator/ai-clips', methods=['POST', 'OPTIONS'], strict_slashes=False)
def ai_clip_create():
    """Create an AI clip generation job (stubbed demo)."""
    import sys
    print(f"[AI-CLIPS] {request.method} /api/generator/ai-clips called", file=sys.stderr, flush=True)
    print(f"[AI-CLIPS] Request path: {request.path}", file=sys.stderr, flush=True)
    print(f"[AI-CLIPS] Blueprint name: {generator_bp.name}", file=sys.stderr, flush=True)
    
    # Handle OPTIONS for CORS
    if request.method == 'OPTIONS':
        response = jsonify({'success': True})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
    try:
        data = request.get_json() or {}
        prompt = (data.get('prompt') or '').strip()
        meta = data.get('meta') or {}

        if not prompt:
            return jsonify({'success': False, 'error': 'prompt is required'}), 400

        job_id = str(uuid.uuid4())
        now = time.time()
        _ai_clip_jobs[job_id] = {
            'status': 'queued',
            'prompt': prompt,
            'meta': meta,
            'created_at': now,
            'updated_at': now,
            'clips': []
        }

        return jsonify({'success': True, 'job_id': job_id, 'status': 'queued'}), 202
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@generator_bp.route('/api/generator/ai-clips/<job_id>', methods=['GET'], strict_slashes=False)
def ai_clip_status(job_id):
    """Poll AI clip generation job status (simulated completion)."""
    import sys
    print(f"[AI-CLIPS] GET /api/generator/ai-clips/{job_id} called", file=sys.stderr, flush=True)
    job = _ai_clip_jobs.get(job_id)
    if not job:
        return jsonify({'success': False, 'error': 'job not found'}), 404

    # Simulate completion after ~2 seconds
    if job['status'] != 'completed' and time.time() - job['created_at'] > 2:
        job['status'] = 'completed'
        job['updated_at'] = time.time()
        job['clips'] = [
            {'title': 'Clip 1', 'url': '/static/generated/clip1.mp4'},
            {'title': 'Clip 2', 'url': '/static/generated/clip2.mp4'},
        ]

    return jsonify({'success': True, 'job_id': job_id, **job})


# Test route to verify blueprint registration
@generator_bp.route('/api/generator/test', methods=['GET'], strict_slashes=False)
def test_route():
    """Test route to verify blueprint is registered"""
    return jsonify({'success': True, 'message': 'Generator blueprint is working!'}), 200

@generator_bp.route('/api/generator/test-process', methods=['POST'], strict_slashes=False)
def test_generator_process():
    """Test URL endpoint for generator process - creates a test video"""
    try:
        from src.utils.input_validator import InputValidator
        
        data = request.get_json() or {}
        title = data.get('title', 'Test Video - Generator Process')
        description = data.get('description', 'A test video to verify the complete generator process works correctly')
        theme = data.get('theme', 'nature')
        
        # Create request data structure
        test_data = {
            'title': title,
            'description': description,
            'theme': theme
        }
        
        # Temporarily replace request.json for create_video function
        original_json = request.get_json
        request.get_json = lambda: test_data
        
        try:
            # Call create_video function
            result = create_video()
            
            # Restore original
            request.get_json = original_json
            
            # If result is a tuple (response, status_code), return it
            if isinstance(result, tuple):
                return result
            
            return result
            
        except Exception as e:
            request.get_json = original_json
            raise
        
    except Exception as e:
        import sys
        import traceback
        print(f"[Generator] Test process error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Test process failed'
        }), 500

# Debug route to see all registered routes
@generator_bp.route('/api/generator/debug-routes', methods=['GET'], strict_slashes=False)
def debug_routes():
    """Debug: Show all registered routes"""
    from flask import current_app
    routes = []
    for rule in current_app.url_map.iter_rules():
        if 'generator' in rule.rule.lower() or 'ai-clips' in rule.rule.lower():
            routes.append({
                'rule': rule.rule,
                'methods': list(rule.methods),
                'endpoint': rule.endpoint
            })
    return jsonify({'success': True, 'routes': routes}), 200


@generator_bp.route('/generator')
@generator_bp.route('/generator/')
def generator_index():
    """Video generator main page - reorganized and improved"""
    from flask import Response
    import os
    
    try:
        # Priority 1: Try serving from vidgenerator/generator directory (production files)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        vidgen_path = os.path.join(base_path, 'vidgenerator', 'generator')
        index_file = os.path.join(vidgen_path, 'index.html')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            response = Response(content, mimetype='text/html; charset=utf-8')
            # Cache headers will be added by app.after_request middleware
            return response
        
        # Priority 2: Try template rendering
        try:
            response = make_response(render_template('generator/index.html'))
            response.headers['Content-Type'] = 'text/html; charset=utf-8'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception:
            pass
        
        # Fallback: Basic HTML
        return """
        <!DOCTYPE html>
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Video Generator - MasterNoder</title>
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       color: #333; min-height: 100vh; padding: 20px; margin: 0; }
                .container { max-width: 1200px; margin: 0 auto; background: white; 
                            border-radius: 15px; padding: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
                h1 { color: #667eea; margin-bottom: 20px; }
                p { color: #666; margin-bottom: 15px; }
                a { color: #667eea; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>AI Video Generator</h1>
                <p>Generator interface loading...</p>
                <p><a href="/vidgenerator">← Back to main page</a></p>
            </div>
        </body>
        </html>
        """, 200
        
    except Exception as e:
        return f"Error loading generator page: {str(e)}", 500


def create_video():
    """API endpoint for creating videos - connects to documentary generation system (can be called directly or via blueprint)"""
    print(f"[Generator] create_video called - method: {request.method}, path: {request.path}", flush=True)
    try:
        from src.utils.input_validator import InputValidator
        
        print(f"[Generator] Getting JSON data...", flush=True)
        # Use safe JSON parsing with sanitization
        data = InputValidator.get_json_safe(default={})
        print(f"[Generator] Data received (sanitized)", flush=True)
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['title'])
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400
        
        # Sanitize and validate inputs
        title = InputValidator.sanitize_string(data.get('title', ''), max_length=200).strip()
        description = InputValidator.sanitize_string(data.get('description', ''), max_length=5000).strip()
        theme = InputValidator.sanitize_string(data.get('theme', 'default'), max_length=50).strip() or 'default'
        
        # Validate title length
        if not InputValidator.validate_length(title, min_length=1, max_length=200):
            return jsonify({'success': False, 'error': 'Title must be between 1 and 200 characters'}), 400
        print(f"[Generator] Title: {title}, Description: {description}, Theme: {theme}", flush=True)
        
        if not title:
            return jsonify({
                'success': False,
                'error': 'Titel er påkrævet'
            }), 400
        
        # Use title as prompt if no description
        prompt = description if description else title
        
        # Import here to avoid circular imports
        print(f"[Generator] Starting imports...", flush=True)
        from flask import current_app
        print(f"[Generator] current_app imported", flush=True)
        from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
        print(f"[Generator] PipelineOrchestrator imported", flush=True)
        from src.db.models import db, Documentary
        print(f"[Generator] db, Documentary imported", flush=True)
        from datetime import datetime
        import uuid
        import threading
        import sys
        
        # Store app reference for background thread
        print(f"[Generator] Getting app reference...", flush=True)
        app = current_app._get_current_object()
        print(f"[Generator] App reference obtained: {type(app)}", flush=True)
        
        # Get category from request (optional) - sanitize
        category_name_raw = data.get('category', '')
        category_name = InputValidator.sanitize_string(category_name_raw, max_length=50).strip().lower() if category_name_raw else ''
        category_id = None
        if category_name:
            try:
                from src.services.content_categories import content_category_service
                category = content_category_service.get_category_by_name(category_name)
                if category:
                    category_id = category.get('id')
                    category_name = category.get('name')  # Use canonical name
                    print(f"[Generator] Category found: {category_name} (ID: {category_id})", flush=True)
            except Exception as cat_err:
                print(f"[Generator] Error getting category: {cat_err}", flush=True)
        
        # Get user_id from request or session (before background thread)
        # Try multiple methods to get user_id
        user_id = None
        try:
            # Method 1: From request JSON data
            user_id = data.get('user_id')
            # Method 2: From request args
            if not user_id:
                user_id = request.args.get('user_id')
            # Method 3: From session (if available)
            if not user_id:
                try:
                    from flask import session
                    if 'user_id' in session:
                        user_id = session.get('user_id')
                except:
                    pass
        except Exception as user_id_err:
            print(f"[Generator] Error getting user_id: {user_id_err}", flush=True)
        
        # Fallback to default_user if no user_id found
        if not user_id:
            user_id = 'default_user'
        
        print(f"[Generator] Using user_id: {user_id}", flush=True)
        
        # Get quality setting (low, medium, high) - default to medium
        quality = InputValidator.sanitize_string(data.get('quality', 'medium'), max_length=10).strip().lower()
        if quality not in ['low', 'medium', 'high']:
            quality = 'medium'
        
        # Create documentary record
        print(f"[Generator] Creating documentary record...", flush=True)
        doc_id = str(uuid.uuid4())
        attributes = {
            'theme': theme,
            'user_agent': request.headers.get('User-Agent', 'unknown'),
            'category': category_name if category_name else None,
            'user_id': user_id,  # Store user_id in attributes for reference
            'quality': quality  # Video quality setting
        }
        
        print(f"[Generator] Creating Documentary object...", flush=True)
        documentary = Documentary(
            id=doc_id,
            title=title,
            description=description or prompt,
            prompt=prompt,
            status='queued',
            progress=0,
            category_id=category_id,
            category_name=category_name if category_name else None
        )
        print(f"[Generator] Adding to session...", flush=True)
        db.session.add(documentary)
        print(f"[Generator] Committing to database...", flush=True)
        
        # Ensure documentaries table exists before committing
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'documentaries' not in inspector.get_table_names():
                print(f"[Generator] documentaries table missing, creating...", flush=True)
                db.create_all()
                print(f"[Generator] Tables created", flush=True)
        except Exception as table_check_err:
            print(f"[Generator] Error checking tables: {table_check_err}", flush=True)
        
        db.session.commit()
        print(f"[Generator] Documentary created: {doc_id}", flush=True)
        
        # Award XP for video creation (queued)
        try:
            from backend.services.hunters_leveling_system import hunters_leveling_system
            xp_result = hunters_leveling_system.award_xp(
                user_id=user_id,
                xp_amount=50,  # Base XP for queuing video
                source='video_generation',
                action_type='queue_video',
                metadata={
                    'documentary_id': doc_id,
                    'title': title,
                    'theme': theme,
                    'quality': quality,
                    'category': category_name
                }
            )
            if xp_result.get('level_up'):
                print(f"[Generator] [LEVEL UP] User {user_id} reached level {xp_result['current_level']}", flush=True)
        except Exception as xp_err:
            print(f"[Generator] Error awarding XP: {xp_err}", flush=True)
        
        # Generate in background (app reference already stored above)
        def generate_in_background():
            """Generate documentary in background"""
            try:
                def progress_callback(doc_id_cb, progress, message, message_key=None):
                    """Update progress in database with enhancements and progress fix"""
                    try:
                        # CRITICAL FIX: Ensure progress completion (130% production ready)
                        from backend.services.generator_progress_fix import generator_progress_fix
                        progress_fix = generator_progress_fix.ensure_progress_completion(
                            doc_id_cb, progress, message_key
                        )
                        fixed_progress = progress_fix.get('progress', progress)
                        
                        # Enhance progress with Fear Twister and future tech
                        enhanced_progress_value = fixed_progress
                        try:
                            from backend.services.generator_progress_enhancer import generator_progress_enhancer
                            context = {
                                'doc_id': doc_id_cb,
                                'stage': message_key,
                                'message': message
                            }
                            enhanced = generator_progress_enhancer.enhance_progress_callback(
                                doc_id_cb, fixed_progress, message, message_key, context
                            )
                            enhanced_progress_value = enhanced.get('enhanced_progress', fixed_progress)
                        except Exception as enhance_err:
                            print(f"[Generator] Progress enhancement error (non-critical): {enhance_err}", flush=True)
                        
                        with app.app_context():
                            doc = Documentary.query.get(doc_id_cb)
                            if doc:
                                # Use enhanced progress value (capped at 100, but ensure it reaches 100)
                                final_progress = min(100, max(int(enhanced_progress_value), int(fixed_progress)))
                                
                                # If progress is stuck below 10%, force it forward
                                if final_progress < 10 and progress < 10:
                                    final_progress = 10
                                    print(f"[Generator] PROGRESS FIX: Forced progression from {progress}% to {final_progress}%", flush=True)
                                
                                doc.progress = final_progress
                                if message_key:
                                    doc.description = f"PROGRESS_KEY:{message_key}"
                                db.session.commit()
                                print(f"[Generator] Progress updated: {doc_id_cb} - {doc.progress}% ({message_key or message}) [Fixed: {progress_fix.get('forced_progression', False)}] [Enhanced: {enhanced_progress_value != progress}]", flush=True)
                    except Exception as e:
                        print(f"[Generator] Error updating progress: {e}", flush=True)
                        import traceback
                        traceback.print_exc()
                
                try:
                    pipeline = PipelineOrchestrator(progress_callback=progress_callback)
                    print(f"[Generator] PipelineOrchestrator initialized successfully", flush=True)
                except Exception as init_err:
                    error_msg = f"Failed to initialize pipeline: {str(init_err)}"
                    print(f"[Generator] Error initializing PipelineOrchestrator: {error_msg}", flush=True)
                    import traceback
                    traceback.print_exc()
                    
                    # Update status with error
                    with app.app_context():
                        doc = Documentary.query.get(doc_id)
                        if doc:
                            doc.status = 'failed'
                            doc.progress = 0
                            doc.description = f"ERROR_INIT: {error_msg}"
                            db.session.commit()
                    
                    # Call progress callback with error
                    if progress_callback:
                        try:
                            progress_callback(doc_id, 0, error_msg, "error")
                        except:
                            pass
                    raise
                
                try:
                    print(f"[Generator] Starting generate_documentary for doc_id: {doc_id}", flush=True)
                    result = pipeline.generate_documentary(
                        doc_id=doc_id,
                        prompt=prompt,
                        title=title,
                        description=description,
                        attributes=attributes
                    )
                    print(f"[Generator] generate_documentary completed. Success: {result.get('success', False)}", flush=True)
                except Exception as gen_err:
                    error_msg = f"Failed to generate documentary: {str(gen_err)}"
                    print(f"[Generator] Error in generate_documentary: {error_msg}", flush=True)
                    import traceback
                    traceback.print_exc()
                    
                    # Update status with error
                    with app.app_context():
                        doc = Documentary.query.get(doc_id)
                        if doc:
                            doc.status = 'failed'
                            doc.progress = 0
                            doc.description = f"ERROR_GEN: {error_msg}"
                            db.session.commit()
                    
                    # Call progress callback with error
                    if progress_callback:
                        try:
                            progress_callback(doc_id, 0, error_msg, "error")
                        except:
                            pass
                    raise
                
                # Update documentary with result - ENSURE 100% COMPLETION
                with app.app_context():
                    doc = Documentary.query.get(doc_id)
                    if doc:
                        if result.get('success'):
                            # CRITICAL: Ensure completion reaches 100%
                            from backend.services.generator_progress_fix import generator_progress_fix
                            completion = generator_progress_fix.ensure_completion(doc_id, doc.progress)
                            
                            doc.status = 'completed'
                            doc.progress = completion.get('progress', 100)  # Guaranteed 100%
                            doc.video_path = result.get('video_path', '')
                            doc.duration = result.get('duration', 0)
                            doc.completed_at = datetime.utcnow()
                            
                            # Save quality information
                            if result.get('quality_score') is not None:
                                doc.quality_score = result.get('quality_score', 0.0)
                            if result.get('quality_level'):
                                doc.quality_level = result.get('quality_level', 'unknown')
                            if result.get('quality_meets_a_plus') is not None:
                                doc.quality_meets_a_plus = result.get('quality_meets_a_plus', False)
                            doc.quality_score = result.get('quality_score', 0.0)
                            doc.quality_level = result.get('quality_level', 'unknown')
                            doc.quality_meets_a_plus = result.get('quality_meets_a_plus', False)
                            
                            # Update category stats
                            if doc.category_id:
                                try:
                                    from src.services.content_categories import content_category_service
                                    content_category_service.increment_category_stat(
                                        doc.category_id, 'documentaries_completed', 1
                                    )
                                except Exception as stat_err:
                                    print(f"[Generator] Error updating category stats: {stat_err}", flush=True)
                            
                            # Enhance video with AI (Top 10 Features)
                            try:
                                from backend.services.video_generation_enhancer import video_generation_enhancer
                                enhancement_result = video_generation_enhancer.enhance_video_quality(
                                    doc_id=doc_id,
                                    video_path=result.get('video_path', ''),
                                    user_id=attributes.get('user_id', 'default_user')
                                )
                                
                                # Update quality score if enhanced
                                if enhancement_result.get('enhanced') and enhancement_result.get('quality_score'):
                                    doc.quality_score = enhancement_result.get('quality_score', doc.quality_score)
                                    doc.quality_level = 'enhanced' if enhancement_result.get('quality_score', 0) >= 0.9 else doc.quality_level
                                
                                # Calculate energy value
                                energy_value = video_generation_enhancer.calculate_energy_value(
                                    doc_id=doc_id,
                                    user_id=attributes.get('user_id', 'default_user'),
                                    quality_score=doc.quality_score or 0.85
                                )
                                
                                # Auto-save progress
                                video_generation_enhancer.auto_save_progress(
                                    doc_id=doc_id,
                                    progress=100,
                                    stage='completed'
                                )
                            except Exception as enh_err:
                                print(f"[Generator] Enhancement error (non-critical): {enh_err}", flush=True)
                            
                            # Agent Opinion and Service Worker Coordination
                            try:
                                from backend.services.agent_system import agent_system
                                user_id_for_agent = attributes.get('user_id', 'default_user')
                                
                                # Get user's primary agent
                                user_agents = agent_system.get_user_agents(user_id_for_agent)
                                if user_agents:
                                    primary_agent = user_agents[0]  # Use first agent
                                    agent_id = primary_agent.get('id')
                                    
                                    # Generate agent opinion on video
                                    video_data = {
                                        'video_id': doc_id,
                                        'title': title,
                                        'description': description,
                                        'quality_score': doc.quality_score or 0.85,
                                        'duration': doc.duration or 0,
                                        'video_path': doc.video_path or ''
                                    }
                                    
                                    agent_opinion = agent_system.generate_video_opinion(
                                        agent_id, doc_id, video_data
                                    )
                                    
                                    # Coordinate with service worker
                                    production_data = {
                                        'stage': 'completed',
                                        'video_id': doc_id,
                                        'video_path': doc.video_path,
                                        'quality_score': doc.quality_score
                                    }
                                    
                                    coordination = agent_system.coordinate_with_service_worker(
                                        agent_id, doc_id, production_data
                                    )
                                    
                                    print(f"[Generator] Agent opinion generated: {agent_opinion.get('opinion_score', 0)}", flush=True)
                            except Exception as agent_err:
                                print(f"[Generator] Agent integration error (non-critical): {agent_err}", flush=True)
                            
                            # Award XP for completed video
                            try:
                                from backend.services.hunters_leveling_system import hunters_leveling_system
                                user_id_for_xp = attributes.get('user_id', 'default_user')
                                
                                # Record theme usage
                                theme = attributes.get('theme', 'default')
                                if theme and theme != 'default':
                                    try:
                                        from backend.services.themes_system import themes_system
                                        themes_system.use_theme(user_id_for_xp, theme)
                                    except Exception as theme_err:
                                        print(f"[Generator] Error recording theme usage: {theme_err}", flush=True)
                                
                                # Base XP for completing video
                                base_xp = 100
                                
                                # Quality bonuses
                                quality_bonus = 0
                                if quality == 'high':
                                    quality_bonus = 50
                                elif quality == 'medium':
                                    quality_bonus = 25
                                
                                # Perfect quality bonus (if applicable)
                                perfect_bonus = 0
                                if result.get('quality_score', 0) >= 1.0:
                                    perfect_bonus = 100
                                
                                total_xp = base_xp + quality_bonus + perfect_bonus
                                
                                xp_result = hunters_leveling_system.award_xp(
                                    user_id=user_id_for_xp,
                                    xp_amount=total_xp,
                                    source='video_generation',
                                    action_type='complete_video',
                                    metadata={
                                        'documentary_id': doc_id,
                                        'title': title,
                                        'quality': quality,
                                        'quality_score': result.get('quality_score', 0),
                                        'duration': result.get('duration', 0),
                                        'category': category_name
                                    }
                                )
                                
                                if xp_result.get('level_up'):
                                    level_info = xp_result.get('level_up_info', {})
                                    print(f"[Generator] [LEVEL UP] User {user_id_for_xp} reached level {xp_result['current_level']}!", flush=True)
                                    print(f"[Generator] Title: {level_info.get('title_unlocked', 'No new title')}", flush=True)
                                    print(f"[Generator] Stat Points Gained: {level_info.get('stat_points_gained', 0)}", flush=True)
                                    print(f"[Generator] Themes Unlocked: {level_info.get('themes_unlocked', [])}", flush=True)
                                
                                # Connect to unified point system
                                try:
                                    from backend.services.point_connection_system import PointConnectionSystem
                                    point_connection = PointConnectionSystem()
                                    
                                    # Award generation points
                                    generation_points = 50  # Base points for video generation
                                    quality_points = int(result.get('quality_score', 0) * 20)  # Quality bonus
                                    total_generation_points = generation_points + quality_points
                                    
                                    # Award activity points
                                    activity_points = 25  # Activity points for video creation
                                    
                                    # Connect all points
                                    point_connection.ensure_point_counting(
                                        user_id_for_xp, 'generation_points', total_generation_points, 'video_generation'
                                    )
                                    point_connection.ensure_point_counting(
                                        user_id_for_xp, 'activity_points', activity_points, 'video_generation'
                                    )
                                    point_connection.ensure_point_counting(
                                        user_id_for_xp, 'xp', total_xp, 'video_generation'
                                    )
                                    
                                    print(f"[Generator] Points awarded: {total_xp} XP, {total_generation_points} generation points, {activity_points} activity points", flush=True)
                                except Exception as point_err:
                                    print(f"[Generator] Error connecting points: {point_err}", flush=True)
                                
                            except Exception as xp_err:
                                print(f"[Generator] Error awarding completion XP: {xp_err}", flush=True)
                            
                            # Check for achievements and milestones (update stats points)
                            try:
                                from backend.services.game_achievements import game_achievement_system
                                if game_achievement_system:
                                    # Get user_id from attributes (stored before background thread)
                                    user_id_for_achievements = attributes.get('user_id', 'default_user')
                                    from backend.routes.stats import _calculate_user_stats_for_achievements
                                    user_stats = _calculate_user_stats_for_achievements(user_id_for_achievements)
                                    achievement_result = game_achievement_system.update_user_stats(user_id_for_achievements, user_stats)
                                    
                                    # Award XP for achievements
                                    if achievement_result.get('new_achievements'):
                                        try:
                                            from backend.services.hunters_leveling_system import hunters_leveling_system
                                            for achievement in achievement_result['new_achievements']:
                                                hunters_leveling_system.award_xp(
                                                    user_id=user_id_for_achievements,
                                                    xp_amount=achievement.get('points', 0),
                                                    source='achievement',
                                                    action_type='earn_achievement',
                                                    metadata={'achievement_id': achievement.get('id')}
                                                )
                                        except Exception as ach_xp_err:
                                            print(f"[Generator] Error awarding achievement XP: {ach_xp_err}", flush=True)
                                    
                                    # Award XP for milestones
                                    if achievement_result.get('new_milestones'):
                                        try:
                                            from backend.services.hunters_leveling_system import hunters_leveling_system
                                            for milestone in achievement_result['new_milestones']:
                                                hunters_leveling_system.award_xp(
                                                    user_id=user_id_for_achievements,
                                                    xp_amount=milestone.get('points', 0),
                                                    source='milestone',
                                                    action_type='reach_milestone',
                                                    metadata={'milestone_id': milestone.get('id')}
                                                )
                                        except Exception as mil_xp_err:
                                            print(f"[Generator] Error awarding milestone XP: {mil_xp_err}", flush=True)
                                    
                                    if achievement_result.get('new_achievements') or achievement_result.get('new_milestones'):
                                        print(f"[Generator] New achievements/milestones earned for user {user_id_for_achievements}! Points: {achievement_result.get('total_earned_points', 0)}", flush=True)
                            except Exception as ach_err:
                                print(f"[Generator] Error checking achievements: {ach_err}", flush=True)
                        else:
                            doc.status = 'failed'
                            doc.progress = 0
                        db.session.commit()
            except Exception as e:
                error_msg = f"Background generation error: {str(e)}"
                print(f"[Generator] {error_msg}", flush=True)
                import traceback
                full_traceback = traceback.format_exc()
                print(f"[Generator] Full traceback:\n{full_traceback}", flush=True)
                
                try:
                    with app.app_context():
                        doc = Documentary.query.get(doc_id)
                        if doc:
                            doc.status = 'failed'
                            doc.progress = 0
                            # Store error message in description for debugging
                            doc.description = f"ERROR_BG: {error_msg[:500]}"  # Limit length
                            db.session.commit()
                            print(f"[Generator] Status updated to 'failed' for doc_id: {doc_id}", flush=True)
                except Exception as db_err:
                    print(f"[Generator] Failed to update status in database: {db_err}", flush=True)
                    import traceback
                    traceback.print_exc()
        
        # Start background generation
        thread = threading.Thread(target=generate_in_background, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'documentary_id': doc_id,
            'message': 'Videogenerering er startet. Dit video bliver genereret i baggrunden.',
            'status': 'generating'
        }), 202
                
    except Exception as e:
        print(f"[Generator] Request error: {e}", flush=True)
        import traceback
        error_trace = traceback.format_exc()
        print(f"[Generator] Full traceback:\n{error_trace}", flush=True)
        try:
            from src.utils.error_handler import ErrorHandler
            # Generate request ID for tracking
            request_id = str(uuid.uuid4())[:8]
            error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
            print(f"[Generator] Error response [{request_id}]: {error_response.get_json()}", flush=True)
            return error_response, status_code
        except ImportError as import_err:
            print(f"[Generator] Could not import ErrorHandler: {import_err}", flush=True)
            error_response = jsonify({
                'success': False,
                'error': f'Der opstod en uventet fejl: {str(e)}. Prøv igen eller kontakt support.',
                'error_code': 'UNKNOWN_ERROR',
                'request_id': str(uuid.uuid4())[:8]
            })
            return error_response, 500
        except Exception as handler_err:
            print(f"[Generator] Error in ErrorHandler: {handler_err}", flush=True)
            import traceback
            traceback.print_exc()
            error_response = jsonify({
                'success': False,
                'error': f'Der opstod en uventet fejl: {str(e)}. Prøv igen eller kontakt support.',
                'error_code': 'GENERATION_ERROR',
                'request_id': str(uuid.uuid4())[:8]
            })
            return error_response, 500

# Register /api/generator/create route BEFORE catch-all to ensure it matches first
@generator_bp.route('/api/generator/create', methods=['POST'], strict_slashes=False)
@rate_limit(endpoint='/api/generator/create')
def create_video_blueprint():
    """Blueprint route wrapper for create_video - MUST be before catch-all route"""
    import sys
    print(f"[BLUEPRINT-ROUTE] create_video_blueprint called - method: {request.method}, path: {request.path}", file=sys.stderr, flush=True)
    try:
        print(f"[BLUEPRINT-ROUTE] About to call create_video()", file=sys.stderr, flush=True)
        result = create_video()
        print(f"[BLUEPRINT-ROUTE] create_video() returned: {type(result)}", file=sys.stderr, flush=True)
        return result
    except Exception as e:
        print(f"[BLUEPRINT-ROUTE] Error calling create_video(): {e}", file=sys.stderr, flush=True)
        import traceback
        error_trace = traceback.format_exc()
        print(f"[BLUEPRINT-ROUTE] Full traceback:\n{error_trace}", file=sys.stderr, flush=True)
        try:
            from src.utils.error_handler import ErrorHandler
            import uuid
            request_id = str(uuid.uuid4())[:8]
            error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
            return error_response, status_code
        except:
            import uuid
            error_response = jsonify({
                'success': False,
                'error': f'Error: {str(e)}',
                'error_code': 'GENERATION_ERROR',
                'request_id': str(uuid.uuid4())[:8]
            })
            return error_response, 500

@generator_bp.route('/api/generator/status/<video_id>')
def video_status(video_id):
    """Get video generation status (legacy endpoint - redirects to new endpoint)"""
    from flask import redirect
    return redirect(f'/vidgenerator/api/documentary/progress/{video_id}', code=307)

@generator_bp.route('/api/documentary/progress/<doc_id>', methods=['GET'], strict_slashes=False)
def documentary_progress(doc_id):
    """Get documentary generation progress"""
    try:
        from src.db.models import db, Documentary
        from flask import current_app
        
        with current_app.app_context():
            doc = Documentary.query.get(doc_id)
            
            if not doc:
                return jsonify({
                    'success': False,
                    'error': 'Documentary not found',
                    'documentary_id': doc_id
                }), 404
            
            # Parse progress message if it contains a message key or error
            message = ''
            message_key = None
            error_message = None
            
            # Check description for progress keys or errors
            description_text = doc.description or ''
            
            if description_text.startswith('PROGRESS_KEY:'):
                message_key = description_text.replace('PROGRESS_KEY:', '').strip()
                # Map message keys to user-friendly messages
                try:
                    from src.utils.progress_stages import ProgressStageManager
                    stage_info = ProgressStageManager.get_stage_info(message_key)
                    message = stage_info.get('message', stage_info.get('description', 'Arbejder på videoen...'))
                except ImportError:
                    # Fallback to simple map
                    message_map = {
                        'script_generation': 'Genererer script...',
                        'script_complete': 'Script genereret',
                        'clip_generation': 'Genererer video klip...',
                        'video_compilation': 'Samler video klip...',
                        'compilation_complete': 'Video samling færdig',
                        'thumbnail_generation': 'Genererer thumbnail...',
                        'generation_complete': 'Generering færdig!',
                        'fallback': 'Opretter video...',
                        'error': 'Fejl opstod...'
                    }
                    message = message_map.get(message_key, 'Arbejder på videoen...')
            elif 'ERROR' in description_text.upper() or description_text.startswith('ERROR_INIT:') or description_text.startswith('ERROR_GEN:') or description_text.startswith('ERROR_BG:'):
                # Extract error message from description
                if ':' in description_text:
                    error_message = description_text.split(':', 1)[1].strip()
                else:
                    error_message = description_text
                message = error_message[:200] if error_message else 'Videogenerering mislykkedes'
                message_key = 'error'
            elif description_text:
                # Use description as message if it's not a progress key
                message = description_text[:200]
            else:
                # Default message based on status
                if doc.status == 'failed':
                    message = 'Videogenerering mislykkedes'
                elif doc.status == 'queued':
                    message = 'I kø...'
                elif doc.status == 'processing':
                    message = f'Genererer... {doc.progress}%'
                else:
                    message = f'Progress: {doc.progress}%'
            
            response_data = {
                'success': True,
                'documentary_id': doc_id,
                'status': doc.status,
                'progress': doc.progress,
                'message': message,
                'message_key': message_key
            }
            
            # Include error message if status is failed
            if doc.status == 'failed':
                if error_message:
                    response_data['error'] = error_message
                elif description_text and ('ERROR' in description_text.upper()):
                    # Try to extract error from description
                    if ':' in description_text:
                        error_text = description_text.split(':', 1)[1].strip()
                    else:
                        error_text = description_text
                    response_data['error'] = error_text[:500]  # Limit length
                else:
                    # Try to get error from message if available
                    if message and message != 'Videogenerering mislykkedes':
                        response_data['error'] = message
                    else:
                        response_data['error'] = 'Videogenerering mislykkedes. Tjek server logs for detaljer.'
            
            # Include quality information if available (not just when completed)
            if doc.quality_score is not None:
                response_data['quality_score'] = doc.quality_score
                response_data['quality_level'] = doc.quality_level or 'unknown'
                response_data['quality_meets_a_plus'] = doc.quality_meets_a_plus or False
                response_data['quality_valid'] = doc.quality_score >= 0.40  # Minimum threshold
            
            # If completed, include video path
            if doc.status == 'completed' and doc.video_path:
                # Convert absolute path to relative URL if needed
                video_path = doc.video_path
                if video_path.startswith('/var/www/html/vidgenerator'):
                    # Convert to relative path for serving
                    video_path = video_path.replace('/var/www/html/vidgenerator', '/vidgenerator')
                elif not video_path.startswith('/'):
                    video_path = f'/vidgenerator/{video_path}'
                
                response_data['video_path'] = video_path
                response_data['video_url'] = f'/vidgenerator/api/documentary/video/{doc_id}'
                response_data['thumbnail_path'] = doc.thumbnail_path or ''
                response_data['duration'] = doc.duration or 0
            
            return jsonify(response_data), 200
            
    except Exception as e:
        import sys
        print(f"[Generator] Error getting progress: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        try:
            from src.utils.error_handler import ErrorHandler
            error_response = ErrorHandler.sanitize_error_for_client(e)
        except:
            error_response = {
                'success': False,
                'error': 'Kunne ikke hente progress',
                'documentary_id': doc_id
            }
        return jsonify(error_response), 500

@generator_bp.route('/api/documentary/restart/<doc_id>', methods=['POST'], strict_slashes=False)
def restart_documentary(doc_id):
    """Restart a failed documentary generation - reset status and start again"""
    try:
        from src.db.models import db, Documentary
        from flask import current_app
        from datetime import datetime
        import threading
        import uuid
        
        with current_app.app_context():
            doc = Documentary.query.get(doc_id)
            
            if not doc:
                return jsonify({
                    'success': False,
                    'error': 'Documentary not found',
                    'documentary_id': doc_id
                }), 404
            
            # Only allow restart if status is failed or queued (stuck)
            if doc.status not in ['failed', 'queued']:
                return jsonify({
                    'success': False,
                    'error': f'Cannot restart generation with status: {doc.status}. Only failed or queued generations can be restarted.',
                    'current_status': doc.status
                }), 400
            
            # Store original values for restart
            original_title = doc.title
            original_description = doc.description or doc.prompt
            original_prompt = doc.prompt
            original_attributes = {}
            
            # Try to extract attributes from description if available
            if doc.description and not doc.description.startswith('ERROR'):
                original_description = doc.description
            else:
                # Use prompt as description if description is an error
                original_description = doc.prompt or doc.title
            
            # Get attributes from documentary record
            if hasattr(doc, 'attributes') and doc.attributes:
                import json
                try:
                    if isinstance(doc.attributes, str):
                        original_attributes = json.loads(doc.attributes)
                    else:
                        original_attributes = doc.attributes
                except:
                    original_attributes = {}
            
            # Reset documentary status
            doc.status = 'queued'
            doc.progress = 0
            doc.description = original_description  # Clear error messages
            doc.completed_at = None
            doc.video_path = None
            doc.thumbnail_path = None
            doc.duration = None
            doc.quality_score = None
            doc.quality_level = None
            doc.quality_meets_a_plus = None
            
            db.session.commit()
            print(f"[Generator] Documentary {doc_id} reset for restart", flush=True)
            
            # Get app reference for background thread
            app = current_app._get_current_object()
            
            # Get user_id from attributes or use default
            user_id = original_attributes.get('user_id', 'default_user')
            
            # Start generation in background
            def generate_in_background():
                """Generate documentary in background"""
                try:
                    def progress_callback(doc_id_cb, progress, message, message_key=None):
                        """Update progress in database"""
                        try:
                            from backend.services.generator_progress_fix import generator_progress_fix
                            progress_fix = generator_progress_fix.ensure_progress_completion(
                                doc_id_cb, progress, message_key
                            )
                            fixed_progress = progress_fix.get('progress', progress)
                            
                            with app.app_context():
                                doc = Documentary.query.get(doc_id_cb)
                                if doc:
                                    final_progress = min(100, max(int(fixed_progress), 0))
                                    if final_progress < 10 and progress < 10:
                                        final_progress = 10
                                    doc.progress = final_progress
                                    if message_key:
                                        doc.description = f"PROGRESS_KEY:{message_key}"
                                    db.session.commit()
                                    print(f"[Generator] Progress updated: {doc_id_cb} - {doc.progress}% ({message_key or message})", flush=True)
                        except Exception as e:
                            print(f"[Generator] Error updating progress: {e}", flush=True)
                    
                    from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
                    pipeline = PipelineOrchestrator(progress_callback=progress_callback)
                    
                    result = pipeline.generate_documentary(
                        doc_id=doc_id,
                        prompt=original_prompt,
                        title=original_title,
                        description=original_description,
                        attributes=original_attributes
                    )
                    
                    # Update documentary with result
                    with app.app_context():
                        doc = Documentary.query.get(doc_id)
                        if doc:
                            if result.get('success'):
                                from backend.services.generator_progress_fix import generator_progress_fix
                                completion = generator_progress_fix.ensure_completion(doc_id, doc.progress)
                                
                                doc.status = 'completed'
                                doc.progress = completion.get('progress', 100)
                                doc.video_path = result.get('video_path', '')
                                doc.duration = result.get('duration', 0)
                                doc.completed_at = datetime.utcnow()
                                doc.quality_score = result.get('quality_score', 0.0)
                                doc.quality_level = result.get('quality_level', 'unknown')
                                doc.quality_meets_a_plus = result.get('quality_meets_a_plus', False)
                            else:
                                doc.status = 'failed'
                                doc.progress = 0
                                doc.description = f"ERROR_GEN: {result.get('error', 'Unknown error')}"
                            db.session.commit()
                            
                except Exception as e:
                    error_msg = f"Background generation error: {str(e)}"
                    print(f"[Generator] {error_msg}", flush=True)
                    import traceback
                    traceback.print_exc()
                    
                    with app.app_context():
                        doc = Documentary.query.get(doc_id)
                        if doc:
                            doc.status = 'failed'
                            doc.progress = 0
                            doc.description = f"ERROR_BG: {error_msg[:500]}"
                            db.session.commit()
            
            # Start background generation
            thread = threading.Thread(target=generate_in_background, daemon=True)
            thread.start()
            
            return jsonify({
                'success': True,
                'documentary_id': doc_id,
                'message': 'Videogenerering er genstartet. Dit video bliver genereret i baggrunden.',
                'status': 'restarted'
            }), 202
            
    except Exception as e:
        print(f"[Generator] Error restarting documentary: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Kunne ikke genstarte videogenerering: {str(e)}',
            'documentary_id': doc_id
        }), 500

@generator_bp.route('/api/documentary/video/<doc_id>', methods=['GET'], strict_slashes=False)
def documentary_video(doc_id):
    """Serve documentary video file with optional download"""
    try:
        from src.db.models import db, Documentary
        from flask import current_app, send_file, abort, request
        import os
        
        # Check if download is requested
        download = request.args.get('download', '0') == '1'
        
        with current_app.app_context():
            doc = Documentary.query.get(doc_id)
            
            if not doc or doc.status != 'completed':
                abort(404)
            
            video_path = doc.video_path
            if not video_path or not os.path.exists(video_path):
                # Try to find video in output directory
                from pathlib import Path
                output_dir = Path('/var/www/html/vidgenerator/output/videos')
                video_file = output_dir / f"{doc_id}.mp4"
                if video_file.exists():
                    video_path = str(video_file)
                else:
                    abort(404)
            
            # Determine filename for download
            filename = None
            if download:
                # Use video title as filename, sanitize it
                title = doc.title or 'video'
                # Remove invalid filename characters
                import re
                filename = re.sub(r'[<>:"/\\|?*]', '_', title) + '.mp4'
            
            response = send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=download,
                download_name=filename if download else None
            )
            
            # Ensure proper headers for download
            if download:
                response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
            else:
                # For preview, ensure inline
                response.headers['Content-Disposition'] = 'inline'
            
            return response
            
    except Exception as e:
                import sys
                print(f"[Generator] Error serving video: {e}", file=sys.stderr, flush=True)
                
                # Log error
                from src.utils.logging_config import ErrorTracker
                ErrorTracker.log_error(
                    logger,
                    e,
                    context={'route': f'/api/documentary/video/{doc_id}', 'doc_id': doc_id}
                )
                
                abort(500)

# Catch-all debug route to see what paths Flask receives
# MUST be LAST to not interfere with specific routes above
@generator_bp.route('/api/generator/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def catch_all_debug(subpath):
    """Catch-all route to debug unmatched paths"""
    import sys
    print(f"[CATCH-ALL] Path: /api/generator/{subpath}", file=sys.stderr, flush=True)
    print(f"[CATCH-ALL] Method: {request.method}", file=sys.stderr, flush=True)
    print(f"[CATCH-ALL] Request path: {request.path}", file=sys.stderr, flush=True)
    
    if subpath == 'ai-clips':
        # This should have been caught by the specific route above
        return jsonify({
            'success': False,
            'error': 'Route /api/generator/ai-clips exists but was not matched',
            'method': request.method,
            'subpath': subpath,
            'request_path': request.path
        }), 404
    
    return jsonify({
        'success': False,
        'error': f'Route /api/generator/{subpath} not found',
        'method': request.method,
        'subpath': subpath,
        'request_path': request.path
    }), 404

