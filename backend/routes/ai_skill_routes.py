"""
AI Skill Routes
API endpoints for AI skill implementations
"""
from flask import Blueprint, request, jsonify
from typing import Dict

ai_skill_bp = Blueprint('ai_skill', __name__)


@ai_skill_bp.route('/api/ai-skills/<skill_name>', methods=['POST'])
def execute_skill(skill_name: str):
    """Execute an AI skill"""
    try:
        from backend.services.ai_skill_implementations import ai_skill_implementations
        
        data = request.get_json() or {}
        agent_id = data.get('agent_id', 'system')
        
        # Map skill names to methods
        skill_methods = {
            # AI Skills
            'context_understanding': ai_skill_implementations.context_understanding,
            'natural_language': ai_skill_implementations.natural_language,
            'image_processing': ai_skill_implementations.image_processing,
            'audio_processing': ai_skill_implementations.audio_processing,
            
            # System Skills
            'debugging': ai_skill_implementations.debugging,
            'monitoring': ai_skill_implementations.monitoring,
            'content_creation': ai_skill_implementations.content_creation,
            'data_analysis': ai_skill_implementations.data_analysis,
            'automation': ai_skill_implementations.automation,
            'security': ai_skill_implementations.security,
            'performance': ai_skill_implementations.performance,
            'integration': ai_skill_implementations.integration,
            'testing': ai_skill_implementations.testing,
            'deployment': ai_skill_implementations.deployment,
            'scaling': ai_skill_implementations.scaling,
            'maintenance': ai_skill_implementations.maintenance,
            
            # Content Skills
            'text_generation': ai_skill_implementations.text_generation,
            'code_generation': ai_skill_implementations.code_generation,
            'image_generation': ai_skill_implementations.image_generation,
            'video_generation': ai_skill_implementations.video_generation,
            'audio_generation': ai_skill_implementations.audio_generation,
            'template_creation': ai_skill_implementations.template_creation,
            'content_optimization': ai_skill_implementations.content_optimization,
            'content_analysis': ai_skill_implementations.content_analysis,

            # Super update / self-heal skills
            'super_upgrade_apply': ai_skill_implementations.super_upgrade_apply,
            'super_upgrade_apply_all': ai_skill_implementations.super_upgrade_apply_all,
            'self_heal': ai_skill_implementations.self_heal,
        }
        
        if skill_name not in skill_methods:
            return jsonify({
                'success': False,
                'error': f'Unknown skill: {skill_name}'
            }), 400
        
        # Execute skill
        method = skill_methods[skill_name]
        result = method(**{k: v for k, v in data.items() if k != 'agent_id'}, agent_id=agent_id)
        
        return jsonify({
            'success': True,
            'skill_name': skill_name,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_skill_bp.route('/api/ai-skills/list', methods=['GET'])
def list_skills():
    """List all available skills"""
    try:
        skills = {
            'ai_skills': [
                'context_understanding',
                'natural_language',
                'image_processing',
                'audio_processing'
            ],
            'system_skills': [
                'debugging',
                'monitoring',
                'content_creation',
                'data_analysis',
                'automation',
                'security',
                'performance',
                'integration',
                'testing',
                'deployment',
                'scaling',
                'maintenance'
            ],
            'content_skills': [
                'text_generation',
                'code_generation',
                'image_generation',
                'video_generation',
                'audio_generation',
                'template_creation',
                'content_optimization',
                'content_analysis'
            ],
            'super_update_skills': [
                'super_upgrade_apply',
                'super_upgrade_apply_all',
                'self_heal'
            ]
        }
        
        return jsonify({
            'success': True,
            'skills': skills,
            'total': sum(len(v) for v in skills.values())
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
