"""
Debugger Agent Analytics Routes
Agent handling and analytics for debugger site
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional
import os
import json
from datetime import datetime, timedelta

debugger_agent_analytics_bp = Blueprint('debugger_agent_analytics', __name__)

# Initialize services with error handling - import inside try blocks
agent_manager = None
agent_point_creator = None

try:
    from backend.services.agent_manager import AgentManager
    agent_manager = AgentManager()
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import AgentManager: {e}")
    agent_manager = None

try:
    from backend.services.agent_point_creator import AgentPointCreator
    agent_point_creator = AgentPointCreator()
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import AgentPointCreator: {e}")
    agent_point_creator = None


@debugger_agent_analytics_bp.route('/api/debugger/agent/analytics', methods=['GET'])
def get_agent_analytics():
    """Get comprehensive agent analytics"""
    try:
        # Get agent manager stats with fallback
        if agent_manager is None:
            agent_data = {
                'agent_id': 'agent_manager',
                'level': 1,
                'experience': 0,
                'tasks_completed': 0,
                'skills': [],
                'tasks_assigned': 0
            }
        elif hasattr(agent_manager, 'data'):
            agent_data = agent_manager.data
        else:
            agent_data = {
                'agent_id': 'agent_manager',
                'level': 1,
                'experience': 0,
                'tasks_completed': 0,
                'skills': [],
                'tasks_assigned': 0
            }
        
        # Get point creator stats with fallback
        if agent_point_creator is None:
            point_data = {
                'total_points_awarded': {'xp': 0, 'activity_points': 0},
                'value_created': 0,
                'points_by_agent': {},
                'points_by_action': {}
            }
        elif hasattr(agent_point_creator, 'data'):
            point_data = agent_point_creator.data
        else:
            point_data = {
                'total_points_awarded': {'xp': 0, 'activity_points': 0},
                'value_created': 0,
                'points_by_agent': {},
                'points_by_action': {}
            }
        
        # Calculate analytics
        analytics = {
            'agent_manager': {
                'agent_id': agent_data.get('agent_id', 'agent_manager'),
                'level': agent_data.get('level', 1),
                'experience': agent_data.get('experience', 0),
                'tasks_completed': agent_data.get('tasks_completed', 0),
                'skills': len(agent_data.get('skills', [])),
                'status': 'active'
            },
            'points': {
                'total_xp_awarded': point_data.get('total_points_awarded', {}).get('xp', 0),
                'total_activity_awarded': point_data.get('total_points_awarded', {}).get('activity_points', 0),
                'value_created': point_data.get('value_created', 0),
                'points_by_agent': point_data.get('points_by_agent', {}),
                'points_by_action': point_data.get('points_by_action', {})
            },
            'tasks': {
                'total_assigned': agent_data.get('tasks_assigned', 0),
                'total_completed': agent_data.get('tasks_completed', 0),
                'completion_rate': round((agent_data.get('tasks_completed', 0) / max(agent_data.get('tasks_assigned', 1), 1)) * 100, 2)
            },
            'performance': {
                'average_points_per_task': round(point_data.get('total_points_awarded', {}).get('xp', 0) / max(agent_data.get('tasks_completed', 1), 1), 2),
                'efficiency_score': min(100, round((agent_data.get('tasks_completed', 0) / max(agent_data.get('tasks_assigned', 1), 1)) * 100, 2))
            }
        }
        
        return jsonify({
            'success': True,
            'analytics': analytics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_analytics_bp.route('/api/debugger/agent/handling', methods=['GET'])
def get_agent_handling():
    """Get agent handling statistics"""
    try:
        # Get agent manager data with fallback
        if agent_manager is None:
            tasks_assigned = 0
            tasks_completed = 0
        elif hasattr(agent_manager, 'data'):
            tasks_assigned = agent_manager.data.get('tasks_assigned', 0)
            tasks_completed = agent_manager.data.get('tasks_completed', 0)
        else:
            tasks_assigned = 0
            tasks_completed = 0
        
        # Get recent agent activity
        handling_stats = {
            'total_agents': 1,  # agent_manager
            'active_agents': 1,
            'tasks_in_progress': max(0, tasks_assigned - tasks_completed),
            'recent_actions': [],
            'error_rate': 0,
            'success_rate': 100
        }
        
        # Get point creator data for recent actions with fallback
        if agent_point_creator is None or not hasattr(agent_point_creator, 'data'):
            points_by_action = {}
        else:
            points_by_action = agent_point_creator.data.get('points_by_action', {})
        if points_by_action:
            handling_stats['recent_actions'] = [
                {
                    'action': action,
                    'count': data.get('count', 0),
                    'total_points': data.get('total_points', 0)
                }
                for action, data in list(points_by_action.items())[:10]
            ]
        
        return jsonify({
            'success': True,
            'handling': handling_stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
