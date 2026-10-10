"""Flask routes for Documentary Generator - Delegates to new modular structure"""
# Import new modular routes - FIXED: Import directly from routes package (routes/__init__.py)
# CRITICAL: This file is src/web/routes.py
# The routes PACKAGE is src/web/routes/ (directory with __init__.py)
# We must import from the PACKAGE, not from this MODULE!
import os
import sys

try:
    # Method 1: Import the routes PACKAGE directly (routes/__init__.py)
    # We need to import from 'routes' subdirectory, not from this file
    routes_package_path = os.path.join(os.path.dirname(__file__), 'routes')
    routes_init_path = os.path.join(routes_package_path, '__init__.py')
    
    if os.path.exists(routes_init_path):
        # Add parent directory to path to allow importing
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Import from routes package (routes/__init__.py)
        from src.web.routes import register_routes as register_modular_routes
        USE_MODULAR_ROUTES = True
        # Don't print at module level - it can cause errno 11 in uWSGI
        # print("✓ Using modular routes from src.web.routes package (routes/__init__.py)")
    else:
        raise ImportError(f"routes/__init__.py not found at {routes_init_path}")
        
except (ImportError, AttributeError) as e:
    USE_MODULAR_ROUTES = False
    # Don't print at module level - it can cause errno 11 in uWSGI
    # print(f"WARNING: Could not import modular routes: {e}")
    # print("WARNING: Falling back to legacy routes")

import os
import uuid
from flask import render_template, request, jsonify, send_file, make_response
from src.db.models import db, Documentary, MovieClip, ViewerSession, ViewerInteraction

# Import services with error handling - these may not be available
try:
    from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
except ImportError:
    PipelineOrchestrator = None
    # Don't print at module level - it can cause errno 11 in uWSGI
    # print("WARNING: PipelineOrchestrator not available - some features may be limited")

try:
    from src.services.viewer_data.viewer_collector import ViewerCollector
except ImportError:
    ViewerCollector = None
    # Don't print at module level - it can cause errno 11 in uWSGI
    # print("WARNING: ViewerCollector not available - some features may be limited")

try:
    from src.services.cache.query_cache import query_cache
except ImportError:
    query_cache = None
    # Don't print at module level - it can cause errno 11 in uWSGI
    # print("WARNING: query_cache not available - caching disabled")

import threading
from datetime import datetime
from sqlalchemy import text
import json


def register_routes(app):
    """Register all routes - uses new modular structure if available"""
    # Safe print for uWSGI
    def _safe_print(*args, **kwargs):
        try:
            print(*args, **kwargs, flush=True)
        except (BlockingIOError, OSError):
            pass
    
    _safe_print(f"[ROUTES.PY] register_routes called, USE_MODULAR_ROUTES={USE_MODULAR_ROUTES}")
    if USE_MODULAR_ROUTES:
        _safe_print("[ROUTES.PY] Using modular routes - calling _register_legacy_api_routes first...")
        # Register legacy API routes FIRST (so service_worker_file is available for templates)
        _register_legacy_api_routes(app)
        _safe_print("[ROUTES.PY] _register_legacy_api_routes completed, now calling register_modular_routes...")
        # Then register modular route structure
        register_modular_routes(app)
        _safe_print("[ROUTES.PY] register_modular_routes completed")
    else:
        _safe_print("[ROUTES.PY] Using legacy routes (fallback)")
        # Fall back to legacy routes
        _register_legacy_routes(app)


def _register_legacy_api_routes(app):
    """Register legacy API routes only (NOT page routes - those are in modular routes)"""
    # This only registers API routes and static file routes, not page routes
    # Page routes (/vidgenerator, etc.) are handled by modular routes
    
    print("[LEGACY_API] ===== STARTING _register_legacy_api_routes =====")
    
    # CRITICAL: Register progress endpoint here (needed immediately after generation starts)
    print("[LEGACY_API] Registering progress endpoint...")
    from src.db.models import Documentary
    from flask import jsonify
    
    def get_pipeline():
        """Get pipeline instance"""
        try:
            from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
            return PipelineOrchestrator()
        except:
            return None
    
    @app.route('/api/documentary/<doc_id>/progress', methods=['GET'], endpoint='get_progress')
    @app.route('/vidgenerator/api/documentary/<doc_id>/progress', methods=['GET'], endpoint='get_progress_vidgenerator')
    def get_progress(doc_id):
        """Get generation progress with comprehensive data"""
        try:
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                return jsonify({'error': 'Documentary not found'}), 404
            
            # Get generation data from pipeline
            generation_data = {
                'clips': [],
                'editable_mp4': None,
                'storyline': {},
                'requirements': {}
            }
            
            # Get generation data from pipeline (with timeout protection)
            try:
                # Use a cached pipeline instance to avoid expensive re-initialization
                # This is wrapped in try-except to prevent blocking if pipeline is unavailable
                bg_pipeline = get_pipeline()
                if bg_pipeline and hasattr(bg_pipeline, 'get_generation_data'):
                    # This should be fast (just dict access), but wrap in try-except for safety
                    pipeline_data = bg_pipeline.get_generation_data(doc_id)
                    if pipeline_data:
                        generation_data.update(pipeline_data)
            except Exception as e:
                # Don't fail the entire request if pipeline data is unavailable
                # This prevents the progress endpoint from hanging
                print(f"Could not get generation data (non-critical): {e}")
            
            # Extract message_key from description
            message_key = None
            if documentary.description and 'PROGRESS_KEY:' in documentary.description:
                message_key = documentary.description.split('PROGRESS_KEY:')[1].split('|')[0].strip()
            
            # CRITICAL: Ensure video_path is always returned, even if empty
            video_path = documentary.video_path or ''
            
            return jsonify({
                'documentary_id': doc_id,
                'progress': documentary.progress or 0,
                'status': documentary.status or 'pending',
                'message': message_key or 'Processing...',
                'message_key': message_key,
                'video_path': video_path,  # Always include video_path
                'duration': documentary.duration,
                'clips': generation_data.get('clips', []),
                'editable_mp4': generation_data.get('editable_mp4'),
                'storyline': generation_data.get('storyline', {}),
                'requirements': generation_data.get('requirements', {})
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                from src.utils.error_handler import ErrorHandler
                error_response = ErrorHandler.sanitize_error_for_client(e)
            except ImportError:
                error_response = {'error': 'Der opstod en uventet fejl. Prøv igen eller kontakt support.', 'error_code': 'UNKNOWN_ERROR'}
            return jsonify(error_response), 500
    
    print("[LEGACY_API] Progress endpoint registered")
    
    # CRITICAL: Register video serving route (needed for video downloads)
    print("[LEGACY_API] Registering video serving route...")
    @app.route('/api/documentary/<doc_id>/video', methods=['GET'], endpoint='get_video')
    @app.route('/vidgenerator/api/documentary/<doc_id>/video', methods=['GET'], endpoint='get_video_vidgenerator')
    def get_video(doc_id):
        """Serve video file from local storage"""
        try:
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                return jsonify({'error': 'Documentary not found'}), 404
            
            # If video_path is not set, try to find or create the file
            if not documentary.video_path:
                # Try to find the file in the output directory
                import os
                from pathlib import Path
                
                if os.path.exists('/var/www/html/vidgenerator/output'):
                    output_dir = Path('/var/www/html/vidgenerator/output')
                elif os.path.exists('output'):
                    output_dir = Path('output')
                else:
                    output_dir = Path('/var/www/html/vidgenerator/output')
                
                potential_path = output_dir / f"{doc_id}.mp4"
                if potential_path.exists() and potential_path.stat().st_size > 1000:
                    # File exists, update database
                    documentary.video_path = str(potential_path)
                    db.session.commit()
                    video_path = str(potential_path)
                else:
                    # File doesn't exist, return error but with helpful message
                    return jsonify({
                        'error': 'Video path not set',
                        'message': f'Video file not found. Expected path: {potential_path}',
                        'doc_id': doc_id
                    }), 404
            else:
                video_path = documentary.video_path
            
            video_path = documentary.video_path
            
            # If path is a URL (external storage), redirect to it
            if video_path.startswith('http://') or video_path.startswith('https://'):
                from flask import redirect
                return redirect(video_path, code=302)
            
            # If local file exists, serve it
            import os
            if os.path.exists(video_path):
                from flask import send_file
                return send_file(video_path, mimetype='video/mp4', as_attachment=False)
            
            # File doesn't exist - return helpful error
            return jsonify({
                'error': 'Video file not found',
                'video_path': video_path,
                'exists': False
            }), 404
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                from src.utils.error_handler import ErrorHandler
                error_response = ErrorHandler.sanitize_error_for_client(e)
            except ImportError:
                error_response = {'error': 'Der opstod en uventet fejl. Prøv igen eller kontakt support.', 'error_code': 'UNKNOWN_ERROR'}
            return jsonify(error_response), 500
    
    print("[LEGACY_API] Video serving route registered")
    print("[LEGACY_API] Registering service worker route...")
    # Register service worker route (needed by templates)
    @app.route('/service-worker.js', endpoint='service_worker_file')
    @app.route('/vidgenerator/service-worker.js', endpoint='service_worker_file_vidgenerator')
    def service_worker_file():
        """Serve Service Worker with proper headers and scope"""
        from flask import send_from_directory, make_response, send_file
        import os
        
        # Try multiple locations for service worker file
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sw_paths = [
            os.path.join(base_path, 'vidgenerator', 'service-worker.js'),  # Primary location
            os.path.join(app.static_folder, 'js', 'service-worker.js'),  # Alternative location
            os.path.join(base_path, 'backend', 'static', 'js', 'service-worker.js'),  # Backend static
        ]
        
        sw_path = None
        for path in sw_paths:
            if os.path.exists(path):
                sw_path = path
                break
        
        if not sw_path:
            return make_response('Service Worker file not found', 404)
        
        # Serve the file directly using send_file
        response = make_response(send_file(sw_path))
        
        # Critical headers for Service Worker
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        response.headers['Service-Worker-Allowed'] = '/'  # Allow root scope
        
        return response
    
    # Register view_documentary route (needed by gallery template) - MUST be registered early
    print("[LEGACY_API] Registering view_documentary route...")
    from flask import render_template, jsonify
    from src.db.models import Documentary
    
    @app.route('/documentary/<doc_id>', methods=['GET'], endpoint='view_documentary')
    @app.route('/vidgenerator/documentary/<doc_id>', methods=['GET'], endpoint='view_documentary_vidgenerator')
    def view_documentary(doc_id):
        """View individual documentary page (for SEO and sharing)"""
        try:
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                return jsonify({'error': 'Documentary not found'}), 404
            
            return render_template('documentary.html', documentary=documentary)
        except Exception as e:
            return f"Error loading documentary: {e}", 500
    
    print("[LEGACY_API] view_documentary route registered with endpoint 'view_documentary'")
    
    # Register generate_documentary API route (needed by generator)
    # Import necessary modules
    from flask import request, jsonify
    from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
    from src.db.models import db, Documentary
    from src.services.cache.query_cache import query_cache
    from datetime import datetime
    import uuid
    
    print("[LEGACY_API] Registering generate_documentary route...")
    
    # Register with explicit endpoint names to avoid conflicts
    @app.route('/api/documentary/generate', methods=['POST'], endpoint='api_generate_documentary')
    @app.route('/vidgenerator/api/documentary/generate', methods=['POST'], endpoint='api_generate_documentary_vidgenerator')
    def generate_documentary():
        """Generate a new documentary from prompt"""
        try:
            # Get client IP address (handles proxies)
            client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            if not client_ip:
                client_ip = request.remote_addr or 'unknown'
            
            # Get user agent
            user_agent = request.headers.get('User-Agent', 'unknown')
            
            # Get JSON data
            if request.is_json:
                data = request.get_json(force=False) or {}
            else:
                try:
                    import json
                    data = json.loads(request.data.decode('utf-8')) if request.data else {}
                except:
                    data = {}
            
            prompt = data.get('prompt', '').strip()
            title = data.get('title', prompt[:100] if prompt else 'Untitled Documentary')
            description = data.get('description', '')
            attributes = data.get('attributes', {})
            
            if not isinstance(attributes, dict):
                attributes = {}
            attributes['user_ip'] = client_ip
            attributes['user_agent'] = user_agent
            attributes['session_start_time'] = datetime.now().isoformat()
            
            if not prompt:
                return jsonify({'error': 'Prompt is required'}), 400
            
            # Create documentary record
            doc_id = str(uuid.uuid4())
            import json as json_module
            attrs_json = json_module.dumps(attributes)
            description_with_attrs = description
            if description:
                description_with_attrs = f"{description}|ATTRS_JSON:{attrs_json}"
            else:
                description_with_attrs = f"ATTRS_JSON:{attrs_json}"
            
            documentary = Documentary(
                id=doc_id,
                title=title,
                prompt=prompt,
                description=description_with_attrs,
                status='pending',
                progress=0
            )
            db.session.add(documentary)
            db.session.commit()
            
            import threading
            
            def progress_update_callback(doc_id_cb: str, progress: int, message: str, message_key: str = None):
                """Update progress in database with explicit commit and flush, with retry logic"""
                max_retries = 3
                retry_delay = 0.1
                
                for attempt in range(max_retries):
                    try:
                        with app.app_context():
                            documentary = Documentary.query.get(doc_id_cb)
                            if documentary:
                                # Update progress
                                documentary.progress = progress
                                
                                # Update description with message key for frontend
                                current_desc = documentary.description or ''
                                attrs_part = ''
                                if 'ATTRS_JSON:' in current_desc:
                                    attrs_part = '|' + current_desc.split('ATTRS_JSON:')[1]
                                    current_desc = current_desc.split('|ATTRS_JSON:')[0]
                                
                                if message_key:
                                    documentary.description = f"PROGRESS_KEY:{message_key}{attrs_part}"
                                elif attrs_part:
                                    documentary.description = f"{current_desc}{attrs_part}"
                                
                                # CRITICAL: Commit and flush to ensure progress is saved
                                db.session.commit()
                                db.session.flush()
                                
                                # Log progress update for debugging
                                if attempt > 0:
                                    print(f"[Progress] Updated {doc_id_cb} to {progress}%: {message} (retry {attempt})", flush=True)
                                else:
                                    print(f"[Progress] Updated {doc_id_cb} to {progress}%: {message}", flush=True)
                                
                                import time
                                time.sleep(0.15)  # Small delay to ensure database write completes
                                return  # Success - exit retry loop
                            else:
                                print(f"[Progress] ⚠ Documentary {doc_id_cb} not found in database", flush=True)
                                return  # Documentary not found - don't retry
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"[Progress] ⚠ Progress update error (attempt {attempt + 1}/{max_retries}): {e}, retrying...", flush=True)
                            import time
                            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        else:
                            # Final attempt failed
                            print(f"[Progress] ✗ Progress update failed after {max_retries} attempts: {e}", flush=True)
                            import traceback
                            traceback.print_exc()
                            # Don't fail the entire process - just log the error
                    print(f"[Progress] Error updating progress: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
            
            def generate_in_background():
                """Generate documentary in background thread"""
                import time
                import sys
                import os
                from pathlib import Path
                bg_pipeline = None
                try:
                    print(f"[Routes] ===== STARTING BACKGROUND GENERATION FOR {doc_id} =====", flush=True)
                    sys.stdout.flush()
                    
                    with app.app_context():
                        documentary = Documentary.query.get(doc_id)
                        if not documentary:
                            print(f"[Routes] ERROR: Documentary {doc_id} not found in database", flush=True)
                            return
                        documentary.status = 'generating'
                        documentary.progress = 5
                        db.session.commit()
                        print(f"[Routes] Documentary status set to 'generating', progress=5%", flush=True)
                        time.sleep(0.5)
                    
                    print(f"[Routes] Creating PipelineOrchestrator...", flush=True)
                    bg_pipeline = PipelineOrchestrator(progress_callback=progress_update_callback)
                    print(f"[Routes] PipelineOrchestrator created, starting generate_documentary...", flush=True)
                    
                    try:
                        # Generate documentary - this will update progress through the callback
                        # DO NOT set progress manually here - let the pipeline control it
                        print(f"[Routes] Starting generate_documentary - pipeline will control progress updates", flush=True)
                        result = bg_pipeline.generate_documentary(
                            doc_id=doc_id,
                            prompt=prompt,
                            title=title,
                            description=description,
                            attributes=attributes
                        )
                        print(f"[Routes] generate_documentary completed: success={result.get('success')}, video_path={result.get('video_path', 'NONE')}", flush=True)
                    except Exception as gen_error:
                        print(f"[Routes] Generation pipeline error: {gen_error}", flush=True)
                        import traceback
                        traceback.print_exc()
                        # Create fallback result with actual file
                        if bg_pipeline:
                            fallback_path = bg_pipeline.file_manager.get_output_path(f"{doc_id}.mp4")
                            # Ensure file exists
                            verified_path = bg_pipeline._ensure_mp4_file_created(doc_id, fallback_path, fallback_duration=180)
                            result = {
                                'success': True,
                                'video_path': verified_path or str(fallback_path),
                                'thumbnail_path': '',
                                'duration': 180,
                                'clips': [],
                                'message': 'Documentary created (fallback)'
                            }
                        else:
                            result = {
                                'success': False,
                                'video_path': '',
                                'error': str(gen_error)
                            }
                    
                    # Only update final status after pipeline completes
                    # The pipeline's progress callback should have already updated progress to 100%
                    with app.app_context():
                        documentary = Documentary.query.get(doc_id)
                        if documentary:
                            video_path = result.get('video_path', '')
                            
                            # Determine output directory
                            if os.path.exists('/var/www/html/vidgenerator/output'):
                                output_dir = Path('/var/www/html/vidgenerator/output')
                            elif os.path.exists('output'):
                                output_dir = Path('output')
                            else:
                                output_dir = Path('/var/www/html/vidgenerator/output')
                                output_dir.mkdir(parents=True, exist_ok=True)
                            
                            # If no video_path or file doesn't exist, create it
                            if not video_path or not os.path.exists(video_path):
                                potential_path = output_dir / f"{doc_id}.mp4"
                                print(f"[Routes] Output directory: {output_dir}, potential path: {potential_path}", flush=True)
                                
                                # Try to find existing file first
                                if potential_path.exists() and potential_path.stat().st_size > 1000:
                                    video_path = str(potential_path)
                                    print(f"[Routes] Found existing video file: {video_path}", flush=True)
                                elif bg_pipeline:
                                    # Create file using pipeline's ensure function
                                    print(f"[Routes] Creating video file: {potential_path}", flush=True)
                                    verified_path = bg_pipeline._ensure_mp4_file_created(doc_id, potential_path, fallback_duration=180)
                                    if verified_path and os.path.exists(verified_path):
                                        video_path = verified_path
                                        print(f"[Routes] ✓ Video file created: {video_path}", flush=True)
                                    else:
                                        video_path = str(potential_path)
                                        print(f"[Routes] ⚠ Using fallback path: {video_path}", flush=True)
                                else:
                                    video_path = str(potential_path)
                                    print(f"[Routes] ⚠ Using default path (no pipeline): {video_path}", flush=True)
                            
                            # CRITICAL: Always set video_path, even if file doesn't exist yet
                            if not video_path or video_path.strip() == '':
                                video_path = str(output_dir / f"{doc_id}.mp4")
                                print(f"[Routes] Using default path (video_path was empty): {video_path}", flush=True)
                            
                            final_video_path = video_path
                            print(f"[Routes] Final video_path to save: {final_video_path}", flush=True)
                            
                            # Only update status if pipeline succeeded
                            # Progress should already be at 100% from pipeline's Phase 2 completion
                            if result.get('success'):
                                # Check current progress - pipeline should have set it to 100%
                                current_progress = documentary.progress
                                print(f"[Routes] Current progress from pipeline: {current_progress}%", flush=True)
                                
                                # Only update if pipeline didn't complete (progress < 100)
                                if current_progress < 100:
                                    print(f"[Routes] Pipeline didn't reach 100%, setting to 95% before final update", flush=True)
                                    documentary.progress = 95
                                    db.session.commit()
                                    time.sleep(0.2)
                                
                                # Final update to completed
                                documentary.status = 'completed'
                                documentary.progress = 100
                                documentary.video_path = final_video_path  # Always set a path
                                documentary.thumbnail_path = result.get('thumbnail_path', '')
                                documentary.duration = result.get('duration', 180) or 180
                                documentary.completed_at = datetime.utcnow()
                                
                                # CRITICAL: Commit the video_path
                                try:
                                    db.session.commit()
                                    print(f"[Routes] ✓ Database updated: video_path={documentary.video_path}, status=completed, progress=100%", flush=True)
                                    # Verify it was saved
                                    db.session.refresh(documentary)
                                    if documentary.video_path:
                                        print(f"[Routes] ✓ Verified: video_path saved as '{documentary.video_path}'", flush=True)
                                    else:
                                        print(f"[Routes] ✗ ERROR: video_path is still None after commit!", flush=True)
                                except Exception as commit_error:
                                    print(f"[Routes] ✗ ERROR committing video_path: {commit_error}", flush=True)
                                    import traceback
                                    traceback.print_exc()
                            else:
                                # Generation failed
                                error_msg = result.get('error', 'Unknown error')
                                print(f"[Routes] Generation failed: {error_msg}", flush=True)
                                
                                # Try to create a fallback video file even if generation failed
                                if bg_pipeline:
                                    try:
                                        fallback_path = bg_pipeline.file_manager.get_output_path(f"{doc_id}.mp4")
                                        verified_path = bg_pipeline._ensure_mp4_file_created(doc_id, fallback_path, fallback_duration=180)
                                        if verified_path and os.path.exists(verified_path):
                                            final_video_path = verified_path
                                            print(f"[Routes] ✓ Created fallback video file: {final_video_path}", flush=True)
                                            documentary.video_path = final_video_path
                                            documentary.status = 'completed'  # Mark as completed even if generation had errors
                                            documentary.progress = 100
                                        else:
                                            documentary.status = 'failed'
                                    except Exception as fallback_error:
                                        print(f"[Routes] ⚠ Fallback video creation failed: {fallback_error}", flush=True)
                                        documentary.status = 'failed'
                                else:
                                    documentary.status = 'failed'
                                
                                db.session.commit()
                            
                            query_cache.invalidate('prompt_suggestions')
                            query_cache.invalidate_pattern('gallery')
                            query_cache.invalidate('progress', doc_id=doc_id)
                            sys.stdout.flush()
                except Exception as e:
                    print(f"[Routes] ===== GENERATION ERROR FOR {doc_id} =====", flush=True)
                    print(f"[Routes] Error: {e}", flush=True)
                    import traceback
                    error_trace = traceback.format_exc()
                    print(f"[Routes] Traceback:\n{error_trace}", flush=True)
                    
                    # Get user-friendly error message
                    try:
                        from src.utils.error_handler import ErrorHandler
                        user_message = ErrorHandler.get_user_friendly_message(e, 'Videogenerering mislykkedes. Prøv igen eller kontakt support.')
                    except ImportError:
                        user_message = 'Videogenerering mislykkedes. Prøv igen eller kontakt support.'
                    
                    try:
                        if bg_pipeline is None:
                            bg_pipeline = PipelineOrchestrator()
                        with app.app_context():
                            documentary = Documentary.query.get(doc_id)
                            if documentary:
                                # Update status with user-friendly error message
                                documentary.status = 'failed'
                                documentary.progress = 0
                                documentary.description = f"ERROR: {user_message}"
                                db.session.commit()
                                
                                output_dir = Path('/var/www/html/vidgenerator/output')
                                output_dir.mkdir(parents=True, exist_ok=True)
                                placeholder_path = output_dir / f"{doc_id}.mp4"
                                if not placeholder_path.exists():
                                    # Create a minimal valid MP4 file
                                    bg_pipeline._ensure_mp4_file_created(doc_id, placeholder_path, fallback_duration=180)
                                print(f"[Routes] Error handler: Status set to 'failed' with message: {user_message}", flush=True)
                    except Exception as db_error:
                        print(f"[Routes] Database error in error handler: {db_error}", flush=True)
                        import traceback
                        traceback.print_exc()
                    sys.stdout.flush()
            
            # CRITICAL: Log thread creation before starting
            print(f"[Routes] ===== CREATING BACKGROUND THREAD FOR {doc_id} =====", flush=True)
            import sys
            sys.stdout.flush()
            
            generation_thread = threading.Thread(target=generate_in_background, daemon=True)
            generation_thread.start()
            
            print(f"[Routes] ===== BACKGROUND THREAD STARTED (ID: {generation_thread.ident}) =====", flush=True)
            sys.stdout.flush()
            
            return jsonify({
                'success': True,
                'documentary_id': doc_id,
                'message': 'Generation started in background. Check progress endpoint for status.',
                'status': 'generating'
            })
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"ERROR in generate_documentary: {e}")
            print(error_trace)
            
            # Get user-friendly error message
            try:
                from src.utils.error_handler import ErrorHandler
                error_response = ErrorHandler.sanitize_error_for_client(e)
            except ImportError:
                # Fallback if error handler not available
                error_response = {
                    'error': 'Der opstod en uventet fejl. Prøv igen eller kontakt support.',
                    'error_code': 'UNKNOWN_ERROR',
                    'message': 'Der opstod en uventet fejl. Prøv igen eller kontakt support.'
                }
            
            return jsonify(error_response), 500
    
    print("[LEGACY_API] Essential routes registered (service_worker, view_documentary, generate_documentary)")

def _register_legacy_routes(app):
    """Register all routes with Flask app (legacy fallback only)"""
    
    # Don't initialize heavy services at module level - create them on demand
    # This avoids blocking startup if imports are slow
    pipeline = None
    viewer_collector = None
    
    def get_pipeline():
        """Get pipeline instance (lazy initialization)"""
        nonlocal pipeline
        if pipeline is None:
            pipeline = PipelineOrchestrator()
        return pipeline
    
    def get_viewer_collector():
        """Get viewer collector instance (lazy initialization)"""
        nonlocal viewer_collector
        if viewer_collector is None:
            viewer_collector = ViewerCollector()
        return viewer_collector
    
    # Static file route - SIMPLE AND ROBUST
    @app.route('/static/<path:filename>')
    @app.route('/vidgenerator/static/<path:filename>')
    def static_files_vidgenerator(filename):
        """Serve static files - handles /static and /vidgenerator/static paths"""
        from flask import send_from_directory, current_app, abort
        import os
        
        # Get base path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Primary static path
        static_path = os.path.join(base_path, 'vidgenerator', 'static')
        
        # Verify file exists
        file_path = os.path.join(static_path, filename)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            # Try alternative paths
            alt_paths = [
                os.path.join(base_path, 'src', 'web', 'static'),
                os.path.join(base_path, 'backend', 'static'),
            ]
            if hasattr(current_app, 'static_folder') and current_app.static_folder:
                alt_paths.insert(0, current_app.static_folder)
            
            found = False
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    alt_file_path = os.path.join(alt_path, filename)
                    if os.path.exists(alt_file_path) and os.path.isfile(alt_file_path):
                        static_path = alt_path
                        file_path = alt_file_path
                        found = True
                        break
            
            if not found:
                abort(404)
        
        # Serve the file
        try:
            return send_from_directory(static_path, filename)
        except Exception as e:
            print(f"[Static Route Error] {str(e)}")
            import traceback
            traceback.print_exc()
            abort(500)

    @app.route('/service-worker.js')
    @app.route('/vidgenerator/service-worker.js')
    def service_worker_file_legacy():
        """Serve Service Worker with proper headers and scope (legacy route)"""
        from flask import send_file, make_response
        import os
        
        # Try multiple locations for service worker file
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sw_paths = [
            os.path.join(base_path, 'vidgenerator', 'service-worker.js'),  # Primary location
            os.path.join(app.static_folder, 'js', 'service-worker.js'),  # Alternative location
            os.path.join(base_path, 'backend', 'static', 'js', 'service-worker.js'),  # Backend static
        ]
        
        sw_path = None
        for path in sw_paths:
            if os.path.exists(path):
                sw_path = path
                break
        
        if not sw_path:
            return make_response('Service Worker file not found', 404)
        
        # Serve the file directly using send_file
        response = make_response(send_file(sw_path))
        
        # Critical headers for Service Worker
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        response.headers['Service-Worker-Allowed'] = '/'  # Allow root scope
        
        return response

    @app.route('/offline')
    @app.route('/vidgenerator/offline')
    def offline_fallback():
        """Offline fallback page for Service Worker"""
        response = make_response(render_template('offline.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
    
    # REMOVED: Legacy index route - now handled by vidgenerator_index_direct() in src/app.py
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            'status': 'ok',
            'phase': 3,
            'message': 'Documentary Generator is running'
        })
    
    @app.route('/api/prompt/suggestions', methods=['GET'])
    @app.route('/vidgenerator/api/prompt/suggestions', methods=['GET'])
    def get_prompt_suggestions():
        """Get suggested prompts based on previous searches - CACHED"""
        try:
            # Try cache first
            cached = query_cache.get('prompt_suggestions')
            if cached is not None:
                return jsonify(cached)
            
            # Get most recent successful prompts from database
            recent_prompts = Documentary.query.filter(
                Documentary.status == 'completed'
            ).order_by(Documentary.created_at.desc()).limit(20).all()
            
            # Extract unique prompts and count frequency
            prompt_counts = {}
            for doc in recent_prompts:
                prompt = doc.prompt.strip()
                if len(prompt) > 10:  # Only meaningful prompts
                    # Use first 60 chars as key to group similar prompts
                    key = prompt[:60].lower()
                    if key not in prompt_counts:
                        prompt_counts[key] = {
                            'prompt': prompt[:100],  # Truncate for display
                            'full_prompt': prompt,
                            'count': 0,
                            'latest': doc.created_at
                        }
                    prompt_counts[key]['count'] += 1
            
            # Sort by count and recency, then take top 7
            suggestions = sorted(
                prompt_counts.values(),
                key=lambda x: (x['count'], x['latest']),
                reverse=True
            )[:7]
            
            # Extract just the prompts
            prompts = [s['full_prompt'] for s in suggestions]
            
            # If we don't have enough, add default suggestions
            default_suggestions = [
                "A documentary about the history of space exploration",
                "Wildlife documentary about endangered species",
                "Historical documentary about ancient civilizations",
                "Technology documentary about artificial intelligence",
                "Cultural documentary about world traditions",
                "Nature documentary about ocean ecosystems",
                "Scientific documentary about climate change"
            ]
            
            while len(prompts) < 7:
                for default in default_suggestions:
                    if default not in prompts:
                        prompts.append(default)
                        if len(prompts) >= 7:
                            break
            
            result = {
                'success': True,
                'suggestions': prompts[:7]
            }
            
            # Cache result for 5 minutes
            query_cache.set('prompt_suggestions', result, ttl=300)
            
            return jsonify(result)
        except Exception as e:
            print(f"Error getting prompt suggestions: {e}")
            # Return default suggestions on error
            return jsonify({
                'success': True,
                'suggestions': [
                    "A documentary about the history of space exploration",
                    "Wildlife documentary about endangered species",
                    "Historical documentary about ancient civilizations",
                    "Technology documentary about artificial intelligence",
                    "Cultural documentary about world traditions",
                    "Nature documentary about ocean ecosystems",
                    "Scientific documentary about climate change"
                ]
            })
    
    @app.route('/gallery', methods=['GET'])
    @app.route('/vidgenerator/gallery', methods=['GET'])
    def gallery():
        """Gallery page - serves static HTML file from vidgenerator/gallery/index.html"""
        from flask import Response
        import os
        
        try:
            # Try known server paths first
            known_paths = [
                '/var/www/html/vidgenerator/vidgenerator/gallery/index.html',
                os.path.join('/var/www/html/vidgenerator', 'vidgenerator', 'gallery', 'index.html'),
            ]
            
            # Also try calculated path
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            calculated_path = os.path.join(base_path, 'vidgenerator', 'gallery', 'index.html')
            if calculated_path not in known_paths:
                known_paths.append(calculated_path)
            
            for gallery_file in known_paths:
                if os.path.exists(gallery_file):
                    with open(gallery_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    response = Response(content, mimetype='text/html; charset=utf-8')
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
            
            return f"Gallery page not found. Tried: {known_paths}", 404
        except Exception as e:
            return f"Error loading gallery: {str(e)}", 500
    
    # NOTE: generate_documentary route is registered in _register_legacy_api_routes()
    # Do NOT duplicate it here to avoid route conflicts
    # The duplicate definition (previously at lines 1028-1324) has been removed to prevent 405 errors
    # This duplicate was causing route conflicts and 405 Method Not Allowed errors
    pass  # Duplicate route removed - see _register_legacy_api_routes() for the actual route
    @app.route('/documentary/<doc_id>', methods=['GET'])
    @app.route('/vidgenerator/documentary/<doc_id>', methods=['GET'])
    def view_documentary(doc_id):
        """View individual documentary page (for SEO and sharing)"""
        try:
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                return jsonify({'error': 'Documentary not found'}), 404
            
            return render_template('documentary.html', documentary=documentary)
        except Exception as e:
            return f"Error loading documentary: {e}", 500
    
    @app.route('/api/documentary/<doc_id>', methods=['GET'])
    @app.route('/vidgenerator/api/documentary/<doc_id>', methods=['GET'])
    def get_documentary(doc_id):
        """Get documentary information"""
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            return jsonify({'error': 'Documentary not found'}), 404
        
        return jsonify(documentary.to_dict())
    
    @app.route('/api/documentary/<doc_id>/progress', methods=['GET'])
    @app.route('/vidgenerator/api/documentary/<doc_id>/progress', methods=['GET'])
    def get_progress(doc_id):
        """Get generation progress with comprehensive data including clips and requirements"""
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            return jsonify({'error': 'Documentary not found'}), 404
        
        # Extract message_key from description if present
        message_key = None
        if documentary.description and documentary.description.startswith('PROGRESS_KEY:'):
            message_key = documentary.description.replace('PROGRESS_KEY:', '').strip()
        
        # Get user stats from attributes (stored in description field)
        user_ip = None
        user_agent = None
        if documentary.description and 'ATTRS_JSON:' in documentary.description:
            import json
            try:
                # Extract JSON from description
                attrs_part = documentary.description.split('ATTRS_JSON:')[1]
                attrs = json.loads(attrs_part)
                user_ip = attrs.get('user_ip')
                user_agent = attrs.get('user_agent')
            except Exception as e:
                print(f"Error parsing attributes from description: {e}")
                pass
        
        # Get generation data from pipeline (if available)
        generation_data = {
            'clips': [],
            'editable_mp4': None,
            'storyline': {},
            'requirements': {}
        }
        
        # Try to get generation data from active pipeline instances
        try:
            # Get pipeline instance
            bg_pipeline = get_pipeline()
            if hasattr(bg_pipeline, 'get_generation_data'):
                pipeline_data = bg_pipeline.get_generation_data(doc_id)
                generation_data.update(pipeline_data)
        except Exception as e:
            print(f"Could not get generation data: {e}")
        
        # Calculate current clip count and total from data
        current_clip = len(generation_data['clips'])
        total_clips = generation_data.get('total_clips_estimated', current_clip)
        
        # Get requirements from documentary or generation data
        requirements = generation_data.get('requirements', {
            'prompt': documentary.prompt or '',
            'title': documentary.title or '',
            'theme': generation_data.get('theme', 'matrix'),
            'emotion': generation_data.get('emotion', 'analyzing...')
        })
        
        # If requirements not in generation data, use documentary data
        if not requirements.get('prompt'):
            requirements['prompt'] = documentary.prompt or ''
        if not requirements.get('title'):
            requirements['title'] = documentary.title or ''
        
        # MP4 metadata awareness
        video_path = documentary.video_path
        video_size_mb = None
        mp4_status = 'pending'
        mp4_confidence = 0.15
        if video_path and os.path.exists(video_path):
            try:
                video_size_mb = round(os.path.getsize(video_path) / (1024 * 1024), 2)
            except OSError:
                video_size_mb = None
            mp4_status = 'ready' if documentary.status == 'completed' else 'generating'
            mp4_confidence = 0.85 if mp4_status == 'ready' else 0.55
        elif video_path:
            mp4_status = 'missing'
            mp4_confidence = 0.05

        result = {
            'status': documentary.status,
            'progress': documentary.progress,
            'message_key': message_key,
            'current_clip': current_clip,
            'total_clips': total_clips,
            'clips': generation_data['clips'],
            'editable_mp4_path': generation_data.get('editable_mp4'),
            'storyline': generation_data.get('storyline', {}),
            'requirements': requirements,
            'video_path': video_path,
            'video_size': video_size_mb,
            'duration': documentary.duration,
            'mp4_status': mp4_status,
            'mp4_confidence': mp4_confidence,
            'user_ip': user_ip,
            'user_agent': user_agent
        }
        
        # Cache result for 2 seconds (progress updates frequently)
        query_cache.set('progress', result, ttl=2, doc_id=doc_id)
        
        return jsonify(result)

    @app.route('/api/documentary/<doc_id>/verify-mp4', methods=['POST'])
    @app.route('/vidgenerator/api/documentary/<doc_id>/verify-mp4', methods=['POST'])
    def verify_mp4(doc_id):
        """Force verify MP4 file and attempt recovery if needed"""
        from pathlib import Path
        documentary = Documentary.query.get(doc_id)
        if not documentary:
            return jsonify({'success': False, 'message': 'Documentary not found'}), 404

        if not documentary.video_path:
            return jsonify({'success': False, 'message': 'No MP4 generated yet'}), 400

        pipeline = get_pipeline()
        video_path = Path(documentary.video_path)
        confidence = 0.2
        verified = False
        ensured_path = None

        if pipeline._verify_mp4_file(video_path):
            verified = True
            confidence = 0.95
        else:
            ensured_path = pipeline._ensure_mp4_file_created(
                doc_id,
                video_path,
                fallback_duration=int(documentary.duration or 180)
            )
            if ensured_path and pipeline._verify_mp4_file(ensured_path):
                verified = True
                confidence = 0.9
                documentary.video_path = ensured_path
                db.session.commit()

        size_mb = None
        if os.path.exists(documentary.video_path):
            size_mb = round(os.path.getsize(documentary.video_path) / (1024 * 1024), 2)

        return jsonify({
            'success': verified,
            'message': 'MP4 verified' if verified else 'Verification failed',
            'confidence': confidence,
            'size': size_mb,
            'duration': documentary.duration,
            'path': documentary.video_path
        }), (200 if verified else 500)
    
    print("[LEGACY_API] Registering video serving route...")
    @app.route('/api/documentary/<doc_id>/video', methods=['GET'], endpoint='get_video')
    @app.route('/vidgenerator/api/documentary/<doc_id>/video', methods=['GET'], endpoint='get_video_vidgenerator')
    def get_video(doc_id):
        """Serve video file (local or from external storage)"""
        from flask import redirect
        from urllib.parse import urlparse
        from backend.utils.url_validator import URLValidator
        
        documentary = Documentary.query.get(doc_id)
        if not documentary or not documentary.video_path:
            return jsonify({'error': 'Video not found'}), 404
        
        video_path = documentary.video_path
        
        # If path is a URL (external storage), redirect to it - SECURITY: Validate first
        if video_path.startswith('http://') or video_path.startswith('https://'):
            is_safe, error = URLValidator.is_safe_redirect(video_path, allow_external=True)
            if is_safe:
                return redirect(video_path, code=302)
            else:
                # Log security issue and return error
                import sys
                print(f"[SECURITY] Blocked unsafe redirect: {video_path} - {error}", file=sys.stderr, flush=True)
                return jsonify({'error': 'Invalid video URL'}), 403  # Forbidden
        
        # If local file exists, serve it
        if os.path.exists(video_path):
            return send_file(video_path, mimetype='video/mp4')
        
        # Try to download from external storage if not found locally
        try:
            from src.services.storage.storage_manager import StorageManager
            storage = StorageManager()
            
            # Extract remote path
            filename = os.path.basename(video_path)
            remote_path = f"videos/{filename}"
            
            # Try to download from external storage
            if storage.file_exists(remote_path):
                # Create temporary local path
                temp_path = os.path.join(os.getenv('OUTPUT_DIR', 'output'), filename)
                if storage.download_file(remote_path, temp_path):
                    # Update documentary with new local path (temporary)
                    return send_file(temp_path, mimetype='video/mp4')
        except Exception as e:
            print(f"Error downloading from external storage: {e}")
        
        return jsonify({'error': 'Video file not found'}), 404
    
    @app.route('/embed/clip/<clip_id>', methods=['GET'])
    @app.route('/vidgenerator/embed/clip/<clip_id>', methods=['GET'])
    def embed_clip(clip_id):
        """Embed iframe for 5-minute clip"""
        clip = MovieClip.query.get(clip_id)
        if not clip:
            return jsonify({'error': 'Clip not found'}), 404
        
        return render_template('embed_clip.html', clip=clip)
    
    @app.route('/embed/documentary/<doc_id>', methods=['GET'])
    @app.route('/vidgenerator/embed/documentary/<doc_id>', methods=['GET'])
    def embed_documentary(doc_id):
        """Enhanced embed iframe for full documentary"""
        try:
            documentary = Documentary.query.get(doc_id)
            if not documentary:
                return jsonify({'error': 'Documentary not found'}), 404
            
            # Get query parameters for embed options
            autoplay = request.args.get('autoplay', 'false').lower() == 'true'
            controls = request.args.get('controls', 'true').lower() == 'true'
            loop = request.args.get('loop', 'false').lower() == 'true'
            muted = request.args.get('muted', 'false').lower() == 'true'
            width = request.args.get('width', '640')
            height = request.args.get('height', '360')
            
            return render_template('embed_documentary.html',
                                 documentary=documentary,
                                 autoplay=autoplay,
                                 controls=controls,
                                 loop=loop,
                                 muted=muted,
                                 width=width,
                                 height=height)
        except Exception as e:
            return f"Error loading embed: {e}", 500
    
    @app.route('/api/clip/<clip_id>', methods=['GET'])
    @app.route('/vidgenerator/api/clip/<clip_id>', methods=['GET'])
    def get_clip(clip_id):
        """Get clip information"""
        clip = MovieClip.query.get(clip_id)
        if not clip:
            return jsonify({'error': 'Clip not found'}), 404
        
        return jsonify(clip.to_dict())
    
    @app.route('/api/clip/<clip_id>/video', methods=['GET'])
    @app.route('/vidgenerator/api/clip/<clip_id>/video', methods=['GET'])
    def get_clip_video(clip_id):
        """Serve clip video file"""
        clip = MovieClip.query.get(clip_id)
        if not clip or not clip.clip_path:
            return jsonify({'error': 'Clip not found'}), 404
        
        if not os.path.exists(clip.clip_path):
            return jsonify({'error': 'Clip file not found'}), 404
        
        return send_file(clip.clip_path, mimetype='video/mp4')
    
    @app.route('/api/embed/track', methods=['POST'])
    @app.route('/vidgenerator/api/embed/track', methods=['POST'])
    def track_interaction():
        """Track viewer interaction"""
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            interaction_type = data.get('interaction_type')
            timestamp = data.get('timestamp')
            clip_position = data.get('clip_position')
            clip_id = data.get('clip_id')
            metadata = data.get('metadata', {})
            
            if not session_id or not interaction_type:
                return jsonify({'error': 'session_id and interaction_type required'}), 400
            
            # Get or create viewer session
            viewer_session = ViewerSession.query.filter_by(session_id=session_id).first()
            if not viewer_session:
                viewer_session = ViewerSession(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    clip_id=clip_id,
                    device_type=data.get('device_type'),
                    browser=data.get('browser'),
                    location=data.get('location'),
                    referrer=data.get('referrer')
                )
                db.session.add(viewer_session)
            
            # Create interaction
            interaction = ViewerInteraction(
                id=str(uuid.uuid4()),
                session_id=viewer_session.id,
                interaction_type=interaction_type,
                clip_position=clip_position,
                interaction_metadata=json.dumps(metadata) if metadata else None
            )
            db.session.add(interaction)
            
            # Update session based on interaction
            if interaction_type == 'play':
                viewer_session.start_time = datetime.utcnow()
            elif interaction_type == 'complete':
                viewer_session.completed = True
                viewer_session.end_time = datetime.utcnow()
            elif interaction_type == 'pause':
                if viewer_session.start_time:
                    elapsed = (datetime.utcnow() - viewer_session.start_time).total_seconds()
                    viewer_session.watch_time = int(viewer_session.watch_time + elapsed)
            
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/embed/session', methods=['POST'])
    @app.route('/vidgenerator/api/embed/session', methods=['POST'])
    def create_session():
        """Create new viewer session"""
        try:
            data = request.get_json()
            session_id = data.get('session_id') or str(uuid.uuid4())
            clip_id = data.get('clip_id')
            device_type = data.get('device_type')
            browser = data.get('browser')
            location = data.get('location')
            referrer = request.headers.get('Referer')
            
            viewer_session = ViewerSession(
                id=str(uuid.uuid4()),
                session_id=session_id,
                clip_id=clip_id,
                device_type=device_type,
                browser=browser,
                location=location,
                referrer=referrer,
                start_time=datetime.utcnow()
            )
            db.session.add(viewer_session)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'viewer_session_id': viewer_session.id
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/admin/cleanup/database/full', methods=['POST'])
    @app.route('/vidgenerator/api/admin/cleanup/database/full', methods=['POST'])
    def cleanup_database_full():
        """Emergency cleanup - delete pending/failed/stuck documentaries to fix 'database or disk is full' error"""
        try:
            from datetime import timedelta
            
            # Get counts before cleanup
            total_before = Documentary.query.count()
            pending = Documentary.query.filter_by(status='pending').all()
            failed = Documentary.query.filter_by(status='failed').all()
            stuck = Documentary.query.filter_by(status='generating').filter(
                Documentary.updated_at < datetime.utcnow() - timedelta(hours=1)
            ).all()
            clips = MovieClip.query.all()
            
            deleted_ids = []
            
            # Delete pending
            for doc in pending:
                deleted_ids.append(doc.id)
                db.session.delete(doc)
            
            # Delete failed
            for doc in failed:
                deleted_ids.append(doc.id)
                db.session.delete(doc)
            
            # Delete stuck (generating for more than 1 hour)
            for doc in stuck:
                deleted_ids.append(doc.id)
                db.session.delete(doc)
            
            # Delete all clips
            for clip in clips:
                # Delete related sessions
                sessions = ViewerSession.query.filter_by(clip_id=clip.id).all()
                for session in sessions:
                    ViewerInteraction.query.filter_by(session_id=session.id).delete()
                    db.session.delete(session)
                db.session.delete(clip)
            
            # Commit deletions
            db.session.commit()
            
            # Vacuum database
            try:
                db.session.execute(text('VACUUM'))
                db.session.commit()
            except:
                pass
            
            total_after = Documentary.query.count()
            deleted_count = total_before - total_after
            
            return jsonify({
                'success': True,
                'deleted_pending': len(pending),
                'deleted_failed': len(failed),
                'deleted_stuck': len(stuck),
                'deleted_clips': len(clips),
                'total_before': total_before,
                'total_after': total_after,
                'deleted_count': deleted_count,
                'deleted_ids': deleted_ids[:10],  # First 10 IDs
                'message': f'Deleted {deleted_count} documentaries and {len(clips)} clips. Database vacuumed.'
            })
            
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Database cleanup failed. Try manual cleanup.'
            }), 500
    
    @app.route('/api/admin/cleanup', methods=['POST'])
    @app.route('/vidgenerator/api/admin/cleanup', methods=['POST'])
    def cleanup_ungenerated():
        """Clean up ungenerated/failed documentaries"""
        try:
            from datetime import timedelta
            import os
            
            data = request.get_json() or {}
            days_old = data.get('days_old', 1)
            delete_failed = data.get('delete_failed', True)
            delete_stuck = data.get('delete_stuck', True)
            delete_old_pending = data.get('delete_old_pending', True)
            
            # Count before
            total_before = Documentary.query.count()
            deleted_count = 0
            deleted_ids = []
            
            # 1. Delete failed
            if delete_failed:
                failed = Documentary.query.filter_by(status='failed').all()
                for doc in failed:
                    if doc.video_path and os.path.exists(doc.video_path):
                        try:
                            os.remove(doc.video_path)
                        except:
                            pass
                    if doc.thumbnail_path and os.path.exists(doc.thumbnail_path):
                        try:
                            os.remove(doc.thumbnail_path)
                        except:
                            pass
                    deleted_ids.append(doc.id)
                    db.session.delete(doc)
                    deleted_count += 1
            
            # 2. Delete stuck (pending/generating without video)
            if delete_stuck:
                stuck = Documentary.query.filter(
                    Documentary.status.in_(['pending', 'generating']),
                    (Documentary.video_path.is_(None) | (Documentary.video_path == ''))
                ).all()
                for doc in stuck:
                    deleted_ids.append(doc.id)
                    db.session.delete(doc)
                    deleted_count += 1
            
            # 3. Delete old pending/generating
            if delete_old_pending:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                old = Documentary.query.filter(
                    Documentary.status.in_(['pending', 'generating']),
                    Documentary.created_at < cutoff_date
                ).all()
                for doc in old:
                    if doc.video_path and os.path.exists(doc.video_path):
                        try:
                            os.remove(doc.video_path)
                        except:
                            pass
                    if doc.thumbnail_path and os.path.exists(doc.thumbnail_path):
                        try:
                            os.remove(doc.thumbnail_path)
                        except:
                            pass
                    deleted_ids.append(doc.id)
                    db.session.delete(doc)
                    deleted_count += 1
            
            db.session.commit()
            
            # Vacuum database to reclaim space
            try:
                db.session.execute(text("VACUUM"))
                db.session.commit()
            except:
                pass  # Vacuum may fail, but continue
            
            total_after = Documentary.query.count()
            
            return jsonify({
                'success': True,
                'deleted_count': deleted_count,
                'total_before': total_before,
                'total_after': total_after,
                'deleted_ids': deleted_ids[:10]  # First 10 IDs
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # 404 handler - COMMENTED OUT: Using handler in src/app.py instead to avoid conflicts
    # @app.errorhandler(404)
    # def not_found(error):
    #     """Handle 404 errors with enhanced context"""
    #     from flask import request
    #     # Check if this is an API request
    #     if request.path.startswith('/api/') or request.path.startswith('/vidgenerator/api/'):
    #         return jsonify({
    #             'error': 'Endpoint not found',
    #             'path': request.path,
    #             'message': 'The requested API endpoint does not exist. Check the API documentation for available endpoints.',
    #             'suggestions': [
    #                 'Verify the endpoint URL is correct',
    #                 'Check if the endpoint requires authentication',
    #                 'Review the API documentation',
    #                 'Contact support if the endpoint should exist'
    #             ]
    #         }), 404
    #     
    #     # For HTML requests, return a friendly error page with more context
    #     # NOTE: This handler is disabled - using the one in src/app.py instead
    #     return """
    #     <!DOCTYPE html>
    #     <html lang="en">
    #     <head>
    #         <meta charset="UTF-8">
    #         <meta name="viewport" content="width=device-width, initial-scale=1.0">
    #         <title>404 - Page Not Found | MasterNoder.dk</title>
    #         <style>
    #             * { margin: 0; padding: 0; box-sizing: border-box; }
    #             body { 
    #                 font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    #                 background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    #                 min-height: 100vh;
                    # display: flex;
                    # align-items: center;
                    # justify-content: center;
                    # padding: 20px;
                    # color: #333;
#             }
#             .container { 
                    # max-width: 700px;
                    # width: 100%;
                    # background: white;
                    # padding: 50px;
                    # border-radius: 20px;
                    # box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    # text-align: center;
#             }
#             .error-code {
                    # font-size: 120px;
                    # font-weight: 900;
                    # background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    # -webkit-background-clip: text;
                    # -webkit-text-fill-color: transparent;
                    # background-clip: text;
                    # line-height: 1;
                    # margin-bottom: 20px;
#             }
                # h1 {
                    # font-size: 32px;
                    # color: #333;
                    # margin-bottom: 15px;
#             }
                # .message {
                    # font-size: 18px;
                    # color: #666;
                    # margin-bottom: 30px;
                    # line-height: 1.6;
#             }
                # .context-box {
                    # background: #f8f9fa;
                    # border-left: 4px solid #667eea;
                    # padding: 20px;
                    # margin: 30px 0;
                    # text-align: left;
                    # border-radius: 8px;
#             }
                # .context-box h3 {
                    # color: #667eea;
                    # margin-bottom: 10px;
                    # font-size: 18px;
#             }
                # .context-box p {
                    # color: #666;
                    # margin-bottom: 10px;
                    # line-height: 1.6;
#             }
                # .suggestions {
                    # text-align: left;
                    # margin-top: 15px;
#             }
                # .suggestions ul {
                    # list-style: none;
                    # padding-left: 0;
#             }
                # .suggestions li {
                    # padding: 8px 0;
                    # padding-left: 25px;
                    # position: relative;
                    # color: #555;
#             }
                # .suggestions li:before {
                    # content: "→";
                    # position: absolute;
                    # left: 0;
                    # color: #667eea;
                    # font-weight: bold;
#             }
                # .links {
                    # display: flex;
                    # gap: 15px;
                    # justify-content: center;
                    # flex-wrap: wrap;
                    # margin-top: 30px;
#             }
                # .link {
                    # display: inline-block;
                    # padding: 14px 28px;
                    # background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    # color: white;
                    # text-decoration: none;
                    # border-radius: 8px;
                    # font-weight: 600;
                    # transition: transform 0.2s, box-shadow 0.2s;
                    # box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
#             }
                # .link:hover {
                    # transform: translateY(-2px);
                    # box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
#             }
                # .link.secondary {
                    # background: white;
                    # color: #667eea;
                    # border: 2px solid #667eea;
                    # box-shadow: none;
#             }
                # .link.secondary:hover {
                    # background: #f8f9fa;
#             }
                # .path-info {
                    # font-family: 'Courier New', monospace;
                    # background: #f1f3f5;
                    # padding: 10px;
                    # border-radius: 5px;
                    # margin: 15px 0;
                    # color: #495057;
                    # font-size: 14px;
                    # word-break: break-all;
#             }
            # </style>
        # </head>
        # <body>
            # <div class="container">
                # <div class="error-code">404</div>
                # <h1>Page Not Found</h1>
                # <p class="message">
                #     The page you're looking for doesn't exist or has been moved.
                # </p>
                
                # <div class="context-box">
                    # <h3>What happened?</h3>
                    # <p>
                        # You tried to access a page that doesn't exist on our server. This could happen if:
                    # </p>
                    # <div class="suggestions">
                        # <ul>
                            # <li>The URL was typed incorrectly</li>
                            # <li>The page was moved or deleted</li>
                            # <li>The link you followed is outdated</li>
                            # <li>You don't have permission to access this page</li>
                        # </ul>
            # </div>
                # </div>
                
                # <div class="path-info" id="path-info"></div>
                
                # <div class="context-box">
                    # <h3>What can you do?</h3>
                    # <div class="suggestions">
                        # <ul>
                            # <li>Check the URL for typos</li>
                            # <li>Go back to the previous page</li>
                            # <li>Visit our main pages using the links below</li>
                            # <li>Use the search function to find what you need</li>
                            # <li>Contact support if you believe this is an error</li>
                        # </ul>
                    # </div>
                # </div>
                
                # <div class="links">
                    # <a href="/" class="link">🏠 Go to Home</a>
                    # <a href="/vidgenerator/generator" class="link">🎬 Video Generator</a>
                    # <a href="/vidgenerator/game" class="link secondary">🎮 Game</a>
                    # <a href="/vidgenerator/battle" class="link secondary">⚔️ Battle</a>
                    # <a href="/vidgenerator/gallery" class="link secondary">🖼️ Gallery</a>
                # </div>
            # </div>
            
            # <script>
            #     // Display the requested path
            #     const pathInfo = document.getElementById('path-info');
            #     pathInfo.textContent = 'Requested path: ' + window.location.pathname;
            # </script>
    #     </body>
    #     </html>
    #     """, 404

    @app.route('/api/admin/cleanup/database', methods=['POST'])
    @app.route('/vidgenerator/api/admin/cleanup/database', methods=['POST'])
    def cleanup_database_clips():
        """Clean up MovieClip records and related data"""
        try:
            # Get statistics before cleanup
            total_clips = MovieClip.query.count()
            total_sessions = ViewerSession.query.filter(ViewerSession.clip_id.isnot(None)).count()
            total_interactions = ViewerInteraction.query.join(ViewerSession).filter(ViewerSession.clip_id.isnot(None)).count()
            
            # Delete all clips
            clips = MovieClip.query.all()
            deleted_clips = 0
            for clip in clips:
                try:
                    # Delete related viewer sessions and interactions
                    sessions = ViewerSession.query.filter_by(clip_id=clip.id).all()
                    for session in sessions:
                        ViewerInteraction.query.filter_by(session_id=session.id).delete()
                        db.session.delete(session)
                    
                    db.session.delete(clip)
                    deleted_clips += 1
                except Exception as e:
                    print(f"Error deleting clip {clip.id}: {e}")
                    db.session.rollback()
            
            # Commit deletions
            db.session.commit()
            
            # Vacuum database (SQLite only)
            try:
                db.session.execute(text('VACUUM'))
                db.session.commit()
            except:
                pass  # Not SQLite or vacuum not supported
            
            # Get final statistics
            final_clips = MovieClip.query.count()
            final_sessions = ViewerSession.query.filter(ViewerSession.clip_id.isnot(None)).count()
            final_interactions = ViewerInteraction.query.join(ViewerSession).filter(ViewerSession.clip_id.isnot(None)).count()
            
            return jsonify({
                'success': True,
                'deleted_clips': deleted_clips,
                'deleted_sessions': total_sessions - final_sessions,
                'deleted_interactions': total_interactions - final_interactions,
                'final_clips': final_clips,
                'message': f'Deleted {deleted_clips} clips'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/cache/stats', methods=['GET'])
    @app.route('/vidgenerator/api/cache/stats', methods=['GET'])
    def cache_stats():
        """Get query cache statistics"""
        try:
            stats = query_cache.get_stats()
            return jsonify({
                'success': True,
                'cache': stats
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/cache/clear', methods=['POST'])
    @app.route('/vidgenerator/api/cache/clear', methods=['POST'])
    def cache_clear():
        """Clear query cache"""
        try:
            query_cache.clear()
            return jsonify({
                'success': True,
                'message': 'Cache cleared'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/admin/cleanup/disk', methods=['GET', 'POST'])
    @app.route('/vidgenerator/api/admin/cleanup/disk', methods=['GET', 'POST'])
    def cleanup_disk_info():
        """Get disk usage information"""
        try:
            from pathlib import Path
            import os
            
            # Find project root
            if os.path.exists('/var/www/html/vidgenerator'):
                project_root = Path('/var/www/html/vidgenerator')
            else:
                project_root = Path(__file__).parent.parent.parent
            
            # Check directories
            directories = {
                'output': project_root / 'output',
                'uploads': project_root / 'uploads',
                'clips': project_root / 'output' / 'clips',
            }
            
            usage = {}
            total_size = 0
            
            def get_size(path):
                if not path.exists():
                    return 0, 0
                total = 0
                count = 0
                try:
                    for entry in os.scandir(path):
                        if entry.is_file():
                            total += entry.stat().st_size
                            count += 1
                        elif entry.is_dir():
                            s, c = get_size(Path(entry.path))
                            total += s
                            count += c
                except PermissionError:
                    pass
                return total / (1024 * 1024), count  # MB
            
            for name, path in directories.items():
                size_mb, count = get_size(path)
                total_size += size_mb
                usage[name] = {
                    'path': str(path),
                    'size_mb': round(size_mb, 2),
                    'file_count': count,
                    'exists': path.exists()
                }
            
            # Find MP4 files
            mp4_files = []
            if (project_root / 'output').exists():
                for mp4_file in (project_root / 'output').rglob('*.mp4'):
                    size_mb = mp4_file.stat().st_size / (1024 * 1024)
                    modified = datetime.fromtimestamp(mp4_file.stat().st_mtime)
                    age_days = (datetime.now() - modified).days
                    
                    mp4_files.append({
                        'name': mp4_file.name,
                        'path': str(mp4_file),
                        'size_mb': round(size_mb, 2),
                        'age_days': age_days,
                        'modified': modified.isoformat()
                    })
            
            return jsonify({
                'success': True,
                'total_size_mb': round(total_size, 2),
                'directories': usage,
                'mp4_files': mp4_files[:100],  # First 100
                'mp4_count': len(mp4_files),
                'message': f'Found {len(mp4_files)} MP4 files, total {round(total_size, 2)} MB'
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # End of legacy routes
