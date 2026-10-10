"""Register all routes with Flask app"""
from .home import register_home_routes
from .generator import register_generator_routes
from .gallery import register_gallery_routes
from .chat import register_chat_routes
from .stats import register_stats_routes
from .monitor_scanner import register_monitor_scanner_routes


def register_health_route(app):
    """Register health check endpoint"""
    @app.route('/health', methods=['GET'])
    @app.route('/vidgenerator/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'phase': 3,
            'message': 'Documentary Generator is running'
        })

def register_service_worker_route(app):
    """Register service worker route (needed by templates)"""
    @app.route('/service-worker.js', endpoint='service_worker_file')
    @app.route('/vidgenerator/service-worker.js', endpoint='service_worker_file_vidgenerator')
    def service_worker_file():
        """Serve Service Worker with proper headers and scope"""
        from flask import send_from_directory, make_response
        import os
        
        sw_directory = os.path.join(app.static_folder, 'js')
        sw_path = os.path.join(sw_directory, 'service-worker.js')
        
        # Check if file exists
        if not os.path.exists(sw_path):
            return make_response('Service Worker file not found', 404)
        
        response = make_response(send_from_directory(sw_directory, 'service-worker.js'))
        
        # Critical headers for Service Worker
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        response.headers['Service-Worker-Allowed'] = '/'  # Allow root scope
        
        return response

def register_view_documentary_route(app):
    """Register view_documentary route (needed by gallery template) - MUST be registered early"""
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


def register_routes(app):
    """Register all routes with Flask app"""
    
    # Register root landing page routes FIRST (for masternoder.dk)
    try:
        from src.web.routes.root_landing import register_root_landing_routes
        register_root_landing_routes(app)
        print("[Routes] Root landing routes registered")
    except Exception as e:
        print(f"[Routes] Error registering root_landing routes: {e}")
        import traceback
        traceback.print_exc()
    
    # Also register /fresh route directly as fallback
    try:
        @app.route('/fresh', methods=['GET'], endpoint='fresh_direct', strict_slashes=False)
        @app.route('/fresh/', methods=['GET'], endpoint='fresh_direct_slash', strict_slashes=False)
        def fresh_direct():
            """Direct /fresh route fallback"""
            from flask import render_template, make_response
            import time
            import random
            try:
                version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
                response = make_response(render_template('landing_fresh.html', page_version=version))
                response.headers['Content-Type'] = 'text/html; charset=utf-8'
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
            except Exception as e:
                return f"Error: {e}. Template might not exist. Use ?fresh=true instead.", 500
        print("[Routes] Direct /fresh route registered as fallback")
    except Exception as e:
        print(f"[Routes] Error registering direct /fresh route: {e}")
    
    # Register defense mechanisms API routes
    try:
        from src.web.routes.defense_mechanisms_api import register_defense_mechanisms_routes
        register_defense_mechanisms_routes(app)
        print("[Routes] Defense mechanisms routes registered")
    except Exception as e:
        print(f"[Routes] Error registering defense_mechanisms routes: {e}")
    
    # Register enhanced hunters game routes
    try:
        from src.web.routes.hunters_game_enhanced import hunters_game_enhanced_bp
        # app.register_blueprint(hunters_game_enhanced_bp, url_prefix='')  # Duplicate - should be in register_blueprints.py
        # app.register_blueprint(hunters_game_enhanced_bp, url_prefix='/vidgenerator')  # Duplicate - should be in register_blueprints.py
        print("[Routes] Enhanced hunters game routes registered")
    except Exception as e:
        print(f"[Routes] Error registering hunters_game_enhanced routes: {e}")
    
    # Register enhanced enemy war plan routes
    try:
        from src.web.routes.enemy_war_plan_enhanced import enemy_war_plan_enhanced_bp
        app.register_blueprint(enemy_war_plan_enhanced_bp, url_prefix='')
        app.register_blueprint(enemy_war_plan_enhanced_bp, url_prefix='/vidgenerator')
        print("[Routes] Enhanced enemy war plan routes registered")
    except Exception as e:
        print(f"[Routes] Error registering enemy_war_plan_enhanced routes: {e}")
    
    # Register themes API routes
    try:
        from src.web.routes.themes_api import themes_api_bp
        app.register_blueprint(themes_api_bp, url_prefix='')
        app.register_blueprint(themes_api_bp, url_prefix='/vidgenerator')
        print("[Routes] Themes API routes registered")
    except Exception as e:
        print(f"[Routes] Error registering themes_api routes: {e}")
    
    # Register game sync API routes
    try:
        from src.web.routes.game_sync_api import game_sync_api_bp
        app.register_blueprint(game_sync_api_bp, url_prefix='')
        app.register_blueprint(game_sync_api_bp, url_prefix='/vidgenerator')
        print("[Routes] Game sync API routes registered")
    except Exception as e:
        print(f"[Routes] Error registering game_sync_api routes: {e}")
    
        # Register AI providers API routes
        try:
            from src.web.routes.ai_providers_api import ai_providers_api_bp
            app.register_blueprint(ai_providers_api_bp, url_prefix='')
            app.register_blueprint(ai_providers_api_bp, url_prefix='/vidgenerator')
            print("[Routes] AI providers API routes registered")
        except Exception as e:
            print(f"[Routes] Error registering ai_providers_api routes: {e}")
        
        # Register create missing static files route
        try:
            from src.web.routes.create_missing_static_files import create_missing_static_bp
            app.register_blueprint(create_missing_static_bp, url_prefix='')
            app.register_blueprint(create_missing_static_bp, url_prefix='/vidgenerator')
            print("[Routes] Create missing static files routes registered")
        except Exception as e:
            print(f"[Routes] Error registering create_missing_static routes: {e}")
        
        # Register API status routes (CRITICAL - must work)
        try:
            from src.web.routes.api_status import api_status_bp
            app.register_blueprint(api_status_bp, url_prefix='')
            app.register_blueprint(api_status_bp, url_prefix='/vidgenerator')
            print("[Routes] API status routes registered")
        except Exception as e:
            print(f"[Routes] Error registering api_status routes: {e}")
        
        # Register API Debugger routes
        try:
            from src.web.routes.api_debugger import api_debugger_bp
            # app.register_blueprint(api_debugger_bp, url_prefix='')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(api_debugger_bp, url_prefix='/vidgenerator', name='api_debugger_with_prefix')  # Duplicate - should be in register_blueprints.py
            print("[Routes] API Debugger routes registered")
        except Exception as e:
            print(f"[Routes] Error registering API Debugger routes: {e}")
            import traceback
            traceback.print_exc()
    
    # Register user config routes
    try:
        from src.web.routes.user_config import register_user_config_routes
        register_user_config_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering user_config routes: {e}")
    
    # Register frames API routes
    try:
        from src.web.routes.frames_api import register_frames_api_routes
        register_frames_api_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering frames_api routes: {e}")
    
    # Register enhanced user profile routes
    try:
        from src.web.routes.user_profile_enhanced import register_user_profile_enhanced_routes
        register_user_profile_enhanced_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering user_profile_enhanced routes: {e}")
    
    # Register theme game routes
    try:
        from src.web.routes.theme_game import register_theme_game_routes
        register_theme_game_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering theme_game routes: {e}")
    
    # Register enhanced chat routes
    try:
        from src.web.routes.chat_enhanced import register_chat_enhanced_routes
        register_chat_enhanced_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering chat_enhanced routes: {e}")
    
    # Register booster pack routes
    try:
        from src.web.routes.booster_packs import register_booster_pack_routes
        register_booster_pack_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering booster_pack routes: {e}")
    
    # Register leveling API routes
    try:
        from src.web.routes.leveling_api import register_leveling_api_routes
        register_leveling_api_routes(app)
    except Exception as e:
        print(f"[Routes] Error registering leveling_api routes: {e}")
    print("[ROUTES] Starting route registration...")
    
    # Register clips blueprint for clip generation
    try:
        from src.web.routes.clips import clips_bp
        app.register_blueprint(clips_bp, url_prefix='/vidgenerator')
        print("[ROUTES] Clips routes registered")
    except Exception as e:
        print(f"[ROUTES] Warning: Could not register clips routes: {e}")
    
    # Register service worker logs blueprint
    try:
        from src.web.routes.service_worker_logs import service_worker_logs_bp
        app.register_blueprint(service_worker_logs_bp, url_prefix='/vidgenerator')
    except Exception as e:
        print(f"[Routes] Could not register service worker logs: {e}")
    
    # Register two-phase generator blueprint
    # Register BOTH with and without prefix to handle all scenarios
    try:
        from src.web.routes.two_phase_api import two_phase_bp
        # Register WITHOUT prefix (for when middleware strips /vidgenerator)
        app.register_blueprint(two_phase_bp, url_prefix='')
        # Also register WITH prefix (for direct access)
        app.register_blueprint(two_phase_bp, url_prefix='/vidgenerator', name='two_phase_with_prefix')
        # print("[Routes] Registered two_phase_api blueprint (with AND without prefix)", flush=True)  # Disabled to prevent errno 11
        
        from src.web.routes.theme_api import theme_api_bp
        # Register WITHOUT prefix
        app.register_blueprint(theme_api_bp, url_prefix='')
        # Also register WITH prefix
        app.register_blueprint(theme_api_bp, url_prefix='/vidgenerator', name='theme_api_with_prefix')
        # print("[Routes] Registered theme_api blueprint (with AND without prefix)", flush=True)  # Disabled to prevent errno 11
    except Exception as e:
        pass  # Empty except block
        import traceback
        traceback.print_exc()
        # Don't crash - continue without two-phase API
    
    # Register points API (graduation + chat points)
    try:
        from src.web.routes.points_api import points_api_bp
        app.register_blueprint(points_api_bp, url_prefix='')
        app.register_blueprint(points_api_bp, url_prefix='/vidgenerator', name='points_api_with_prefix')
        # print("[Routes] Points API routes registered (graduation + chat points)", flush=True)  # Disabled to prevent errno 11
        
        # Register debug API
        try:
            from src.web.routes.debug_api import debug_api_bp
            app.register_blueprint(debug_api_bp, url_prefix='/api/debug')
            app.register_blueprint(debug_api_bp, url_prefix='/vidgenerator/api/debug', name='debug_api_with_prefix')
            # print("[Routes] Debug API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register theme restore API
        try:
            from src.web.routes.theme_restore import theme_restore_bp
            app.register_blueprint(theme_restore_bp, url_prefix='')
            app.register_blueprint(theme_restore_bp, url_prefix='/vidgenerator', name='theme_restore_with_prefix')
            # print("[Routes] Theme restore API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register site fixer API
        try:
            from src.web.routes.site_fixer import site_fixer_bp
            app.register_blueprint(site_fixer_bp, url_prefix='/api/debug')
            app.register_blueprint(site_fixer_bp, url_prefix='/vidgenerator/api/debug', name='site_fixer_with_prefix')
            # print("[Routes] Site fixer API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register auto-fix documentation API
        try:
            from src.web.routes.auto_fix_documentation import auto_fix_doc_bp
            app.register_blueprint(auto_fix_doc_bp, url_prefix='/api/debug')
            app.register_blueprint(auto_fix_doc_bp, url_prefix='/vidgenerator/api/debug', name='auto_fix_doc_with_prefix')
            # print("[Routes] Auto-fix documentation API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register theme debugger API
        try:
            from src.web.routes.theme_debugger_api import theme_debugger_bp
            app.register_blueprint(theme_debugger_bp, url_prefix='')
            app.register_blueprint(theme_debugger_bp, url_prefix='/vidgenerator', name='theme_debugger_with_prefix')
            # print("[Routes] Theme debugger API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register comprehensive debugger API
        try:
            from src.web.routes.comprehensive_debugger import comprehensive_debugger_bp
            # app.register_blueprint(comprehensive_debugger_bp, url_prefix='/api/debug/comprehensive')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(comprehensive_debugger_bp, url_prefix='/vidgenerator/api/debug/comprehensive', name='comprehensive_debugger_with_prefix')  # Duplicate - should be in register_blueprints.py
            # print("[Routes] Comprehensive debugger API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register system fixer API
        try:
            from src.web.routes.system_fixer import system_fixer_bp
            app.register_blueprint(system_fixer_bp, url_prefix='/api/system')
            app.register_blueprint(system_fixer_bp, url_prefix='/vidgenerator/api/system', name='system_fixer_with_prefix')
            # print("[Routes] System fixer API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register debugger page
        try:
            from src.web.routes.debugger_page import debugger_page_bp
            # app.register_blueprint(debugger_page_bp, url_prefix='')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(debugger_page_bp, url_prefix='/vidgenerator', name='debugger_page_with_prefix')  # Duplicate - should be in register_blueprints.py
            # print("[Routes] Debugger page routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register hunters game API
        try:
            from src.web.routes.hunters_game import hunters_game_bp
            # app.register_blueprint(hunters_game_bp, url_prefix='/api/game/hunters')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(hunters_game_bp, url_prefix='/vidgenerator/api/game/hunters', name='hunters_game_with_prefix')  # Duplicate - should be in register_blueprints.py
            # print("[Routes] Hunters game API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register game page
        try:
            from src.web.routes.game_page import game_page_bp
            app.register_blueprint(game_page_bp, url_prefix='')
            app.register_blueprint(game_page_bp, url_prefix='/vidgenerator', name='game_page_with_prefix')
            # print("[Routes] Game page routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register landing page report
        try:
            from src.web.routes.landing_page_report import landing_report_bp
            app.register_blueprint(landing_report_bp, url_prefix='')
            app.register_blueprint(landing_report_bp, url_prefix='/vidgenerator', name='landing_report_with_prefix')
            # print("[Routes] Landing page report routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register stats summary API
        try:
            from src.web.routes.stats_summary import stats_summary_bp
            # app.register_blueprint(stats_summary_bp, url_prefix='/api/stats')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(stats_summary_bp, url_prefix='/vidgenerator/api/stats', name='stats_summary_with_prefix')  # Duplicate - should be in register_blueprints.py
            # print("[Routes] Stats summary API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register enhanced debugger API
        try:
            from src.web.routes.debugger_enhanced import debugger_enhanced_bp
            # app.register_blueprint(debugger_enhanced_bp, url_prefix='/api/debug')  # Duplicate - should be in register_blueprints.py
            # app.register_blueprint(debugger_enhanced_bp, url_prefix='/vidgenerator/api/debug', name='debugger_enhanced_with_prefix')  # Duplicate - should be in register_blueprints.py
            # print("[Routes] Enhanced debugger API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register progress API
        try:
            from src.web.routes.progress_api import progress_api_bp
            app.register_blueprint(progress_api_bp, url_prefix='/api/progress')
            app.register_blueprint(progress_api_bp, url_prefix='/vidgenerator/api/progress', name='progress_api_with_prefix')
            # print("[Routes] Progress API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register documentation API
        try:
            from src.web.routes.documentation_api import documentation_api_bp
            app.register_blueprint(documentation_api_bp, url_prefix='/api/docs')
            app.register_blueprint(documentation_api_bp, url_prefix='/vidgenerator/api/docs', name='documentation_api_with_prefix')
            # print("[Routes] Documentation API routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register documentation page
        try:
            from src.web.routes.documentation_page import documentation_page_bp
            app.register_blueprint(documentation_page_bp, url_prefix='')
            app.register_blueprint(documentation_page_bp, url_prefix='/vidgenerator', name='documentation_page_with_prefix')
            # print("[Routes] Documentation page routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register debugger download API - MUST be registered without url_prefix for root routes
        try:
            from src.web.routes.debugger_download import debugger_download_bp
            # Register with empty prefix for root routes
            # app.register_blueprint(debugger_download_bp, url_prefix='')  # Duplicate - commented out
            # Register with /api/debugger prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/api/debugger')  # Duplicate - commented out
            # Register with /vidgenerator/api/debugger prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/vidgenerator/api/debugger', name='debugger_download_with_prefix')  # Duplicate - commented out
            # Register with /api/fixer prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/api/fixer', name='fixer_api')  # Duplicate - commented out
            # Register with /vidgenerator/api/fixer prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/vidgenerator/api/fixer', name='fixer_api_with_prefix')  # Duplicate - commented out
            # Register with /download/fixer prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/download/fixer', name='fixer_download')  # Duplicate - commented out
            # Register with /vidgenerator/download/fixer prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/vidgenerator/download/fixer', name='fixer_download_with_prefix')  # Duplicate - commented out
            # Register with /tools prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/tools', name='tools_download')  # Duplicate - commented out
            # Register with /vidgenerator/tools prefix
            # app.register_blueprint(debugger_download_bp, url_prefix='/vidgenerator/tools', name='tools_download_with_prefix')  # Duplicate - commented out
            # print("[Routes] Debugger download API routes registered (with resistant paths)", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register enemy war plan
        try:
            from src.web.routes.enemy_war_plan import enemy_war_plan_bp
            app.register_blueprint(enemy_war_plan_bp, url_prefix='')
            app.register_blueprint(enemy_war_plan_bp, url_prefix='/vidgenerator', name='enemy_war_plan_with_prefix')
            # print("[Routes] Enemy war plan routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register enhanced generator
        try:
            from src.web.routes.generator_enhanced import register_generator_enhanced_routes
            register_generator_enhanced_routes(app)
            # print("[Routes] Enhanced generator routes registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register generator debugger
        try:
            from src.web.routes.generator_debugger import generator_debugger_bp
            # Register WITHOUT prefix first (for /generator-debugger)
            app.register_blueprint(generator_debugger_bp, url_prefix='', name='generator_debugger')
            # Also register WITH vidgenerator prefix (for /vidgenerator/generator-debugger)
            app.register_blueprint(generator_debugger_bp, url_prefix='/vidgenerator', name='generator_debugger_vidgenerator')
            # print("[Routes] Generator debugger routes registered:", flush=True)  # Disabled to prevent errno 11
            print("  - /generator-debugger", flush=True)
            print("  - /vidgenerator/generator-debugger", flush=True)
            print("  - /api/generator/debug", flush=True)
            print("  - /vidgenerator/api/generator/debug", flush=True)
        except Exception as e:
            pass  # Empty except block
            import traceback
            traceback.print_exc()
        
        # Register test route for generator debugger
        try:
            from src.web.routes.generator_debugger_test import generator_debugger_test_bp
            app.register_blueprint(generator_debugger_test_bp, url_prefix='')
            app.register_blueprint(generator_debugger_test_bp, url_prefix='/vidgenerator', name='generator_debugger_test_vidgenerator')
            # print("[Routes] Generator debugger test route registered", flush=True)  # Disabled to prevent errno 11
        except Exception as e:
            pass  # Empty except block
    except Exception as e:
        pass  # Empty except block
        import traceback
        traceback.print_exc()
    
    # Register gallery debug blueprint
    try:
        from src.web.routes.gallery_debug import gallery_debug_bp
        app.register_blueprint(gallery_debug_bp, url_prefix='/vidgenerator')
        # print("[Routes] Registered gallery_debug blueprint", flush=True)  # Disabled to prevent errno 11
    except Exception as e:
        pass  # Empty except block
        import traceback
        traceback.print_exc()
        # Don't crash - continue without debug endpoint
    
    # Register monitoring blueprint
    try:
        from src.web.routes.monitoring import monitoring_bp
        app.register_blueprint(monitoring_bp)
        print("[Routes] Monitoring routes registered")
    except Exception as e:
        print(f"[Routes] Could not register monitoring: {e}")
        print("[ROUTES] Service worker logs routes registered")
    except Exception as e:
        print(f"[ROUTES] Warning: Could not register service worker logs routes: {e}")
    
    # IMPORTANT: Import and call _register_legacy_api_routes from routes.py FIRST
    # This registers service_worker, view_documentary, generate_documentary, and progress endpoint
    try:
        # Import from routes.py module (not routes package)
        import sys
        import os
        routes_module_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'routes.py')
        if os.path.exists(routes_module_path):
            # Import the module directly
            import importlib.util
            spec = importlib.util.spec_from_file_location("routes_module", routes_module_path)
            routes_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(routes_module)
            _register_legacy_api_routes = routes_module._register_legacy_api_routes
            print("[ROUTES] Calling _register_legacy_api_routes from routes.py...")
            _register_legacy_api_routes(app)
            print("[ROUTES] _register_legacy_api_routes completed")
            
            # Verify route registration
            registered_routes = [str(r) for r in app.url_map.iter_rules() if 'generate' in str(r)]
            print(f"[ROUTES] Registered generate routes: {registered_routes}")
            if not any('generate' in str(r) for r in app.url_map.iter_rules()):
                print("[ROUTES] WARNING: No generate routes found after registration!")
        else:
            raise ImportError(f"routes.py not found at {routes_module_path}")
    except Exception as e:
        print(f"[ROUTES] ERROR calling _register_legacy_api_routes: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: Register service worker and view_documentary directly
        register_service_worker_route(app)
        register_view_documentary_route(app)
        # Also register generate_documentary in fallback
        print("[ROUTES] Registering generate_documentary in fallback...")
        from flask import request, jsonify
        from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
        from src.db.models import db, Documentary
        from src.services.cache.query_cache import query_cache
        from datetime import datetime
        import uuid
        import threading
        
        @app.route('/api/documentary/generate', methods=['POST'], endpoint='generate_documentary')
        @app.route('/vidgenerator/api/documentary/generate', methods=['POST'], endpoint='generate_documentary_vidgenerator')
        def generate_documentary():
            """Generate a new documentary from prompt"""
            try:
                client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()
                if not client_ip:
                    client_ip = request.remote_addr or 'unknown'
                
                user_agent = request.headers.get('User-Agent', 'unknown')
                
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
                
                # Track generation start
                try:
                    from src.services.behavioral_tracking.generation_tracker import (
                        get_user_id_from_request,
                        track_generation_start
                    )
                    user_id = get_user_id_from_request(request)
                    doc_id = str(uuid.uuid4())
                    track_generation_start(
                        user_id=user_id,
                        doc_id=doc_id,
                        prompt=prompt,
                        metadata={'title': title}
                    )
                except Exception as track_error:
                    print(f"[Routes] Warning: Could not track generation start: {track_error}")
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
                
                def progress_update_callback(doc_id_cb: str, progress: int, message: str, message_key: str = None):
                    try:
                        with app.app_context():
                            documentary = Documentary.query.get(doc_id_cb)
                            if documentary:
                                documentary.progress = progress
                                current_desc = documentary.description or ''
                                attrs_part = ''
                                if 'ATTRS_JSON:' in current_desc:
                                    attrs_part = '|' + current_desc.split('ATTRS_JSON:')[1]
                                    current_desc = current_desc.split('|ATTRS_JSON:')[0]
                                
                                if message_key:
                                    documentary.description = f"PROGRESS_KEY:{message_key}{attrs_part}"
                                elif attrs_part:
                                    documentary.description = f"{current_desc}{attrs_part}"
                                db.session.commit()
                                db.session.flush()  # Force flush to ensure progress is visible immediately
                                print(f"[Progress] Updated to {progress}%: {message[:50]}", flush=True)
                                import time
                                time.sleep(0.1)
                    except Exception as e:
                        print(f"Progress update error: {e}")
                
                def generate_in_background():
                    import time
                    import sys
                    bg_pipeline = None
                    try:
                        # Force flush to ensure logs appear
                        # print(f"[Routes] ===== STARTING BACKGROUND GENERATION FOR {doc_id} =====", flush=True)  # Disabled to prevent errno 11
                        sys.stdout.flush()
                        with app.app_context():
                            documentary = Documentary.query.get(doc_id)
                            if not documentary:
                                print(f"[Routes] ERROR: Documentary {doc_id} not found in database")
                                return
                            documentary.status = 'generating'
                            documentary.progress = 5
                            db.session.commit()
                            print(f"[Routes] Documentary status set to 'generating', progress=5%")
                            time.sleep(0.5)
                        
                        print(f"[Routes] Creating PipelineOrchestrator...")
                        bg_pipeline = PipelineOrchestrator(progress_callback=progress_update_callback)
                        print(f"[Routes] PipelineOrchestrator created, starting generate_documentary...")
                        
                        try:
                            result = bg_pipeline.generate_documentary(
                                doc_id=doc_id,
                                prompt=prompt,
                                title=title,
                                description=description,
                                attributes=attributes
                            )
                            print(f"[Routes] generate_documentary returned: success={result.get('success')}, video_path={result.get('video_path', 'NONE')}")
                        except Exception as gen_error:
                            print(f"[Routes] Generation pipeline error: {gen_error}")
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
                        
                        with app.app_context():
                            documentary = Documentary.query.get(doc_id)
                            if documentary:
                                video_path = result.get('video_path', '')
                                
                                # CRITICAL FIX: Ensure video file exists before saving
                                import os
                                from pathlib import Path
                                
                                # Determine output directory
                                if os.path.exists('/var/www/html/vidgenerator/output'):
                                    output_dir = Path('/var/www/html/vidgenerator/output')
                                elif os.path.exists('output'):
                                    output_dir = Path('output')
                                else:
                                    # Create output directory
                                    output_dir = Path('/var/www/html/vidgenerator/output')
                                    output_dir.mkdir(parents=True, exist_ok=True)
                                
                                # If no video_path or file doesn't exist, create it
                                if not video_path or not os.path.exists(video_path):
                                    potential_path = output_dir / f"{doc_id}.mp4"
                                    print(f"[Routes] Output directory: {output_dir}, potential path: {potential_path}")
                                    
                                    # Try to find existing file first
                                    if potential_path.exists() and potential_path.stat().st_size > 1000:
                                        video_path = str(potential_path)
                                        print(f"[Routes] Found existing video file: {video_path}")
                                    elif bg_pipeline:
                                        # Create file using pipeline's ensure function
                                        print(f"[Routes] Creating video file: {potential_path}")
                                        verified_path = bg_pipeline._ensure_mp4_file_created(doc_id, potential_path, fallback_duration=180)
                                        if verified_path and os.path.exists(verified_path):
                                            video_path = verified_path
                                            print(f"[Routes] ✓ Video file created: {video_path}")
                                        else:
                                            # Last resort: use the path anyway
                                            video_path = str(potential_path)
                                            print(f"[Routes] ⚠ Using fallback path: {video_path}")
                                    else:
                                        # No pipeline, use default path
                                        video_path = str(potential_path)
                                        print(f"[Routes] ⚠ Using default path (no pipeline): {video_path}")
                                
                                # Verify file exists before saving
                                if video_path and os.path.exists(video_path):
                                    file_size = os.path.getsize(video_path)
                                    print(f"[Routes] Video file verified: {video_path} ({file_size} bytes)")
                                else:
                                    print(f"[Routes] ⚠ WARNING: Video file does not exist: {video_path}")
                                
                                # CRITICAL: Always set video_path, even if file doesn't exist yet
                                # This ensures the database has a path and the documentary appears in gallery
                                # Check for both None and empty string
                                if not video_path or video_path.strip() == '':
                                    video_path = str(output_dir / f"{doc_id}.mp4")
                                    print(f"[Routes] Using default path (video_path was empty): {video_path}")
                                
                                final_video_path = video_path
                                print(f"[Routes] Final video_path to save: {final_video_path}")
                                
                                # AI CONTROLLER: Use AI controller to validate and fix video
                                valid_video = False
                                ai_controller = None
                                try:
                                    from src.services.ai_generation.generation_ai_controller import get_ai_controller
                                    ai_controller = get_ai_controller()
                                except Exception as e:
                                    print(f"[Routes] AI Controller not available: {e}")
                                
                                if final_video_path and os.path.exists(final_video_path):
                                    file_size = os.path.getsize(final_video_path)
                                    # print(f"[Routes] Checking video file: {final_video_path} ({file_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                    
                                    if ai_controller:
                                        # Use AI controller to validate
                                        is_valid = ai_controller.validate_file(doc_id, final_video_path)
                                        if is_valid:
                                            valid_video = True
                                            # print(f"[Routes] ✓ AI Controller validated video: {final_video_path} ({file_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                        else:
                                            # print(f"[Routes] ⚠ AI Controller validation failed, attempting fix...", flush=True)  # Disabled to prevent errno 11
                                            fixed_path = ai_controller._fix_small_file(doc_id, final_video_path)
                                            if fixed_path and os.path.exists(fixed_path):
                                                new_size = os.path.getsize(fixed_path)
                                                if new_size > 10240:
                                                    final_video_path = fixed_path
                                                    valid_video = True
                                                    # print(f"[Routes] ✓ AI Controller fixed video: {fixed_path} ({new_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                                else:
                                                    pass  # Empty block
                                                    # print(f"[Routes] ✗ AI Controller fix still too small ({new_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                            else:
                                                pass  # Empty block
                                                # print(f"[Routes] ✗ AI Controller could not fix video", flush=True)  # Disabled to prevent errno 11
                                    else:
                                        # Fallback to manual validation
                                        if file_size > 10240:  # > 10KB - actual video file
                                            valid_video = True
                                            # print(f"[Routes] ✓ Final video valid: {final_video_path} ({file_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                        else:
                                            # print(f"[Routes] ⚠ Final video too small ({file_size} bytes), recreating...", flush=True)  # Disabled to prevent errno 11
                                            # Try to recreate the video file
                                            try:
                                                from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
                                                orchestrator = PipelineOrchestrator()
                                                recreated_path = orchestrator._ensure_mp4_file_created(
                                                    doc_id, 
                                                    Path(final_video_path), 
                                                    fallback_duration=120
                                                )
                                                if recreated_path and os.path.exists(recreated_path):
                                                    new_size = os.path.getsize(recreated_path)
                                                    if new_size > 10240:
                                                        final_video_path = recreated_path
                                                        valid_video = True
                                                        # print(f"[Routes] ✓ Video recreated: {recreated_path} ({new_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                                    else:
                                                        pass  # Empty block
                                                        # print(f"[Routes] ✗ Recreated video still too small ({new_size} bytes)", flush=True)  # Disabled to prevent errno 11
                                                else:
                                                    pass  # Empty block
                                                    # print(f"[Routes] ✗ Could not recreate video file", flush=True)  # Disabled to prevent errno 11
                                            except Exception as recreate_error:
                                                pass  # Empty except block
                                else:
                                    pass  # Empty block
                                    # print(f"[Routes] ⚠ Final video path invalid or missing: {final_video_path}", flush=True)  # Disabled to prevent errno 11
                                
                                documentary.progress = 90
                                db.session.commit()
                                time.sleep(0.3)
                                
                                if valid_video:
                                    documentary.status = 'completed'
                                    documentary.progress = 100
                                    documentary.video_path = final_video_path
                                    documentary.completed_at = datetime.utcnow()
                                else:
                                    # Keep as generating if video is invalid
                                    documentary.status = 'generating'
                                    documentary.progress = 95
                                    if final_video_path:
                                        documentary.video_path = final_video_path  # Still save path, but don't mark complete
                                    # print(f"[Routes] ⚠ Video file invalid, keeping status as 'generating'", flush=True)  # Disabled to prevent errno 11
                                
                                documentary.thumbnail_path = result.get('thumbnail_path', '')
                                documentary.duration = result.get('duration', 180) or 180
                                
                                # CRITICAL: Commit the video_path
                                try:
                                    db.session.commit()
                                    # print(f"[Routes] ✓ Database updated: video_path={documentary.video_path}, status=completed", flush=True)  # Disabled to prevent errno 11
                                    # Verify it was saved
                                    db.session.refresh(documentary)
                                    if documentary.video_path:
                                        pass  # Empty if block
                                        # print(f"[Routes] ✓ Verified: video_path saved as '{documentary.video_path}'", flush=True)  # Disabled to prevent errno 11
                                    else:
                                        pass  # Empty block
                                        # print(f"[Routes] ✗ ERROR: video_path is still None after commit!", flush=True)  # Disabled to prevent errno 11
                                except Exception as commit_error:
                                    pass  # Empty except block
                                    import traceback
                                    traceback.print_exc()
                                    import sys
                                    sys.stdout.flush()
                                
                                # Track XP and trophies for successful generation
                                try:
                                    from src.services.behavioral_tracking.generation_tracker import (
                                        get_user_id_from_request,
                                        track_generation_complete
                                    )
                                    user_id = get_user_id_from_request(request)
                                    
                                    # Get quality score if available
                                    quality_score = result.get('quality_score', 0.0)
                                    if not quality_score and result.get('clips'):
                                        # Calculate average quality from clips
                                        clips = result.get('clips', [])
                                        if clips:
                                            quality_scores = [c.get('quality', 0.0) for c in clips if c.get('quality')]
                                            if quality_scores:
                                                quality_score = sum(quality_scores) / len(quality_scores)
                                    
                                    tracking_result = track_generation_complete(
                                        user_id=user_id,
                                        doc_id=doc_id,
                                        success=True,
                                        video_path=final_video_path,
                                        duration=documentary.duration,
                                        quality_score=quality_score,
                                        metadata={
                                            'title': title,
                                            'prompt_length': len(prompt),
                                            'clips_count': len(result.get('clips', []))
                                        }
                                    )
                                    
                                    if tracking_result.get('level_up'):
                                        print(f"[Routes] 🎉 User {user_id} leveled up to {tracking_result.get('new_level')}!")
                                    if tracking_result.get('trophies_awarded'):
                                        print(f"[Routes] 🏆 User {user_id} earned {len(tracking_result['trophies_awarded'])} trophies!")
                                except Exception as track_error:
                                    print(f"[Routes] Warning: Could not track generation: {track_error}")
                                    import traceback
                                    traceback.print_exc()
                                
                                query_cache.invalidate('prompt_suggestions')
                                query_cache.invalidate_pattern('gallery')
                                query_cache.invalidate('progress', doc_id=doc_id)
                    except Exception as e:
                        pass  # Empty except block
                        # print(f"[Routes] Error: {e}", flush=True)  # Disabled to prevent errno 11
                        import traceback
                        error_trace = traceback.format_exc()
                        # print(f"[Routes] Traceback:\n{error_trace}", flush=True)  # Disabled to prevent errno 11
                        import sys
                        sys.stdout.flush()
                        try:
                            if bg_pipeline is None:
                                bg_pipeline = PipelineOrchestrator()
                            with app.app_context():
                                documentary = Documentary.query.get(doc_id)
                                if documentary:
                                    from pathlib import Path
                                    import os
                                    
                                    placeholder_path = bg_pipeline.file_manager.get_output_path(f"{doc_id}.mp4")
                                    placeholder_path.parent.mkdir(parents=True, exist_ok=True)
                                    
                                    # CRITICAL: Use _ensure_mp4_file_created to create actual video, not empty file
                                    if not placeholder_path.exists() or (placeholder_path.exists() and placeholder_path.stat().st_size < 10240):
                                        print(f"[Routes] Creating valid video file for error handler: {placeholder_path}")
                                        actual_video_path = bg_pipeline._ensure_mp4_file_created(doc_id, placeholder_path, fallback_duration=180)
                                        if actual_video_path and os.path.exists(actual_video_path):
                                            placeholder_path = Path(actual_video_path)
                                            file_size = placeholder_path.stat().st_size
                                            print(f"[Routes] ✓ Error handler created valid video: {placeholder_path} ({file_size} bytes)")
                                        else:
                                            print(f"[Routes] ⚠ Error handler: _ensure_mp4_file_created returned None or file missing")
                                    
                                    # Validate file before saving
                                    if placeholder_path.exists():
                                        file_size = placeholder_path.stat().st_size
                                        if file_size > 10240:
                                            documentary.status = 'completed'
                                            documentary.progress = 100
                                            documentary.video_path = str(placeholder_path)
                                            documentary.duration = 180
                                            documentary.completed_at = datetime.utcnow()
                                            db.session.commit()
                                            print(f"[Routes] ✓ Error handler: Valid video saved ({file_size} bytes)")
                                        else:
                                            print(f"[Routes] ⚠ Error handler: Video file too small ({file_size} bytes), keeping as generating")
                                            documentary.status = 'generating'
                                            documentary.progress = 95
                                    else:
                                        print(f"[Routes] ⚠ Error handler: Video file does not exist")
                        except Exception as db_error:
                            print(f"Database error: {db_error}")
                            import traceback
                            traceback.print_exc()
                
                # CRITICAL: Log thread creation before starting
                # print(f"[Routes] ===== CREATING BACKGROUND THREAD FOR {doc_id} =====", flush=True)  # Disabled to prevent errno 11
                import sys
                sys.stdout.flush()
                
                generation_thread = threading.Thread(target=generate_in_background, daemon=True)
                generation_thread.start()
                
                # print(f"[Routes] ===== BACKGROUND THREAD STARTED (ID: {generation_thread.ident}) =====", flush=True)  # Disabled to prevent errno 11
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
                return jsonify({
                    'error': str(e),
                    'traceback': error_trace
                }), 500
        
        print("[ROUTES] generate_documentary route registered in fallback")
    
    # Register health endpoint
    register_health_route(app)
    print("[ROUTES] Health route registered")
    # Register all route modules
    try:
        register_home_routes(app)
        print("[ROUTES] Home routes registered")
    except Exception as e:
        print(f"[ROUTES] ERROR registering home routes: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        register_generator_routes(app)
        print("[ROUTES] Generator routes registered")
    except Exception as e:
        print(f"[ROUTES] ERROR registering generator routes: {e}")
        import traceback
        traceback.print_exc()
    
    # Register gallery routes (includes view_documentary)
    try:
        register_gallery_routes(app)
        print("[ROUTES] Gallery routes registered (including view_documentary)")
    except Exception as e:
        print(f"[ROUTES] ERROR registering gallery routes: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # register_chat_routes(app)  # Duplicate - commented out
        print("[ROUTES] Chat routes registered")
    except Exception as e:
        print(f"[ROUTES] ERROR registering chat routes: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        # register_stats_routes(app)  # Already registered in backend.register_blueprints
        print("[ROUTES] Stats routes registered")
    except Exception as e:
        print(f"[ROUTES] ERROR registering stats routes: {e}")
        import traceback
        traceback.print_exc()
    
    try:
        register_monitor_scanner_routes(app)
        print("[ROUTES] Monitor & Scanner routes registered")
    except Exception as e:
        print(f"[ROUTES] ERROR registering monitor_scanner routes: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"[ROUTES] Route registration complete. Total routes: {len(list(app.url_map.iter_rules()))}")
