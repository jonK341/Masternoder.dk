"""
Tech Debug Routes
Provides debugging endpoints for tech structure analysis
"""
from flask import Blueprint, jsonify, current_app
from backend.utils.debug_tech_structure import (
    TechStructureAnalyzer,
    RouteDebugger,
    DebugLogger,
    create_debug_blueprint
)

# Create the debug blueprint
tech_debug_bp = create_debug_blueprint()

# Additional custom routes
@tech_debug_bp.route('/api/debug/tech-structure/validate')
def validate_tech_structure():
    """Validate tech structure"""
    analyzer = TechStructureAnalyzer(current_app)
    validation = analyzer.tech_structure.validate_structure()
    return jsonify(validation)

@tech_debug_bp.route('/api/debug/tech-structure/dependencies')
def get_dependencies():
    """Get dependency tree"""
    analyzer = TechStructureAnalyzer(current_app)
    dependencies = analyzer.tech_structure.get_dependency_tree()
    return jsonify({"dependencies": dependencies})

@tech_debug_bp.route('/api/debug/route/<path:route_path>')
def check_route(route_path):
    """Check if a specific route exists"""
    debugger = RouteDebugger(current_app)
    route = debugger.find_route(route_path)
    if route:
        return jsonify({"found": True, "route": route})
    else:
        return jsonify({"found": False, "route_path": route_path}), 404

@tech_debug_bp.route('/api/debug/blueprint/<blueprint_name>')
def check_blueprint(blueprint_name):
    """Check blueprint registration"""
    debugger = RouteDebugger(current_app)
    result = debugger.check_blueprint_registration(blueprint_name)
    return jsonify(result)

@tech_debug_bp.route('/api/debug/victory-routes')
def check_victory_routes():
    """Check all victory-related routes"""
    debugger = RouteDebugger(current_app)
    all_routes = debugger.get_all_routes()
    
    victory_routes = []
    for route in all_routes:
        path = route.get("path", "")
        if "victory" in path.lower() or "trophy" in path.lower() or "emblem" in path.lower():
            victory_routes.append(route)
    
    return jsonify({
        "total_victory_routes": len(victory_routes),
        "routes": victory_routes
    })

@tech_debug_bp.route('/api/debug/points-routes')
def check_points_routes():
    """Check all points-related routes"""
    debugger = RouteDebugger(current_app)
    all_routes = debugger.get_all_routes()
    
    points_routes = []
    for route in all_routes:
        path = route.get("path", "")
        if "points" in path.lower():
            points_routes.append(route)
    
    return jsonify({
        "total_points_routes": len(points_routes),
        "routes": points_routes
    })

@tech_debug_bp.route('/api/debug/tech-tree-routes')
def check_tech_tree_routes():
    """Check all tech tree routes"""
    debugger = RouteDebugger(current_app)
    all_routes = debugger.get_all_routes()
    
    tech_tree_routes = []
    for route in all_routes:
        path = route.get("path", "")
        if "tech-tree" in path.lower() or "tech_tree" in path.lower():
            tech_tree_routes.append(route)
    
    return jsonify({
        "total_tech_tree_routes": len(tech_tree_routes),
        "routes": tech_tree_routes
    })

