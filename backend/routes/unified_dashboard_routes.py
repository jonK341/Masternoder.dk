"""
Unified Dashboard Routes
API for the unified dashboard
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
unified_dashboard_bp = Blueprint('unified_dashboard', __name__)


# Note: Middleware strips /vidgenerator, so routes should be /unified_dashboard (not /vidgenerator/unified_dashboard)
@unified_dashboard_bp.route('/unified-dashboard', methods=['GET'], strict_slashes=False)
@unified_dashboard_bp.route('/unified-dashboard/', methods=['GET'], strict_slashes=False)
@unified_dashboard_bp.route('/unified-dashboard/index.html', methods=['GET'], strict_slashes=False)
@unified_dashboard_bp.route('/unified_dashboard', methods=['GET'], strict_slashes=False)
@unified_dashboard_bp.route('/unified_dashboard/', methods=['GET'], strict_slashes=False)
@unified_dashboard_bp.route('/unified_dashboard/index.html', methods=['GET'], strict_slashes=False)
def unified_dashboard_page():
    """Serve the unified dashboard page"""
    from flask import Response
    import os
    
    # Try multiple possible paths (both server and local)
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    possible_paths = [
        '/var/www/html/vidgenerator/vidgenerator/unified_dashboard/index.html',
        '/var/www/html/vidgenerator/unified_dashboard/index.html',
        os.path.join(base_path, 'vidgenerator', 'unified_dashboard', 'index.html'),
        os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'unified_dashboard', 'index.html'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'vidgenerator', 'unified_dashboard', 'index.html'),
        os.path.join('/var/www/html', 'vidgenerator', 'unified_dashboard', 'index.html'),
    ]
    
    for dashboard_path in possible_paths:
        try:
            if os.path.exists(dashboard_path):
                with open(dashboard_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        except Exception as e:
            continue
    
    # Fallback: Return a basic HTML page instead of 404
    fallback_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Unified Dashboard - MasterNoder</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; padding: 40px; text-align: center; }
        a { color: #00ff88; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Unified Dashboard</h1>
    <p>Loading dashboard...</p>
    <p><a href="/vidgenerator/">← Back to Home</a></p>
    <script>
        // Try to load dashboard data
        fetch('/vidgenerator/api/unified-dashboard/data?user_id=default_user')
            .then(r => r.json())
            .then(data => console.log('Dashboard data:', data))
            .catch(e => console.error('Error loading dashboard:', e));
    </script>
</body>
</html>"""
    response = Response(fallback_html, mimetype='text/html; charset=utf-8')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    return response


@unified_dashboard_bp.route('/api/tech-tree', methods=['GET'])
@unified_dashboard_bp.route('/vidgenerator/api/tech-tree', methods=['GET'])
def get_tech_tree():
    """Get tech tree data for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        try:
            from backend.services.enhanced_tech_tree_with_quests import enhanced_tech_tree
            if enhanced_tech_tree:
                try:
                    tech_tree_data = enhanced_tech_tree.get_user_tech_tree(user_id)
                    return jsonify({
                        'success': True,
                        'tech_tree': tech_tree_data if isinstance(tech_tree_data, dict) else {}
                    }), 200
                except AttributeError:
                    # Try alternative method
                    tech_tree_data = enhanced_tech_tree.get_tech_tree(user_id) if hasattr(enhanced_tech_tree, 'get_tech_tree') else {}
                    return jsonify({
                        'success': True,
                        'tech_tree': tech_tree_data if isinstance(tech_tree_data, dict) else {}
                    }), 200
        except ImportError:
            pass
        
        # Fallback to empty tech tree
        return jsonify({
            'success': True,
            'tech_tree': {
                'technologies': {},
                'total_researched': 0,
                'total_available': 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting tech tree: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'tech_tree': {
                'technologies': {},
                'total_researched': 0,
                'total_available': 0
            }
        }), 200


@unified_dashboard_bp.route('/api/tech-tree/knowledge', methods=['GET'])
@unified_dashboard_bp.route('/vidgenerator/api/tech-tree/knowledge', methods=['GET'])
def get_knowledge():
    """Get knowledge tree data - fallback route if tech_tree blueprint fails"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try to get from tech_tree_system
        try:
            from backend.services.tech_tree_system import tech_tree_system
            if tech_tree_system:
                try:
                    result = tech_tree_system.get_knowledge(user_id)
                    if isinstance(result, dict) and 'success' in result:
                        # Ensure knowledge key exists
                        if 'knowledge' not in result:
                            result['knowledge'] = result if isinstance(result, dict) else {}
                        # Convert knowledge_nodes to knowledge if needed
                        if 'knowledge_nodes' in result and 'knowledge' not in result:
                            result['knowledge'] = {'nodes': result.get('knowledge_nodes', [])}
                        return jsonify(result), 200
                except AttributeError:
                    pass
        except ImportError:
            pass
        
        # Try enhanced_tech_tree
        try:
            from backend.services.enhanced_tech_tree_with_quests import enhanced_tech_tree
            if enhanced_tech_tree:
                try:
                    result = enhanced_tech_tree.get_knowledge(user_id)
                    if isinstance(result, dict):
                        return jsonify({
                            'success': True,
                            'knowledge': result if 'knowledge' in result else {'nodes': result.get('knowledge_nodes', [])}
                        }), 200
                except AttributeError:
                    pass
        except ImportError:
            pass
        
        # Fallback to empty data
        return jsonify({
            'success': True,
            'knowledge': {
                'nodes': [],
                'total_unlocked': 0,
                'total_available': 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error getting knowledge: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'knowledge': {
                'nodes': [],
                'total_unlocked': 0,
                'total_available': 0
            }
        }), 200


@unified_dashboard_bp.route('/api/unified-dashboard/data', methods=['GET'])
@unified_dashboard_bp.route('/vidgenerator/api/unified-dashboard/data', methods=['GET'])
def get_unified_dashboard_data():
    """Get all unified dashboard data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Import all services with error handling
        try:
            from backend.services.unified_point_system_json_storage import unified_point_json_storage
            unified_point_system = unified_point_json_storage  # Alias for compatibility
        except ImportError:
            logger.warning("unified_point_json_storage not available")
            unified_point_system = None
        
        try:
            from backend.services.ultra_resource_controller import ultra_resource_controller
        except ImportError:
            logger.warning("ultra_resource_controller not available")
            ultra_resource_controller = None
        
        try:
            from backend.services.monetization_cash_generator import monetization_cash_generator
        except ImportError:
            logger.warning("monetization_cash_generator not available")
            monetization_cash_generator = None
        
        try:
            from backend.services.enhanced_tech_tree_with_quests import enhanced_tech_tree_quests
            enhanced_tech_tree = enhanced_tech_tree_quests  # Alias for compatibility
        except ImportError:
            logger.warning("enhanced_tech_tree_quests not available")
            enhanced_tech_tree = None
        
        try:
            from backend.services.unified_game_mechanics_constructor import unified_game_mechanics
        except ImportError:
            logger.warning("unified_game_mechanics not available")
            unified_game_mechanics = None
        
        # Get all data with error handling
        if unified_point_system:
            try:
                # unified_point_json_storage uses get_all_points, not get_points
                points_data = unified_point_system.get_all_points(user_id)
                # Ensure it's in the expected format
                if not isinstance(points_data, dict):
                    points_data = {'points': points_data if points_data else {}}
                elif 'points' not in points_data:
                    points_data = {'points': points_data}
            except Exception as e:
                logger.warning(f"Error getting points data: {e}")
                points_data = {'points': {}}
        else:
            points_data = {'points': {}}
        
        if ultra_resource_controller:
            try:
                # ultra_resource_controller uses get_energy_status, not get_energy
                energy_status = ultra_resource_controller.get_energy_status(user_id)
                # Convert to expected format
                if isinstance(energy_status, dict) and 'energy' in energy_status:
                    energy_data = energy_status
                else:
                    energy_data = {'energy': energy_status if isinstance(energy_status, dict) else {}}
            except Exception as e:
                logger.warning(f"Error getting energy data: {e}")
                energy_data = {'energy': {}}
        else:
            energy_data = {'energy': {}}
        
        if monetization_cash_generator:
            try:
                cash_data = monetization_cash_generator.get_user_cash(user_id)
            except Exception as e:
                logger.warning(f"Error getting cash data: {e}")
                cash_data = {'total_cash': 0, 'cash_sources': {}}
        else:
            cash_data = {'total_cash': 0, 'cash_sources': {}}
        
        if monetization_cash_generator:
            try:
                # Try without limit parameter first (method may not accept it)
                try:
                    top50_data = monetization_cash_generator.get_top_50()
                except (TypeError, AttributeError) as e:
                    # If method doesn't exist or has different signature, return empty
                    logger.warning(f"Error calling get_top_50: {e}")
                    top50_data = []
                # Ensure it's a dict with success key
                if not isinstance(top50_data, dict):
                    top50_data = {'success': True, 'top50': top50_data if isinstance(top50_data, list) else []}
                if 'success' not in top50_data:
                    top50_data['success'] = True
                # Limit to 6 if it's a list
                if isinstance(top50_data.get('top50'), list) and len(top50_data['top50']) > 6:
                    top50_data['top50'] = top50_data['top50'][:6]
            except Exception as e:
                logger.warning(f"Error getting top50 data: {e}")
                top50_data = {'success': False, 'top50': []}
        else:
            top50_data = {'success': False, 'top50': []}
        
        if unified_game_mechanics:
            try:
                progress_data = unified_game_mechanics.get_user_progress(user_id)
            except Exception as e:
                logger.warning(f"Error getting progress data: {e}")
                progress_data = {}
        else:
            progress_data = {}
        
        # Calculate totals
        total_points = sum(v for v in points_data.get('points', {}).values() if isinstance(v, (int, float)))
        total_energy = sum(v for k, v in energy_data.get('energy', {}).items() 
                          if k != 'last_update' and isinstance(v, (int, float)))
        
        # Find user rank
        user_rank = None
        if top50_data.get('success') and top50_data.get('top50'):
            for idx, user in enumerate(top50_data['top50']):
                if user.get('user_id') == user_id:
                    user_rank = idx + 1
                    break
        
        # Handle top50_data structure - it might have 'top50' or 'top_50' key
        top50_list = []
        if top50_data.get('success'):
            top50_list = top50_data.get('top50', top50_data.get('top_50', []))
        elif isinstance(top50_data, list):
            top50_list = top50_data
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'points': {
                'data': points_data.get('points', {}),
                'total': total_points
            },
            'energy': {
                'data': energy_data.get('energy', {}),
                'total': total_energy,
                'percentage': min(100, (total_energy / 400) * 100) if total_energy > 0 else 0  # 4 types * 100 max
            },
            'cash': {
                'total': cash_data.get('total_cash', 0),
                'sources': cash_data.get('cash_sources', {})
            },
            'top50': {
                'rank': user_rank,
                'top6': top50_list[:6] if isinstance(top50_list, list) else []
            },
            'progress': {
                'game_mechanics': progress_data,
                'completion': progress_data.get('completion_percentage', 0) if isinstance(progress_data, dict) else 0
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in unified dashboard data endpoint: {e}", exc_info=True)
        # Return 200 with empty data instead of 500 to prevent frontend crashes
        return jsonify({
            'success': False,
            'error': str(e),
            'user_id': request.args.get('user_id', 'default_user'),
            'points': {'data': {}, 'total': 0},
            'energy': {'data': {}, 'total': 0, 'percentage': 0},
            'cash': {'total': 0, 'sources': {}},
            'top50': {'rank': None, 'top6': []},
            'progress': {'game_mechanics': {}, 'completion': 0}
        }), 200

