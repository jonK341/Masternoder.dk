"""
Enemy War Plan System
Strategic planning and defense system integrated with Hunters Game
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime
import json
import random

enemy_war_plan_bp = Blueprint('enemy_war_plan', __name__)

# War plan storage (in production, use database)
war_plans = {}
enemy_intelligence = {}

class EnemyWarPlan:
    """Enemy War Plan System"""
    
    def __init__(self):
        self.enemy_types = {
            'cyber_attack': {
                'name': 'Cyber Attack',
                'threat_level': 'high',
                'defense_strategy': 'firewall_upgrade',
                'xp_reward': 200,
                'description': 'Enemy attempting to breach system defenses'
            },
            'ddos_attack': {
                'name': 'DDoS Attack',
                'threat_level': 'critical',
                'defense_strategy': 'rate_limiting',
                'xp_reward': 300,
                'description': 'Distributed denial of service attack'
            },
            'data_breach': {
                'name': 'Data Breach Attempt',
                'threat_level': 'high',
                'defense_strategy': 'encryption_boost',
                'xp_reward': 250,
                'description': 'Enemy trying to steal sensitive data'
            },
            'infiltration': {
                'name': 'Infiltration',
                'threat_level': 'medium',
                'defense_strategy': 'security_audit',
                'xp_reward': 150,
                'description': 'Enemy attempting to infiltrate system'
            },
            'sabotage': {
                'name': 'Sabotage',
                'threat_level': 'critical',
                'defense_strategy': 'backup_system',
                'xp_reward': 400,
                'description': 'Enemy trying to sabotage operations'
            }
        }
        
        self.defense_tactics = {
            'firewall_upgrade': {'name': 'Firewall Upgrade', 'effectiveness': 0.8, 'cost': 100},
            'rate_limiting': {'name': 'Rate Limiting', 'effectiveness': 0.9, 'cost': 150},
            'encryption_boost': {'name': 'Encryption Boost', 'effectiveness': 0.85, 'cost': 120},
            'security_audit': {'name': 'Security Audit', 'effectiveness': 0.75, 'cost': 80},
            'backup_system': {'name': 'Backup System', 'effectiveness': 0.95, 'cost': 200}
        }
    
    def generate_enemy_plan(self, user_id: str) -> dict:
        """Generate a new enemy war plan"""
        enemy_type = random.choice(list(self.enemy_types.keys()))
        enemy_data = self.enemy_types[enemy_type]
        
        plan = {
            'plan_id': f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
            'user_id': user_id,
            'enemy_type': enemy_type,
            'enemy_name': enemy_data['name'],
            'threat_level': enemy_data['threat_level'],
            'defense_strategy': enemy_data['defense_strategy'],
            'xp_reward': enemy_data['xp_reward'],
            'description': enemy_data['description'],
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'defense_effectiveness': 0
        }
        
        war_plans[user_id] = plan
        return plan
    
    def execute_defense(self, user_id: str, tactic: str = None) -> dict:
        """Execute defense against enemy plan"""
        if user_id not in war_plans:
            return {'success': False, 'error': 'No active war plan'}
        
        plan = war_plans[user_id]
        
        if not tactic:
            tactic = plan['defense_strategy']
        
        if tactic not in self.defense_tactics:
            return {'success': False, 'error': 'Invalid defense tactic'}
        
        defense = self.defense_tactics[tactic]
        
        # Calculate defense success
        success_chance = defense['effectiveness']
        success = random.random() < success_chance
        
        if success:
            plan['status'] = 'defeated'
            plan['progress'] = 100
            plan['defense_effectiveness'] = defense['effectiveness']
            
            result = {
                'success': True,
                'enemy_defeated': True,
                'xp_earned': plan['xp_reward'],
                'defense_used': defense['name'],
                'message': f"Successfully defended against {plan['enemy_name']}!"
            }
        else:
            plan['progress'] += 20
            plan['defense_effectiveness'] = defense['effectiveness'] * 0.5
            
            result = {
                'success': True,
                'enemy_defeated': False,
                'xp_earned': int(plan['xp_reward'] * 0.3),
                'defense_used': defense['name'],
                'message': f"Partial defense against {plan['enemy_name']}. Enemy still active.",
                'progress': plan['progress']
            }
        
        plan['last_defense'] = datetime.now().isoformat()
        return result
    
    def get_intelligence(self, user_id: str) -> dict:
        """Gather intelligence on enemy plans"""
        if user_id not in war_plans:
            return {'intelligence': 'No active threats detected'}
        
        plan = war_plans[user_id]
        
        intelligence = {
            'active_threats': 1,
            'threat_level': plan['threat_level'],
            'enemy_type': plan['enemy_name'],
            'recommended_defense': plan['defense_strategy'],
            'estimated_xp_reward': plan['xp_reward'],
            'status': plan['status']
        }
        
        return intelligence

# Initialize war plan system
war_plan_system = EnemyWarPlan()

@enemy_war_plan_bp.route('/war-plan')
@enemy_war_plan_bp.route('/vidgenerator/war-plan')
def war_plan_page():
    """War Plan page"""
    return render_template('war_plan/index.html')

@enemy_war_plan_bp.route('/api/war-plan/generate', methods=['POST'])
@enemy_war_plan_bp.route('/vidgenerator/api/war-plan/generate', methods=['POST'])
def generate_war_plan():
    """Generate a new enemy war plan"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        plan = war_plan_system.generate_enemy_plan(user_id)
        
        return jsonify({
            'success': True,
            'war_plan': plan
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_bp.route('/api/war-plan/defend', methods=['POST'])
@enemy_war_plan_bp.route('/vidgenerator/api/war-plan/defend', methods=['POST'])
def execute_defense():
    """Execute defense against enemy"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        tactic = data.get('tactic')
        
        result = war_plan_system.execute_defense(user_id, tactic)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_bp.route('/api/war-plan/intelligence/<user_id>', methods=['GET'])
@enemy_war_plan_bp.route('/vidgenerator/api/war-plan/intelligence/<user_id>', methods=['GET'])
def get_intelligence(user_id):
    """Get intelligence on enemy plans"""
    try:
        intelligence = war_plan_system.get_intelligence(user_id)
        
        return jsonify({
            'success': True,
            'intelligence': intelligence
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_bp.route('/api/war-plan/status/<user_id>', methods=['GET'])
@enemy_war_plan_bp.route('/vidgenerator/api/war-plan/status/<user_id>', methods=['GET'])
def get_war_plan_status(user_id):
    """Get current war plan status"""
    try:
        if user_id not in war_plans:
            return jsonify({
                'success': True,
                'active': False,
                'message': 'No active war plan'
            })
        
        plan = war_plans[user_id]
        
        return jsonify({
            'success': True,
            'active': plan['status'] == 'active',
            'war_plan': plan
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

