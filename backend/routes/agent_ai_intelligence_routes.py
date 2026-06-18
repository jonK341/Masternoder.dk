"""
Agent AI Intelligence Routes
API endpoints for agent AI intelligence capabilities
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
from backend.services.agent_ai_intelligence import agent_ai_intelligence

agent_ai_intelligence_bp = Blueprint('agent_ai_intelligence', __name__)

# ========== DECISION MAKING ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/decision', methods=['POST'])
def make_decision():
    """Make an intelligent decision"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        context = data.get('context', {})
        options = data.get('options', [])
        strategy = data.get('strategy', 'balanced')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        if not options:
            return jsonify({
                'success': False,
                'error': 'options required'
            }), 400
        
        decision = agent_ai_intelligence.make_decision(agent_id, context, options, strategy)
        return jsonify({
            'success': True,
            'decision': decision
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/llm-insight', methods=['POST'])
def llm_insight():
    """
    LLM-backed tactical insight for an agent (defaults to free-tier provider routing).
    Body: agent_id (required), topic (required), context (optional dict),
    task_type (optional: speed|code|reason|context|free|default).
    """
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        topic = (data.get('topic') or '').strip()
        context = data.get('context') if isinstance(data.get('context'), dict) else {}
        task_type = data.get('task_type')

        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id required'}), 400
        if not topic:
            return jsonify({'success': False, 'error': 'topic required'}), 400

        result = agent_ai_intelligence.llm_insight(
            agent_id=agent_id,
            topic=topic,
            context=context,
            task_type=task_type,
        )
        reward = None
        uid = str(data.get("user_id") or "").strip()
        if result.get("success") and uid and uid not in ("default_user", "anonymous"):
            try:
                from backend.services.agent_crypto_rewards_service import award_agent_action

                ref = f"insight:{agent_id}:{hash(topic) & 0xFFFFFFFF:08x}:{datetime.now().strftime('%Y-%m-%d')}"
                reward = award_agent_action(
                    uid,
                    "llm_insight",
                    reference=ref,
                    metadata={"agent_id": agent_id, "topic": topic},
                    success=True,
                )
            except Exception:
                pass
        if reward is not None:
            result = {**result, "reward": reward}
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== LEARNING ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/learn', methods=['POST'])
def learn_from_experience():
    """Learn from experience"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        experience = data.get('experience', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_ai_intelligence.learn_from_experience(agent_id, experience)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== PREDICTION ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/predict', methods=['POST'])
def predict_outcome():
    """Predict outcome of an action"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        action = data.get('action', {})
        context = data.get('context', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        prediction = agent_ai_intelligence.predict_outcome(agent_id, action, context)
        return jsonify({
            'success': True,
            'prediction': prediction
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== PATTERN RECOGNITION ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/pattern', methods=['POST'])
def recognize_pattern():
    """Recognize patterns in data"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        pattern_data = data.get('data', [])
        pattern_type = data.get('pattern_type', 'sequence')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        if not pattern_data:
            return jsonify({
                'success': False,
                'error': 'data required'
            }), 400
        
        result = agent_ai_intelligence.recognize_pattern(agent_id, pattern_data, pattern_type)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== STRATEGY ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/strategy', methods=['POST'])
def develop_strategy():
    """Develop an intelligent strategy"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        goal = data.get('goal')
        constraints = data.get('constraints', {})
        
        if not agent_id or not goal:
            return jsonify({
                'success': False,
                'error': 'agent_id and goal required'
            }), 400
        
        strategy = agent_ai_intelligence.develop_strategy(agent_id, goal, constraints)
        return jsonify({
            'success': True,
            'strategy': strategy
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== RISK ASSESSMENT ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/risk', methods=['POST'])
def assess_risk():
    """Assess risk for a scenario"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        scenario = data.get('scenario', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        assessment = agent_ai_intelligence.assess_risk(agent_id, scenario)
        return jsonify({
            'success': True,
            'assessment': assessment
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== OPTIMIZATION ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/optimize', methods=['POST'])
def optimize_decision():
    """Optimize a set of decisions"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        decisions = data.get('decisions', [])
        constraints = data.get('constraints', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        if not decisions:
            return jsonify({
                'success': False,
                'error': 'decisions required'
            }), 400
        
        result = agent_ai_intelligence.optimize_decision(agent_id, decisions, constraints)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== CONTEXT UNDERSTANDING ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/context', methods=['POST'])
def understand_context():
    """Understand and analyze context"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        context = data.get('context', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        understanding = agent_ai_intelligence.understand_context(agent_id, context)
        return jsonify({
            'success': True,
            'understanding': understanding
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== STATISTICS ENDPOINTS ==========

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/agent/<agent_id>', methods=['GET'])
def get_agent_intelligence(agent_id):
    """Get intelligence data for an agent"""
    try:
        intelligence = agent_ai_intelligence.get_agent_intelligence(agent_id)
        return jsonify({
            'success': True,
            'intelligence': intelligence
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_ai_intelligence_bp.route('/api/agent/ai-intelligence/all', methods=['GET'])
def get_all_intelligence():
    """Get all intelligence data"""
    try:
        intelligence = agent_ai_intelligence.get_all_intelligence()
        return jsonify({
            'success': True,
            'intelligence': intelligence
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
