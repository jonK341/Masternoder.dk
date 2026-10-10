"""
Manager Artifacts Routes
API endpoints for manager artifacts system
"""
from flask import Blueprint, request, jsonify
from backend.services.manager_artifacts_system import manager_artifacts_system
import sys
import traceback

manager_artifacts_bp = Blueprint('manager_artifacts', __name__)

@manager_artifacts_bp.route('/api/manager-artifacts/all', methods=['GET'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/all', methods=['GET'])
def get_all_manager_artifacts():
    """Get all available manager artifacts"""
    try:
        result = manager_artifacts_system.get_all_artifacts()
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error getting all artifacts: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@manager_artifacts_bp.route('/api/manager-artifacts/user-agent', methods=['GET'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/user-agent', methods=['GET'])
def get_user_agent_artifacts():
    """Get artifacts collected by a specific agent"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        agent_id = request.args.get('agent_id')
        
        if not agent_id:
            return jsonify({'success': False, 'message': 'agent_id is required'}), 400
        
        result = manager_artifacts_system.get_user_agent_artifacts(user_id, agent_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error getting user agent artifacts: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@manager_artifacts_bp.route('/api/manager-artifacts/collect', methods=['POST'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/collect', methods=['POST'])
def collect_manager_artifact():
    """Collect a manager artifact for an agent"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        artifact_id = data.get('artifact_id')
        
        if not all([agent_id, artifact_id]):
            return jsonify({'success': False, 'message': 'agent_id and artifact_id are required'}), 400
        
        result = manager_artifacts_system.collect_artifact(user_id, agent_id, artifact_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error collecting artifact: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@manager_artifacts_bp.route('/api/manager-artifacts/activate', methods=['POST'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/activate', methods=['POST'])
def activate_manager_artifact():
    """Activate an artifact's effects"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        artifact_id = data.get('artifact_id')
        
        if not all([agent_id, artifact_id]):
            return jsonify({'success': False, 'message': 'agent_id and artifact_id are required'}), 400
        
        result = manager_artifacts_system.activate_artifact(user_id, agent_id, artifact_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error activating artifact: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@manager_artifacts_bp.route('/api/manager-artifacts/deactivate', methods=['POST'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/deactivate', methods=['POST'])
def deactivate_manager_artifact():
    """Deactivate an artifact's effects"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        artifact_id = data.get('artifact_id')
        
        if not all([agent_id, artifact_id]):
            return jsonify({'success': False, 'message': 'agent_id and artifact_id are required'}), 400
        
        result = manager_artifacts_system.deactivate_artifact(user_id, agent_id, artifact_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error deactivating artifact: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@manager_artifacts_bp.route('/api/manager-artifacts/active-effects', methods=['GET'])
@manager_artifacts_bp.route('/vidgenerator/api/manager-artifacts/active-effects', methods=['GET'])
def get_active_effects():
    """Get all active artifact effects for an agent"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        agent_id = request.args.get('agent_id')
        
        if not agent_id:
            return jsonify({'success': False, 'message': 'agent_id is required'}), 400
        
        result = manager_artifacts_system.get_active_effects(user_id, agent_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[ManagerArtifactsRoutes] Error getting active effects: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
