"""
Game Sync API - Client-Server Integration
Handles game mechanics sync, peer downloads, and state management
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from src.services.game_mechanics.sync_engine import SyncEngine

game_sync_api_bp = Blueprint('game_sync_api', __name__)

sync_engine = SyncEngine()

@game_sync_api_bp.route('/api/game/sync', methods=['POST'])
@game_sync_api_bp.route('/vidgenerator/api/game/sync', methods=['POST'])
def sync_game_state():
    """Sync game state between client and server"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        client_state = data.get('client_state', {})
        server_state = data.get('server_state', {})
        
        result = sync_engine.sync_game_state(user_id, client_state, server_state)
        
        return jsonify({
            'success': True,
            'sync_result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@game_sync_api_bp.route('/api/game/peers/register', methods=['POST'])
@game_sync_api_bp.route('/vidgenerator/api/game/peers/register', methods=['POST'])
def register_peer():
    """Register peer for download"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        peer_info = {
            'ip': data.get('ip'),
            'port': data.get('port'),
            'capabilities': data.get('capabilities', []),
            'bandwidth': data.get('bandwidth', 0)
        }
        
        result = sync_engine.register_peer(user_id, peer_info)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@game_sync_api_bp.route('/api/game/peers/download/<resource_id>', methods=['GET'])
@game_sync_api_bp.route('/vidgenerator/api/game/peers/download/<resource_id>', methods=['GET'])
def get_download_peers(resource_id):
    """Get peers for download (double or triple)"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        count = int(request.args.get('count', 3))  # Default to triple
        
        result = sync_engine.get_download_peers(resource_id, user_id, count)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@game_sync_api_bp.route('/api/game/peers/add', methods=['POST'])
@game_sync_api_bp.route('/vidgenerator/api/game/peers/add', methods=['POST'])
def add_download_peer():
    """Add peer to download pool"""
    try:
        data = request.get_json() or {}
        resource_id = data.get('resource_id')
        peer_info = {
            'user_id': data.get('user_id', 'anonymous'),
            'ip': data.get('ip'),
            'port': data.get('port'),
            'url': data.get('url'),
            'capabilities': data.get('capabilities', [])
        }
        
        result = sync_engine.add_download_peer(resource_id, peer_info)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

