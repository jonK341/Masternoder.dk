"""
Parent Controls Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.parent_controls_system import parent_controls_system
import traceback

parent_controls_bp = Blueprint('parent_controls', __name__, url_prefix='/api/parent-controls')


@parent_controls_bp.route('/parent-group/create', methods=['POST'])
def create_parent_group():
    """Create a parent group"""
    try:
        data = request.get_json() or {}
        parent_user_id = data.get('parent_user_id', 'anonymous')
        group_name = data.get('group_name', '')
        description = data.get('description', '')
        agency_ids = data.get('agency_ids', [])
        
        result = parent_controls_system.create_parent_group(
            parent_user_id, group_name, description, agency_ids
        )
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in create_parent_group: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/child/add', methods=['POST'])
def add_child_user():
    """Add child user to parent control"""
    try:
        data = request.get_json() or {}
        parent_user_id = data.get('parent_user_id', 'anonymous')
        child_user_id = data.get('child_user_id', '')
        
        result = parent_controls_system.add_child_user(parent_user_id, child_user_id)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in add_child_user: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/controls/set', methods=['POST'])
def set_parent_controls():
    """Set parent control settings"""
    try:
        data = request.get_json() or {}
        parent_user_id = data.get('parent_user_id', 'anonymous')
        controls = data.get('controls', {})
        
        result = parent_controls_system.set_parent_controls(parent_user_id, controls)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in set_parent_controls: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/controls/<parent_user_id>', methods=['GET'])
def get_parent_controls(parent_user_id: str):
    """Get parent control settings"""
    try:
        result = parent_controls_system.get_parent_controls(parent_user_id)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in get_parent_controls: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/approval/check', methods=['POST'])
def check_parent_approval():
    """Check if parent approval is needed"""
    try:
        data = request.get_json() or {}
        child_user_id = data.get('child_user_id', 'anonymous')
        action_type = data.get('action_type', '')
        action_data = data.get('action_data', {})
        
        result = parent_controls_system.check_parent_approval(
            child_user_id, action_type, action_data
        )
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in check_parent_approval: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/approval/<parent_user_id>/<request_id>', methods=['POST'])
def approve_request(parent_user_id: str, request_id: str):
    """Approve or deny a request"""
    try:
        data = request.get_json() or {}
        approved = data.get('approved', False)
        
        result = parent_controls_system.approve_request(parent_user_id, request_id, approved)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in approve_request: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/agency/link', methods=['POST'])
def link_agency():
    """Link agency to parent group"""
    try:
        data = request.get_json() or {}
        agency_id = data.get('agency_id', '')
        parent_group_id = data.get('parent_group_id', '')
        
        result = parent_controls_system.link_agency_to_parent_group(agency_id, parent_group_id)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in link_agency: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/agency/<agency_id>/parent-group', methods=['GET'])
def get_agency_parent_group(agency_id: str):
    """Get parent group for an agency"""
    try:
        result = parent_controls_system.get_agency_parent_group(agency_id)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in get_agency_parent_group: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@parent_controls_bp.route('/parent-groups', methods=['GET'])
def get_all_parent_groups():
    """Get all parent groups"""
    try:
        parent_user_id = request.args.get('parent_user_id')
        result = parent_controls_system.get_all_parent_groups(parent_user_id)
        return jsonify(result)
    except Exception as e:
        print(f"[ParentControlsRoutes] Error in get_all_parent_groups: {e}", flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

