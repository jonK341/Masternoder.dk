"""
AI Agent Routes
API endpoints for AI Agent class
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List
from datetime import datetime

ai_agent_bp = Blueprint('ai_agent', __name__)


@ai_agent_bp.route('/api/ai-agents/create', methods=['POST'])
def create_ai_agent():
    """Create a new AI agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'skills': agent.skills,
            'limits': agent.limits
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/decision', methods=['POST'])
def make_ai_decision(agent_id):
    """Make AI decision with unified points"""
    try:
        data = request.get_json() or {}
        context = data.get('context', {})
        options = data.get('options', [])
        strategy = data.get('strategy', 'balanced')
        
        if not options:
            return jsonify({
                'success': False,
                'error': 'options are required'
            }), 400
        
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        decision = agent.make_ai_decision(context, options, strategy)
        
        return jsonify({
            'success': True,
            'decision': decision
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/generate-content', methods=['POST'])
def generate_content(agent_id):
    """Generate content using AI agent"""
    try:
        data = request.get_json() or {}
        content_type = data.get('content_type', 'text')
        parameters = data.get('parameters', {})
        agent_class = data.get('agent_class', 'ai_agent')

        normalized = str(content_type or '').strip().lower()
        if normalized in ('video', 'clip', 'clips'):
            # Route media generation through content agent so AI planning actually creates jobs.
            from backend.services.agent_content_generator import agent_content_generator
            content = agent_content_generator.generate_content(
                content_type=normalized,
                parameters=parameters,
                user_id=data.get('user_id', agent_id or 'agent_user'),
            )
        else:
            from backend.services.ai_content_generator import ai_content_generator
            content = ai_content_generator.generate_content(content_type, parameters, agent_class)
        
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/skills', methods=['GET'])
def get_agent_skills(agent_id):
    """Get agent skills with definitions"""
    try:
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        skills = agent.get_skill_definitions()
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'skills': skills
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/bridge-skills', methods=['POST'])
def bridge_skills(agent_id):
    """Create a skill bridge"""
    try:
        data = request.get_json() or {}
        skill1 = data.get('skill1')
        skill2 = data.get('skill2')
        bridge_type = data.get('bridge_type', 'complementary')
        
        if not skill1 or not skill2:
            return jsonify({
                'success': False,
                'error': 'skill1 and skill2 are required'
            }), 400
        
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        bridge = agent.create_skill_bridge(skill1, skill2, bridge_type)
        
        return jsonify({
            'success': True,
            'bridge': bridge
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/add-skill', methods=['POST'])
def add_missing_skill(agent_id):
    """Add a missing skill"""
    try:
        data = request.get_json() or {}
        skill_type = data.get('skill_type', 'ai_skills')
        skill_name = data.get('skill_name')
        initial_level = data.get('initial_level', 0)
        
        if not skill_name:
            return jsonify({
                'success': False,
                'error': 'skill_name is required'
            }), 400
        
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        result = agent.add_missing_skill(skill_type, skill_name, initial_level)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-agents/<agent_id>/unified-points', methods=['GET'])
def get_unified_points_context(agent_id):
    """Get unified points context for AI agent"""
    try:
        user_id = request.args.get('user_id', 'system')
        
        from backend.services.ai_agent_class import get_ai_agent
        
        agent = get_ai_agent(agent_id)
        points_context = agent.get_unified_points_context(user_id)
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'points_context': points_context
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/definition', methods=['GET'])
def get_system_skills_definition():
    """Get system skills definition with bridges and limits"""
    try:
        from backend.services.system_skills_definition import system_skills_definition
        
        definitions = system_skills_definition.get_skill_definitions_with_placeholders()
        
        return jsonify({
            'success': True,
            'definitions': definitions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/bridge', methods=['POST'])
def create_system_skill_bridge():
    """Create a system skill bridge"""
    try:
        data = request.get_json() or {}
        skill1 = data.get('skill1')
        skill2 = data.get('skill2')
        bridge_type = data.get('bridge_type', 'complementary')
        
        if not skill1 or not skill2:
            return jsonify({
                'success': False,
                'error': 'skill1 and skill2 are required'
            }), 400
        
        from backend.services.system_skills_definition import system_skills_definition
        
        bridge = system_skills_definition.create_skill_bridge(skill1, skill2, bridge_type)
        
        return jsonify({
            'success': True,
            'bridge': bridge
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/class-limits', methods=['GET'])
def get_class_limits():
    """Get limits for agent classes"""
    try:
        agent_class = request.args.get('agent_class')
        
        from backend.services.system_skills_definition import system_skills_definition
        
        if agent_class:
            limits = system_skills_definition.get_class_limits(agent_class)
        else:
            limits = system_skills_definition.skills['class_limits']
        
        return jsonify({
            'success': True,
            'limits': limits
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/add-missing', methods=['POST'])
def add_missing_system_skill():
    """Add a missing skill to system definition"""
    try:
        data = request.get_json() or {}
        skill_line = data.get('skill_line')
        skill_name = data.get('skill_name')
        skill_data = data.get('skill_data', {})
        
        if not skill_line or not skill_name:
            return jsonify({
                'success': False,
                'error': 'skill_line and skill_name are required'
            }), 400
        
        from backend.services.system_skills_definition import system_skills_definition
        
        skill = system_skills_definition.add_missing_skill(skill_line, skill_name, skill_data)
        
        return jsonify({
            'success': True,
            'skill': skill
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/super-upgrade/blocks', methods=['GET'])
def get_super_upgrade_blocks():
    """Get super upgrade blocks with links and linkboxes."""
    try:
        from backend.services.system_skills_definition import system_skills_definition
        blocks = system_skills_definition.get_super_upgrade_blocks()
        return jsonify({
            'success': True,
            'blocks': blocks,
            'count': len(blocks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/super-upgrade/apply', methods=['POST'])
def apply_super_upgrade():
    """Apply a +10 super upgrade and trigger self-activate/self-repair."""
    try:
        data = request.get_json() or {}
        upgrade_id = data.get('upgrade_id')
        if not upgrade_id:
            return jsonify({
                'success': False,
                'error': 'upgrade_id is required'
            }), 400

        from backend.services.system_skills_definition import system_skills_definition
        from backend.services.agent_activation_system import agent_activation_system

        result = system_skills_definition.apply_super_upgrade(upgrade_id)
        repair = agent_activation_system.self_activate_and_repair(reason=f'super_upgrade:{upgrade_id}')

        return jsonify({
            'success': result.get('success', False),
            'upgrade_result': result,
            'self_heal_result': repair,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/super-upgrade/apply-all', methods=['POST'])
def apply_all_super_upgrades():
    """Apply all super upgrades with rollback safety and trigger self-heal."""
    try:
        from backend.services.system_skills_definition import system_skills_definition
        from backend.services.agent_activation_system import agent_activation_system

        result = system_skills_definition.apply_all_super_upgrades()
        repair = agent_activation_system.self_activate_and_repair(reason='super_upgrade:apply_all')

        status_code = 200 if result.get('success') else 500
        return jsonify({
            'success': result.get('success', False),
            'upgrade_result': result,
            'self_heal_result': repair,
        }), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/system-skills/self-heal/status', methods=['GET'])
def get_self_heal_status():
    """Get self-heal policy and activation status."""
    try:
        from backend.services.system_skills_definition import system_skills_definition
        from backend.services.agent_activation_system import agent_activation_system
        return jsonify({
            'success': True,
            'policy': system_skills_definition.get_self_heal_policy(),
            'activation_status': agent_activation_system.get_status(),
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-power/enhance', methods=['POST'])
def enhance_ai_power():
    """Enhance AI power"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id', 'system')
        power_type = data.get('power_type', 'decision_power')
        amount = data.get('amount', 10.0)
        
        from backend.services.ai_power_controller import ai_power_controller
        
        result = ai_power_controller.enhance_ai_power(agent_id, power_type, amount)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_agent_bp.route('/api/ai-power/level/<agent_id>', methods=['GET'])
def get_ai_power_level(agent_id):
    """Get AI power level"""
    try:
        from backend.services.ai_power_controller import ai_power_controller
        
        power_level = ai_power_controller.get_ai_power_level(agent_id)
        
        return jsonify({
            'success': True,
            'power_level': power_level
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
