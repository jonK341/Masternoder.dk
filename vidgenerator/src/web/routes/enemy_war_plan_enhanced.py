"""
Enhanced Enemy War Plan System with Defense Mechanisms
Includes psychological warfare, hacks, scams, and enemy websites
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime
import json
import random

from src.services.defense_mechanisms.defense_engine import (
    DefenseMechanismsEngine,
    DefenseMechanism,
    SkillType,
    EnemyType,
    HackType
)

enemy_war_plan_enhanced_bp = Blueprint('enemy_war_plan_enhanced', __name__)

# War plan storage (in production, use database)
war_plans = {}
enemy_intelligence = {}
defense_engine = DefenseMechanismsEngine()

class EnhancedEnemyWarPlan:
    """Enhanced Enemy War Plan System with defense mechanisms"""
    
    def __init__(self):
        # Get enemy websites from defense engine
        self.enemy_websites = defense_engine.get_enemy_websites()
        
        # Enhanced enemy types with defense mechanisms
        self.enemy_types = {
            'cyber_attack': {
                'name': 'Cyber Attack',
                'threat_level': 'high',
                'defense_strategy': 'firewall_upgrade',
                'xp_reward': 200,
                'description': 'Enemy attempting to breach system defenses',
                'enemy_type': EnemyType.HACKER,
                'recommended_defense': DefenseMechanism.INTELLECTUALIZATION
            },
            'ddos_attack': {
                'name': 'DDoS Attack',
                'threat_level': 'critical',
                'defense_strategy': 'rate_limiting',
                'xp_reward': 300,
                'description': 'Distributed denial of service attack',
                'enemy_type': EnemyType.HACKER,
                'recommended_defense': DefenseMechanism.SUBLIMATION
            },
            'data_breach': {
                'name': 'Data Breach Attempt',
                'threat_level': 'high',
                'defense_strategy': 'encryption_boost',
                'xp_reward': 250,
                'description': 'Enemy trying to steal sensitive data',
                'enemy_type': EnemyType.CORPORATE,
                'recommended_defense': DefenseMechanism.IDENTIFICATION
            },
            'infiltration': {
                'name': 'Infiltration',
                'threat_level': 'medium',
                'defense_strategy': 'security_audit',
                'xp_reward': 150,
                'description': 'Enemy attempting to infiltrate system',
                'enemy_type': EnemyType.SCAMMER,
                'recommended_defense': DefenseMechanism.PROJECTION
            },
            'sabotage': {
                'name': 'Sabotage',
                'threat_level': 'critical',
                'defense_strategy': 'backup_system',
                'xp_reward': 400,
                'description': 'Enemy trying to sabotage operations',
                'enemy_type': EnemyType.GOVERNMENT,
                'recommended_defense': DefenseMechanism.REACTION_FORMATION
            },
            'website_competitor': {
                'name': 'Competitor Website Attack',
                'threat_level': 'medium',
                'defense_strategy': 'market_analysis',
                'xp_reward': 180,
                'description': 'Competitor website attempting to outcompete',
                'enemy_type': EnemyType.COMPETITOR,
                'recommended_defense': DefenseMechanism.COMPENSATION
            }
        }
        
        self.defense_tactics = {
            'firewall_upgrade': {'name': 'Firewall Upgrade', 'effectiveness': 0.8, 'cost': 100},
            'rate_limiting': {'name': 'Rate Limiting', 'effectiveness': 0.9, 'cost': 150},
            'encryption_boost': {'name': 'Encryption Boost', 'effectiveness': 0.85, 'cost': 120},
            'security_audit': {'name': 'Security Audit', 'effectiveness': 0.75, 'cost': 80},
            'backup_system': {'name': 'Backup System', 'effectiveness': 0.95, 'cost': 200},
            'market_analysis': {'name': 'Market Analysis', 'effectiveness': 0.7, 'cost': 90}
        }
    
    def generate_enhanced_war_plan(self, user_id: str, enemy_website_id: str = None) -> dict:
        """Generate enhanced war plan with defense mechanisms"""
        if enemy_website_id:
            # Use specific enemy website
            enemy_website = next((e for e in self.enemy_websites if e['id'] == enemy_website_id), None)
            if enemy_website:
                enemy_type_enum = EnemyType(enemy_website['type'])
                enemy_name = enemy_website['name']
            else:
                enemy_type_enum = EnemyType.COMPETITOR
                enemy_name = 'Unknown Enemy'
        else:
            # Random enemy type
            enemy_type_key = random.choice(list(self.enemy_types.keys()))
            enemy_data = self.enemy_types[enemy_type_key]
            enemy_type_enum = enemy_data['enemy_type']
            enemy_name = enemy_data['name']
            enemy_type_key = enemy_type_key
        
        plan = {
            'plan_id': f"plan_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
            'user_id': user_id,
            'enemy_type': enemy_type_enum.value,
            'enemy_name': enemy_name,
            'enemy_website_id': enemy_website_id,
            'threat_level': self.enemy_types.get(enemy_type_key, {}).get('threat_level', 'medium'),
            'defense_strategy': self.enemy_types.get(enemy_type_key, {}).get('defense_strategy', 'security_audit'),
            'recommended_defense_mechanism': self.enemy_types.get(enemy_type_key, {}).get('recommended_defense', DefenseMechanism.SUBLIMATION).value,
            'xp_reward': self.enemy_types.get(enemy_type_key, {}).get('xp_reward', 150),
            'description': self.enemy_types.get(enemy_type_key, {}).get('description', 'Enemy threat detected'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'progress': 0,
            'defense_effectiveness': 0,
            'defense_actions': []
        }
        
        war_plans[user_id] = plan
        return plan
    
    def execute_enhanced_defense(
        self,
        user_id: str,
        defense_mechanism: DefenseMechanism,
        skill_levels: dict,
        tactic: str = None
    ) -> dict:
        """Execute defense with defense mechanisms"""
        if user_id not in war_plans:
            return {'success': False, 'error': 'No active war plan'}
        
        plan = war_plans[user_id]
        
        if not tactic:
            tactic = plan['defense_strategy']
        
        if tactic not in self.defense_tactics:
            return {'success': False, 'error': 'Invalid defense tactic'}
        
        defense = self.defense_tactics[tactic]
        enemy_type = EnemyType(plan['enemy_type'])
        
        # Calculate defense points using defense engine
        defense_result = defense_engine.calculate_defense_points(
            mechanism=defense_mechanism,
            base_points=float(plan['xp_reward']),
            skill_levels=skill_levels,
            enemy_threat=enemy_type,
            time_factor=1.0
        )
        
        # Calculate success based on defense effectiveness and mechanism
        base_success_chance = defense['effectiveness']
        mechanism_bonus = defense_engine.base_multipliers.get(defense_mechanism, 1.0) / 2.0  # Normalize
        success_chance = min(0.95, base_success_chance + (mechanism_bonus - 1.0) * 0.2)
        success = random.random() < success_chance
        
        # Store defense action
        defense_action = {
            'mechanism': defense_mechanism.value,
            'tactic': tactic,
            'final_points': defense_result['final_points'],
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        plan['defense_actions'].append(defense_action)
        
        if success:
            plan['status'] = 'defeated'
            plan['progress'] = 100
            plan['defense_effectiveness'] = success_chance
            
            result = {
                'success': True,
                'enemy_defeated': True,
                'xp_earned': int(defense_result['final_points']),
                'defense_used': defense['name'],
                'defense_mechanism': defense_mechanism.value,
                'defense_breakdown': defense_result,
                'message': f"Successfully defended against {plan['enemy_name']} using {defense_mechanism.value}!"
            }
        else:
            plan['progress'] += 20
            plan['defense_effectiveness'] = success_chance * 0.5
            
            result = {
                'success': True,
                'enemy_defeated': False,
                'xp_earned': int(defense_result['final_points'] * 0.3),
                'defense_used': defense['name'],
                'defense_mechanism': defense_mechanism.value,
                'defense_breakdown': defense_result,
                'message': f"Partial defense against {plan['enemy_name']}. Enemy still active.",
                'progress': plan['progress']
            }
        
        plan['last_defense'] = datetime.now().isoformat()
        return result
    
    def execute_hack(
        self,
        user_id: str,
        hack_type: HackType,
        target_enemy_id: str,
        skill_levels: dict,
        success_rate: float = 0.5
    ) -> dict:
        """Execute hack/scam against enemy"""
        # Find target enemy
        target_enemy = next((e for e in self.enemy_websites if e['id'] == target_enemy_id), None)
        if not target_enemy:
            return {'success': False, 'error': 'Target enemy not found'}
        
        enemy_type = EnemyType(target_enemy['type'])
        
        # Calculate hack points
        hack_result = defense_engine.calculate_hack_points(
            hack_type=hack_type,
            success_rate=success_rate,
            skill_levels=skill_levels,
            target_enemy=enemy_type
        )
        
        # Determine actual success
        actual_success = random.random() < success_rate
        
        return {
            'success': True,
            'hack_successful': actual_success,
            'hack_type': hack_type.value,
            'target_enemy': target_enemy['name'],
            'points_earned': int(hack_result['final_points'] if actual_success else hack_result['final_points'] * 0.2),
            'hack_breakdown': hack_result
        }
    
    def get_enhanced_intelligence(self, user_id: str) -> dict:
        """Gather enhanced intelligence with defense mechanisms"""
        if user_id not in war_plans:
            return {
                'intelligence': 'No active threats detected',
                'available_enemies': self.enemy_websites,
                'recommended_defenses': [mech.value for mech in DefenseMechanism]
            }
        
        plan = war_plans[user_id]
        
        intelligence = {
            'active_threats': 1,
            'threat_level': plan['threat_level'],
            'enemy_type': plan['enemy_name'],
            'enemy_type_enum': plan['enemy_type'],
            'recommended_defense': plan['defense_strategy'],
            'recommended_defense_mechanism': plan.get('recommended_defense_mechanism', 'sublimation'),
            'estimated_xp_reward': plan['xp_reward'],
            'status': plan['status'],
            'defense_actions_count': len(plan.get('defense_actions', [])),
            'available_enemies': self.enemy_websites,
            'available_hacks': defense_engine.get_available_hacks()
        }
        
        return intelligence

# Initialize enhanced war plan system
enhanced_war_plan_system = EnhancedEnemyWarPlan()

@enemy_war_plan_enhanced_bp.route('/war-plan-enhanced')
@enemy_war_plan_enhanced_bp.route('/vidgenerator/war-plan-enhanced')
def war_plan_enhanced_page():
    """Enhanced War Plan page"""
    return render_template('war_plan/index.html')

@enemy_war_plan_enhanced_bp.route('/api/war-plan-enhanced/generate', methods=['POST'])
@enemy_war_plan_enhanced_bp.route('/vidgenerator/api/war-plan-enhanced/generate', methods=['POST'])
def generate_enhanced_war_plan():
    """Generate enhanced war plan with enemy websites"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        enemy_website_id = data.get('enemy_website_id')
        
        plan = enhanced_war_plan_system.generate_enhanced_war_plan(user_id, enemy_website_id)
        
        return jsonify({
            'success': True,
            'war_plan': plan
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_enhanced_bp.route('/api/war-plan-enhanced/defend', methods=['POST'])
@enemy_war_plan_enhanced_bp.route('/vidgenerator/api/war-plan-enhanced/defend', methods=['POST'])
def execute_enhanced_defense():
    """Execute enhanced defense with defense mechanisms"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        mechanism_str = data.get('defense_mechanism', 'sublimation')
        tactic = data.get('tactic')
        
        # Get skill levels
        skill_levels = {
            SkillType.LOGIC: float(data.get('logic_skill', 50.0)),
            SkillType.ORGANIZATION: float(data.get('organization_skill', 50.0)),
            SkillType.SOCIAL: float(data.get('social_skill', 50.0)),
            SkillType.TECHNICAL: float(data.get('technical_skill', 50.0)),
            SkillType.STRATEGIC: float(data.get('strategic_skill', 50.0)),
            SkillType.PSYCHOLOGICAL: float(data.get('psychological_skill', 50.0)),
        }
        
        mechanism = DefenseMechanism(mechanism_str)
        result = enhanced_war_plan_system.execute_enhanced_defense(
            user_id=user_id,
            defense_mechanism=mechanism,
            skill_levels=skill_levels,
            tactic=tactic
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_enhanced_bp.route('/api/war-plan-enhanced/hack', methods=['POST'])
@enemy_war_plan_enhanced_bp.route('/vidgenerator/api/war-plan-enhanced/hack', methods=['POST'])
def execute_hack_attack():
    """Execute hack/scam against enemy"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        hack_str = data.get('hack_type', 'phishing')
        target_enemy_id = data.get('target_enemy_id')
        success_rate = float(data.get('success_rate', 0.5))
        
        # Get skill levels
        skill_levels = {
            SkillType.TECHNICAL: float(data.get('technical_skill', 50.0)),
            SkillType.STRATEGIC: float(data.get('strategic_skill', 50.0)),
            SkillType.SOCIAL: float(data.get('social_skill', 50.0)),
        }
        
        hack_type = HackType(hack_str)
        result = enhanced_war_plan_system.execute_hack(
            user_id=user_id,
            hack_type=hack_type,
            target_enemy_id=target_enemy_id,
            skill_levels=skill_levels,
            success_rate=success_rate
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enemy_war_plan_enhanced_bp.route('/api/war-plan-enhanced/intelligence/<user_id>', methods=['GET'])
@enemy_war_plan_enhanced_bp.route('/vidgenerator/api/war-plan-enhanced/intelligence/<user_id>', methods=['GET'])
def get_enhanced_intelligence(user_id):
    """Get enhanced intelligence"""
    try:
        intelligence = enhanced_war_plan_system.get_enhanced_intelligence(user_id)
        
        return jsonify({
            'success': True,
            'intelligence': intelligence
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

