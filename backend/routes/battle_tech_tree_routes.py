"""
Battle Tech Tree Routes - All technologies integrated
"""
from flask import Blueprint, request, jsonify
from backend.services.tech_tree_system import tech_tree_system
from backend.services.advanced_battle_tech import advanced_battle_tech
import sys

battle_tech_tree_bp = Blueprint('battle_tech_tree', __name__)

@battle_tech_tree_bp.route('/api/battle/tech-tree/all', methods=['GET'])
@battle_tech_tree_bp.route('/vidgenerator/api/battle/tech-tree/all', methods=['GET'])
def get_all_tech_tree():
    """Get complete tech tree with all technologies"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Get base tech tree
        tech_tree = {}
        try:
            tech_tree = tech_tree_system.get_tech_tree(user_id)
            if not isinstance(tech_tree, dict):
                tech_tree = {'technologies': {}}
        except Exception as e:
            print(f"[BattleTechTree] Error getting base tech tree: {e}", file=sys.stderr, flush=True)
            tech_tree = {'technologies': {}}
        
        # Get advanced battle tech
        advanced_tech = {}
        try:
            available = advanced_battle_tech.get_available_tech(user_id)
            if available and isinstance(available, dict) and available.get('success'):
                advanced_tech = available.get('tech', {})
        except Exception as e:
            print(f"[BattleTechTree] Error getting advanced tech: {e}", file=sys.stderr, flush=True)
        
        # Get galactic tech
        galactic_tech = {}
        try:
            from backend.services.tech_tree_galactic_upgrade import tech_tree_galactic_upgrade
            galactic = tech_tree_galactic_upgrade.get_galactic_tech_tree(user_id)
            if galactic and isinstance(galactic, dict) and galactic.get('success'):
                galactic_tech = galactic.get('technologies', {})
        except Exception as e:
            print(f"[BattleTechTree] Error getting galactic tech: {e}", file=sys.stderr, flush=True)
        
        base_tech_count = len(tech_tree.get('technologies', {})) if isinstance(tech_tree.get('technologies'), dict) else 0
        
        return jsonify({
            'success': True,
            'tech_tree': tech_tree,
            'advanced_tech': advanced_tech,
            'galactic_tech': galactic_tech,
            'total_technologies': base_tech_count + len(advanced_tech) + len(galactic_tech)
        }), 200
    except Exception as e:
        print(f"[BattleTechTree] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@battle_tech_tree_bp.route('/api/battle/tech-tree/research', methods=['POST'])
@battle_tech_tree_bp.route('/vidgenerator/api/battle/tech-tree/research', methods=['POST'])
def research_tech():
    """Research a technology"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        tech_id = data.get('tech_id', '')
        
        if not tech_id:
            return jsonify({'success': False, 'error': 'tech_id required'}), 400
        
        result = tech_tree_system.research_technology(user_id, tech_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

