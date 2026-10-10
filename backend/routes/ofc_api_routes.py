"""
OFC API Routes
Open Framework Communication API with all systems
"""
from flask import Blueprint, request, jsonify
from backend.services.neutrino_system import neutrino_system
from backend.services.ghost_tables_dawn import ghost_tables_dawn
from backend.services.teenager_strategy_intelligence import teenager_strategy_intelligence
from backend.services.social_points_system import social_points_system
from backend.services.time_lock_security import time_lock_security
from backend.services.unified_point_matrix import unified_point_matrix
from backend.services.compass_hourglass_system import compass_hourglass_system
from backend.services.unified_point_counter import UnifiedPointCounter
from backend.services.victory_emblems_trophies import victory_emblems_trophies_system
import logging

logger = logging.getLogger(__name__)

ofc_api_bp = Blueprint('ofc_api', __name__, url_prefix='/api/ofc')

# Initialize unified point counter
unified_point_counter = UnifiedPointCounter()

# ========== Neutrino System Routes ==========

@ofc_api_bp.route('/neutrino/create', methods=['POST'])
def create_neutrino():
    """Create a neutrino particle"""
    try:
        data = request.get_json()
        flavor = data.get('flavor', 'electron')
        energy = data.get('energy', 1.0)
        position = data.get('position')
        
        result = neutrino_system.create_neutrino(flavor, energy, position)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating neutrino: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/neutrino/forces', methods=['POST'])
def calculate_neutrino_forces():
    """Calculate all forces for neutrino"""
    try:
        data = request.get_json()
        neutrino_id = data.get('neutrino_id')
        
        if not neutrino_id:
            return jsonify({'success': False, 'error': 'neutrino_id required'}), 400
        
        result = neutrino_system.calculate_all_forces(neutrino_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error calculating forces: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/neutrino/power', methods=['POST'])
def calculate_neutrino_power():
    """Calculate power for neutrino"""
    try:
        data = request.get_json()
        neutrino_id = data.get('neutrino_id')
        velocity = data.get('velocity')
        
        if not neutrino_id:
            return jsonify({'success': False, 'error': 'neutrino_id required'}), 400
        
        result = neutrino_system.calculate_power(neutrino_id, velocity)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error calculating power: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/neutrino/research-group/<group_id>/stats', methods=['GET'])
def get_research_group_stats(group_id):
    """Get research group statistics"""
    try:
        result = neutrino_system.get_research_group_stats(group_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting research stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Ghost Tables Routes ==========

@ofc_api_bp.route('/ghost-tables/add', methods=['POST'])
def add_to_ghost_table():
    """Add data to ghost table"""
    try:
        data = request.get_json()
        table_name = data.get('table_name')
        entry_data = data.get('data')
        
        if not table_name or not entry_data:
            return jsonify({'success': False, 'error': 'table_name and data required'}), 400
        
        result = ghost_tables_dawn.add_to_ghost_table(table_name, entry_data)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error adding to ghost table: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/ghost-tables/<table_name>', methods=['GET'])
def get_ghost_table(table_name):
    """Get ghost table data"""
    try:
        result = ghost_tables_dawn.get_ghost_table_data(table_name)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting ghost table: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Teenager Strategy Routes ==========

@ofc_api_bp.route('/teenager-strategy/analyze', methods=['POST'])
def analyze_teenager_behavior():
    """Analyze teenager behavior pattern"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        age = data.get('age')
        behavior_data = data.get('behavior_data', {})
        
        if not user_id or not age:
            return jsonify({'success': False, 'error': 'user_id and age required'}), 400
        
        result = teenager_strategy_intelligence.analyze_behavior_pattern(user_id, age, behavior_data)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error analyzing behavior: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/teenager-strategy/predict', methods=['POST'])
def predict_teenager_likelihood():
    """Predict teenager action likelihood"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        action_type = data.get('action_type')
        
        if not user_id or not action_type:
            return jsonify({'success': False, 'error': 'user_id and action_type required'}), 400
        
        result = teenager_strategy_intelligence.predict_likelihood(user_id, action_type)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error predicting likelihood: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Social Points Routes ==========

@ofc_api_bp.route('/social-points/add', methods=['POST'])
def add_social_points():
    """Add social points"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        points = data.get('points', 0.0)
        activity_type = data.get('activity_type', 'general')
        metadata = data.get('metadata', {})
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400
        
        result = social_points_system.add_social_points(user_id, points, activity_type, metadata)
        
        # Update unified point system
        unified_point_counter.add_points(user_id, {'social_points': points})
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error adding social points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/social-points/<user_id>', methods=['GET'])
def get_social_points(user_id):
    """Get social points for user"""
    try:
        result = social_points_system.get_social_points(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting social points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Time Lock Security Routes ==========

@ofc_api_bp.route('/time-lock/create', methods=['POST'])
def create_time_lock():
    """Create time lock for structure"""
    try:
        data = request.get_json()
        structure_id = data.get('structure_id')
        structure_type = data.get('structure_type', 'generic')
        structure_data = data.get('data')
        unlock_time = data.get('unlock_time')
        
        if not structure_id or not structure_data:
            return jsonify({'success': False, 'error': 'structure_id and data required'}), 400
        
        from datetime import datetime
        unlock_dt = datetime.fromisoformat(unlock_time) if unlock_time else None
        
        result = time_lock_security.create_time_lock(structure_id, structure_type, structure_data, unlock_dt)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating time lock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/time-lock/verify', methods=['POST'])
def verify_time_lock():
    """Verify time lock"""
    try:
        data = request.get_json()
        structure_id = data.get('structure_id')
        structure_data = data.get('data')
        
        if not structure_id or not structure_data:
            return jsonify({'success': False, 'error': 'structure_id and data required'}), 400
        
        result = time_lock_security.verify_time_lock(structure_id, structure_data)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error verifying time lock: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/time-lock/protect-dna', methods=['POST'])
def protect_dna():
    """Protect DNA sequence with time lock"""
    try:
        data = request.get_json()
        dna_id = data.get('dna_id')
        sequence = data.get('sequence')
        
        if not dna_id or not sequence:
            return jsonify({'success': False, 'error': 'dna_id and sequence required'}), 400
        
        result = time_lock_security.protect_dna_sequence(dna_id, sequence)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error protecting DNA: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Unified Point Matrix Routes ==========

@ofc_api_bp.route('/unified-matrix/matrix-all', methods=['POST'])
def matrix_all_points():
    """Matrix all points into unified system"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        point_systems = data.get('point_systems', {})
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400
        
        result = unified_point_matrix.matrix_all_points(user_id, point_systems)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error matrixing points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/unified-matrix/<user_id>', methods=['GET'])
def get_unified_matrix(user_id):
    """Get unified point matrix"""
    try:
        result = unified_point_matrix.get_unified_matrix(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting unified matrix: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/unified-matrix/calculate-all', methods=['POST'])
def calculate_all_now():
    """Calculate all points now"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        result = unified_point_matrix.calculate_all_now(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error calculating all: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Compass & HourGlass Routes ==========

@ofc_api_bp.route('/compass/create', methods=['POST'])
def create_compass():
    """Create compass"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        target = data.get('target')
        
        if not user_id or not target:
            return jsonify({'success': False, 'error': 'user_id and target required'}), 400
        
        result = compass_hourglass_system.create_compass(user_id, target)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating compass: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/hourglass/create', methods=['POST'])
def create_hourglass():
    """Create hourglass timer"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        duration_minutes = data.get('duration_minutes', 60)
        purpose = data.get('purpose', 'general')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'user_id required'}), 400
        
        result = compass_hourglass_system.create_hourglass(user_id, duration_minutes, purpose)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating hourglass: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/spells/create', methods=['POST'])
def create_spell():
    """Create textual spell"""
    try:
        data = request.get_json()
        spell_name = data.get('spell_name')
        spell_text = data.get('spell_text')
        effect_type = data.get('effect_type', 'general')
        power_level = data.get('power_level', 1)
        
        if not spell_name or not spell_text:
            return jsonify({'success': False, 'error': 'spell_name and spell_text required'}), 400
        
        result = compass_hourglass_system.create_textual_spell(spell_name, spell_text, effect_type, power_level)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating spell: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/spells/cast', methods=['POST'])
def cast_spell():
    """Cast textual spell"""
    try:
        data = request.get_json()
        spell_id = data.get('spell_id')
        target = data.get('target')
        
        if not spell_id or not target:
            return jsonify({'success': False, 'error': 'spell_id and target required'}), 400
        
        result = compass_hourglass_system.cast_spell(spell_id, target)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error casting spell: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v2/add', methods=['POST'])
def add_to_rulebook():
    """Add rule to Rulebook v2.0"""
    try:
        data = request.get_json()
        rule_name = data.get('rule_name')
        rule_text = data.get('rule_text')
        category = data.get('category', 'general')
        
        if not rule_name or not rule_text:
            return jsonify({'success': False, 'error': 'rule_name and rule_text required'}), 400
        
        result = compass_hourglass_system.add_to_rulebook_v2(rule_name, rule_text, category)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error adding to rulebook: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v2', methods=['GET'])
def get_rulebook():
    """Get Rulebook v2.0"""
    try:
        result = compass_hourglass_system.get_rulebook_v2()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting rulebook: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Rulebook v3.0 Routes ==========

@ofc_api_bp.route('/rulebook-v3/add', methods=['POST'])
def add_to_rulebook_v3():
    """Add rule to Rulebook v3.0"""
    try:
        data = request.get_json()
        rule_name = data.get('rule_name')
        rule_text = data.get('rule_text')
        category = data.get('category', 'general')
        subcategory = data.get('subcategory')
        tags = data.get('tags', [])
        priority = data.get('priority', 5)
        dependencies = data.get('dependencies', [])
        expires_at = data.get('expires_at')
        active = data.get('active', True)
        metadata = data.get('metadata', {})
        
        if not rule_name or not rule_text:
            return jsonify({'success': False, 'error': 'rule_name and rule_text required'}), 400
        
        from datetime import datetime
        expires_dt = datetime.fromisoformat(expires_at) if expires_at else None
        
        result = compass_hourglass_system.add_to_rulebook_v3(
            rule_name, rule_text, category, subcategory, tags, priority,
            dependencies, expires_dt, active, metadata
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error adding to rulebook v3: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3', methods=['GET'])
def get_rulebook_v3():
    """Get Rulebook v3.0 with filtering"""
    try:
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        tags = request.args.getlist('tags')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        priority_min = request.args.get('priority_min', type=int)
        
        result = compass_hourglass_system.get_rulebook_v3(
            category, subcategory, tags if tags else None, active_only, priority_min
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting rulebook v3: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/search', methods=['GET'])
def search_rules_v3():
    """Search rules in Rulebook v3.0"""
    try:
        query = request.args.get('query', '')
        category = request.args.get('category')
        
        if not query:
            return jsonify({'success': False, 'error': 'query parameter required'}), 400
        
        result = compass_hourglass_system.search_rules_v3(query, category)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error searching rules: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>', methods=['GET'])
def get_rule_v3(rule_id):
    """Get a specific rule from Rulebook v3.0"""
    try:
        result = compass_hourglass_system.view_rule_v3(rule_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting rule: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>', methods=['PUT'])
def update_rule_v3(rule_id):
    """Update a rule in Rulebook v3.0"""
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        
        if not updates:
            return jsonify({'success': False, 'error': 'updates required'}), 400
        
        result = compass_hourglass_system.update_rule_v3(rule_id, updates)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error updating rule: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>/deactivate', methods=['POST'])
def deactivate_rule_v3(rule_id):
    """Deactivate a rule in Rulebook v3.0"""
    try:
        result = compass_hourglass_system.deactivate_rule_v3(rule_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error deactivating rule: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>/activate', methods=['POST'])
def activate_rule_v3(rule_id):
    """Activate a rule in Rulebook v3.0"""
    try:
        result = compass_hourglass_system.activate_rule_v3(rule_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error activating rule: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>/rate', methods=['POST'])
def rate_rule_v3(rule_id):
    """Rate a rule in Rulebook v3.0"""
    try:
        data = request.get_json()
        rating = data.get('rating')
        
        if not rating or not isinstance(rating, (int, float)):
            return jsonify({'success': False, 'error': 'rating (1-10) required'}), 400
        
        result = compass_hourglass_system.rate_rule_v3(rule_id, float(rating))
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error rating rule: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/<rule_id>/history', methods=['GET'])
def get_rule_history_v3(rule_id):
    """Get history for a rule in Rulebook v3.0"""
    try:
        result = compass_hourglass_system.get_rule_history_v3(rule_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting rule history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/analytics', methods=['GET'])
def get_rulebook_analytics_v3():
    """Get analytics for Rulebook v3.0"""
    try:
        result = compass_hourglass_system.get_rule_analytics_v3()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting rulebook analytics: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/templates', methods=['POST'])
def create_rule_template_v3():
    """Create a rule template for Rulebook v3.0"""
    try:
        data = request.get_json()
        template_name = data.get('template_name')
        template_data = data.get('template_data', {})
        
        if not template_name:
            return jsonify({'success': False, 'error': 'template_name required'}), 400
        
        result = compass_hourglass_system.create_rule_template_v3(template_name, template_data)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating rule template: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Fantasy Monsters Routes ==========

@ofc_api_bp.route('/rulebook-v3/monsters/create', methods=['POST'])
def create_fantasy_monster():
    """Create a fantasy monster"""
    try:
        data = request.get_json()
        monster_name = data.get('monster_name')
        monster_type = data.get('monster_type', 'beast')
        stats = data.get('stats', {})
        abilities = data.get('abilities', [])
        weaknesses = data.get('weaknesses', [])
        divine_power = data.get('divine_power', 0.0)
        psycho_factors = data.get('psycho_factors', [])
        
        if not monster_name or not stats:
            return jsonify({'success': False, 'error': 'monster_name and stats required'}), 400
        
        result = compass_hourglass_system.create_fantasy_monster(
            monster_name, monster_type, stats, abilities, weaknesses,
            divine_power, psycho_factors
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating monster: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/monsters/<monster_id>', methods=['GET'])
def get_fantasy_monster(monster_id):
    """Get a fantasy monster"""
    try:
        result = compass_hourglass_system.get_fantasy_monster(monster_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting monster: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/monsters', methods=['GET'])
def list_fantasy_monsters():
    """List all fantasy monsters"""
    try:
        monster_type = request.args.get('type')
        result = compass_hourglass_system.list_fantasy_monsters(monster_type)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error listing monsters: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Enhanced Spells Routes ==========

@ofc_api_bp.route('/rulebook-v3/spells/enhanced/create', methods=['POST'])
def create_enhanced_spell():
    """Create an enhanced spell with pluses/minuses"""
    try:
        data = request.get_json()
        spell_name = data.get('spell_name')
        spell_text = data.get('spell_text')
        effect_type = data.get('effect_type', 'general')
        power_level = data.get('power_level', 1)
        pluses = data.get('pluses', {})
        minuses = data.get('minuses', {})
        divine_bonus = data.get('divine_bonus', 0.0)
        psycho_effects = data.get('psycho_effects', [])
        mana_cost = data.get('mana_cost', 10)
        
        if not spell_name or not spell_text:
            return jsonify({'success': False, 'error': 'spell_name and spell_text required'}), 400
        
        result = compass_hourglass_system.create_enhanced_spell(
            spell_name, spell_text, effect_type, power_level,
            pluses, minuses, divine_bonus, psycho_effects, mana_cost
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating enhanced spell: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/spells/enhanced/cast', methods=['POST'])
def cast_enhanced_spell():
    """Cast an enhanced spell"""
    try:
        data = request.get_json()
        spell_id = data.get('spell_id')
        target = data.get('target')
        target_type = data.get('target_type', 'monster')
        
        if not spell_id or not target:
            return jsonify({'success': False, 'error': 'spell_id and target required'}), 400
        
        result = compass_hourglass_system.cast_enhanced_spell(spell_id, target, target_type)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error casting enhanced spell: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Divine Elements Routes ==========

@ofc_api_bp.route('/rulebook-v3/divine/create', methods=['POST'])
def create_divine_element():
    """Create a divine element"""
    try:
        data = request.get_json()
        element_name = data.get('element_name')
        element_type = data.get('element_type', 'blessing')
        power_level = data.get('power_level', 1.0)
        blessings = data.get('blessings', [])
        curses = data.get('curses', [])
        
        if not element_name:
            return jsonify({'success': False, 'error': 'element_name required'}), 400
        
        result = compass_hourglass_system.create_divine_element(
            element_name, element_type, power_level, blessings, curses
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating divine element: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/divine/<element_id>/blessing', methods=['POST'])
def apply_divine_blessing(element_id):
    """Apply a divine blessing"""
    try:
        data = request.get_json()
        target = data.get('target')
        
        if not target:
            return jsonify({'success': False, 'error': 'target required'}), 400
        
        result = compass_hourglass_system.apply_divine_blessing(element_id, target)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error applying blessing: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/divine/<element_id>/curse', methods=['POST'])
def apply_divine_curse(element_id):
    """Apply a divine curse"""
    try:
        data = request.get_json()
        target = data.get('target')
        
        if not target:
            return jsonify({'success': False, 'error': 'target required'}), 400
        
        result = compass_hourglass_system.apply_divine_curse(element_id, target)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error applying curse: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Psycho Factors Routes ==========

@ofc_api_bp.route('/rulebook-v3/psycho/create', methods=['POST'])
def create_psycho_factor():
    """Create a psycho factor"""
    try:
        data = request.get_json()
        factor_name = data.get('factor_name')
        factor_type = data.get('factor_type', 'mental')
        intensity = data.get('intensity', 0.5)
        effects = data.get('effects', {})
        triggers = data.get('triggers', [])
        
        if not factor_name or not effects:
            return jsonify({'success': False, 'error': 'factor_name and effects required'}), 400
        
        result = compass_hourglass_system.create_psycho_factor(
            factor_name, factor_type, intensity, effects, triggers
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating psycho factor: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/psycho/apply', methods=['POST'])
def apply_psycho_factors():
    """Apply multiple psycho factors"""
    try:
        data = request.get_json()
        target = data.get('target')
        factor_ids = data.get('factor_ids', [])
        
        if not target or not factor_ids:
            return jsonify({'success': False, 'error': 'target and factor_ids required'}), 400
        
        result = compass_hourglass_system.apply_psycho_factors(target, factor_ids)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error applying psycho factors: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/psycho', methods=['GET'])
def get_all_psycho_factors():
    """Get all psycho factors"""
    try:
        result = compass_hourglass_system.get_all_psycho_factors()
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting psycho factors: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Enhanced Stats Routes ==========

@ofc_api_bp.route('/rulebook-v3/stats/enhanced/create', methods=['POST'])
def create_enhanced_stats():
    """Create enhanced stats"""
    try:
        data = request.get_json()
        entity_id = data.get('entity_id')
        entity_type = data.get('entity_type', 'character')
        base_stats = data.get('base_stats', {})
        stat_modifiers = data.get('stat_modifiers', {})
        divine_modifiers = data.get('divine_modifiers', {})
        psycho_modifiers = data.get('psycho_modifiers', {})
        
        if not entity_id or not base_stats:
            return jsonify({'success': False, 'error': 'entity_id and base_stats required'}), 400
        
        result = compass_hourglass_system.create_enhanced_stats(
            entity_id, entity_type, base_stats, stat_modifiers,
            divine_modifiers, psycho_modifiers
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating enhanced stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/stats/enhanced/<entity_id>', methods=['GET'])
def get_enhanced_stats(entity_id):
    """Get enhanced stats"""
    try:
        result = compass_hourglass_system.get_enhanced_stats(entity_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting enhanced stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/rulebook-v3/stats/enhanced/<entity_id>', methods=['PUT'])
def update_enhanced_stats(entity_id):
    """Update enhanced stats"""
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        
        if not updates:
            return jsonify({'success': False, 'error': 'updates required'}), 400
        
        result = compass_hourglass_system.update_enhanced_stats(entity_id, updates)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error updating enhanced stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Unified Points Sync Route ==========

@ofc_api_bp.route('/unified-points/sync', methods=['POST'])
def sync_unified_points():
    """Sync and equalize all unified points to frontend"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        
        # Get all points from unified counter
        all_points = unified_point_counter.get_all_points(user_id, force_refresh=True)
        
        # Matrix all points
        matrix_result = unified_point_matrix.matrix_all_points(user_id, all_points)
        
        # Calculate all
        calculation_result = unified_point_matrix.calculate_all_now(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'unified_points': all_points,
            'matrix': matrix_result.get('matrix_entry'),
            'calculation': calculation_result.get('calculation'),
            'synced_at': unified_point_counter.get_last_update_time(user_id)
        }), 200
    except Exception as e:
        logger.error(f"Error syncing unified points: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== Victory Emblems and Trophies Routes ==========

@ofc_api_bp.route('/victory/emblem/create', methods=['POST'])
def create_victory_emblem():
    """Create a victory emblem"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        name = data.get('name')
        description = data.get('description')
        victory_type = data.get('victory_type', 'war')
        rarity = data.get('rarity', 'common')
        icon = data.get('icon', '🏆')
        power_level = data.get('power_level', 1.0)
        switch_statement = data.get('switch_statement', '')
        affection_level = data.get('affection_level', 0.0)
        shadow_intensity = data.get('shadow_intensity', 0.0)
        cloud_size = data.get('cloud_size', 0.0)
        
        if not name or not description:
            return jsonify({'success': False, 'error': 'name and description required'}), 400
        
        result = victory_emblems_trophies_system.create_victory_emblem(
            user_id, name, description, victory_type, rarity, icon, power_level,
            switch_statement, affection_level, shadow_intensity, cloud_size
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating victory emblem: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/trophy/create', methods=['POST'])
def create_victory_trophy():
    """Create a victory trophy"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        name = data.get('name')
        description = data.get('description')
        war_id = data.get('war_id')
        opponent_type = data.get('opponent_type', 'goliath')
        victory_method = data.get('victory_method', 'strategic')
        war_duration_years = data.get('war_duration_years', 0)
        final_statement = data.get('final_statement', '')
        overlooked_statement = data.get('overlooked_statement', '')
        trigger_timing = data.get('trigger_timing_seconds', 0)
        criminal_mentality_cuts = data.get('criminal_mentality_cuts', 0)
        
        if not name or not description or not war_id:
            return jsonify({'success': False, 'error': 'name, description, and war_id required'}), 400
        
        result = victory_emblems_trophies_system.create_victory_trophy(
            user_id, name, description, war_id, opponent_type, victory_method,
            war_duration_years, final_statement, overlooked_statement,
            trigger_timing, criminal_mentality_cuts
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error creating victory trophy: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/goliath/defeat', methods=['POST'])
def record_goliath_defeat():
    """Record a victory against an overpowered goliath"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        goliath_name = data.get('goliath_name')
        goliath_power = data.get('goliath_power', 1.0)
        defeat_method = data.get('defeat_method', 'strategic')
        years_of_war = data.get('years_of_war', 0)
        switch_statement = data.get('switch_statement', 'They are switching on them now')
        affection_gained = data.get('affection_gained', 0.0)
        shadow_from_giga = data.get('shadow_from_giga', 0.0)
        cloud_from_giga = data.get('cloud_from_giga', 0.0)
        
        if not goliath_name:
            return jsonify({'success': False, 'error': 'goliath_name required'}), 400
        
        result = victory_emblems_trophies_system.record_goliath_defeat(
            user_id, goliath_name, goliath_power, defeat_method, years_of_war,
            switch_statement, affection_gained, shadow_from_giga, cloud_from_giga
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error recording goliath defeat: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/ego/defeat', methods=['POST'])
def record_ego_defeat():
    """Record a victory against an undermined EGO"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        ego_name = data.get('ego_name')
        ego_arrogance_level = data.get('ego_arrogance_level', 1.0)
        defeat_method = data.get('defeat_method', 'strategic')
        years_of_war = data.get('years_of_war', 0)
        winner_mentality_tripped = data.get('winner_mentality_tripped', True)
        criminal_mentality_cuts = data.get('criminal_mentality_cuts', 0)
        
        if not ego_name:
            return jsonify({'success': False, 'error': 'ego_name required'}), 400
        
        result = victory_emblems_trophies_system.record_ego_defeat(
            user_id, ego_name, ego_arrogance_level, defeat_method, years_of_war,
            winner_mentality_tripped, criminal_mentality_cuts
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error recording ego defeat: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/war/record', methods=['POST'])
def record_war_victory():
    """Record a complete war victory"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        opponent_name = data.get('opponent_name')
        opponent_type = data.get('opponent_type', 'goliath')
        war_duration_years = data.get('war_duration_years', 0)
        victory_method = data.get('victory_method', 'strategic')
        switch_statement = data.get('switch_statement', 'They are switching on them now')
        overlooked_statement = data.get('overlooked_statement', '')
        trigger_timing = data.get('trigger_timing_seconds', 4)
        affection_gained = data.get('affection_gained', 0.0)
        shadow_intensity = data.get('shadow_intensity', 0.0)
        cloud_size = data.get('cloud_size', 0.0)
        viking_frenzy_triggered = data.get('viking_frenzy_triggered', False)
        criminal_mentality_cuts = data.get('criminal_mentality_cuts', 0)
        
        if not opponent_name:
            return jsonify({'success': False, 'error': 'opponent_name required'}), 400
        
        result = victory_emblems_trophies_system.record_war_victory(
            user_id, opponent_name, opponent_type, war_duration_years, victory_method,
            switch_statement, overlooked_statement, trigger_timing, affection_gained,
            shadow_intensity, cloud_size, viking_frenzy_triggered, criminal_mentality_cuts
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error recording war victory: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/viking-frenzy/trigger', methods=['POST'])
def trigger_viking_frenzy():
    """Trigger Viking Blood Frenzy (0-133% instant)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        emblem_id = data.get('emblem_id')
        trigger_intensity = data.get('trigger_intensity', 1.33)
        
        if not emblem_id:
            return jsonify({'success': False, 'error': 'emblem_id required'}), 400
        
        result = victory_emblems_trophies_system.trigger_viking_blood_frenzy(
            user_id, emblem_id, trigger_intensity
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error triggering viking frenzy: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/jyske-lov/apply', methods=['POST'])
def apply_jyske_lov():
    """Apply Jyske Lov (Jutlandic Law)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        target_id = data.get('target_id')
        violation_type = data.get('violation_type', 'alarm_ignored')
        
        if not target_id:
            return jsonify({'success': False, 'error': 'target_id required'}), 400
        
        result = victory_emblems_trophies_system.apply_jyske_lov(
            user_id, target_id, violation_type
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error applying Jyske Lov: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/monster-hunter/add', methods=['POST'])
def add_fantasy_monster_hunter():
    """Add a fantasy monster hunter seeking answers"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        trophy_id = data.get('trophy_id')
        monster_name = data.get('monster_name')
        hunting_reason = data.get('hunting_reason', 'Seeking answers about the victory curse')
        
        if not trophy_id or not monster_name:
            return jsonify({'success': False, 'error': 'trophy_id and monster_name required'}), 400
        
        result = victory_emblems_trophies_system.add_fantasy_monster_hunter(
            user_id, trophy_id, monster_name, hunting_reason
        )
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error adding fantasy monster hunter: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/emblems/<user_id>', methods=['GET'])
def get_user_emblems(user_id):
    """Get all victory emblems for a user"""
    try:
        result = victory_emblems_trophies_system.get_user_emblems(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting user emblems: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/trophies/<user_id>', methods=['GET'])
def get_user_trophies(user_id):
    """Get all victory trophies for a user"""
    try:
        museum_category = request.args.get('museum_category')
        result = victory_emblems_trophies_system.get_user_trophies(user_id, museum_category)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting user trophies: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/museum/<user_id>', methods=['GET'])
def get_museum_collection(user_id):
    """Get museum collection for a user"""
    try:
        result = victory_emblems_trophies_system.get_museum_collection(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting museum collection: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@ofc_api_bp.route('/victory/stats/<user_id>', methods=['GET'])
def get_victory_stats(user_id):
    """Get comprehensive victory statistics"""
    try:
        result = victory_emblems_trophies_system.get_victory_stats(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting victory stats: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

