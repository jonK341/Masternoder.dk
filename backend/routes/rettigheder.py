"""
Rettigheder API - Håndter rettigheder
"""
from flask import Blueprint, jsonify, request
from datetime import datetime

# Import rights law system
try:
    from backend.services.rights_law_system import rights_law_system
    RIGHTS_SYSTEM_AVAILABLE = True
except ImportError:
    RIGHTS_SYSTEM_AVAILABLE = False
    rights_law_system = None

rettigheder_bp = Blueprint('rettigheder', __name__)

@rettigheder_bp.route('/api/rettigheder/slaa', methods=['POST'])
@rettigheder_bp.route('/vidgenerator/api/rettigheder/slaa', methods=['POST'])
def slaa_rettigheder():
    """Slå valgte rettigheder"""
    try:
        data = request.get_json() or {}
        rettigheder = data.get('rettigheder', [])
        user_id = data.get('user_id', 'default_user')
        
        if not rettigheder:
            return jsonify({
                'success': False,
                'error': 'Ingen rettigheder valgt'
            }), 400
        
        # Implementer faktisk logik til at slå rettigheder
        if RIGHTS_SYSTEM_AVAILABLE and rights_law_system:
            # Track user rights selections
            if not hasattr(rights_law_system, 'user_rights'):
                rights_law_system.user_rights = {}
            
            if user_id not in rights_law_system.user_rights:
                rights_law_system.user_rights[user_id] = {}
            
            # Mark each selected right as active
            activated_rights = []
            for rettighed in rettigheder:
                right_id = f"custom_{rettighed.lower().replace(' ', '_')}"
                rights_law_system.user_rights[user_id][right_id] = {
                    'right_name': rettighed,
                    'activated_at': datetime.utcnow().isoformat(),
                    'active': True
                }
                activated_rights.append(rettighed)
            
            return jsonify({
                'success': True,
                'message': f'{len(activated_rights)} rettigheder er blevet slået',
                'rettigheder': activated_rights,
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        else:
            # Fallback if system not available
            return jsonify({
                'success': True,
                'message': f'{len(rettigheder)} rettigheder er blevet slået',
                'rettigheder': rettigheder,
                'timestamp': datetime.utcnow().isoformat(),
                'note': 'Rights system not available, using fallback'
            })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@rettigheder_bp.route('/api/rettigheder/list', methods=['GET'])
@rettigheder_bp.route('/vidgenerator/api/rettigheder/list', methods=['GET'])
def list_rettigheder():
    """List alle tilgængelige rettigheder"""
    rettigheder = [
        'Musik', 'TV', 'Sex', 'Porn', 'ID', 'EGO', 'Commercials',
        'Girls', 'Woman', 'Baby', 'Familie', 'Født', 'Garanti',
        'Boks', 'Fodbold', 'Fisse', 'Kusse', 'Pussy', 'Jon. Køhrsen', 'ASE'
    ]
    
    return jsonify({
        'success': True,
        'rettigheder': rettigheder,
        'total': len(rettigheder)
    })

@rettigheder_bp.route('/api/rettigheder/status', methods=['GET'])
@rettigheder_bp.route('/vidgenerator/api/rettigheder/status', methods=['GET'])
def get_rettigheder_status():
    """Hent status for alle rettigheder"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Standard rettigheder liste
        rettigheder = [
            'Musik', 'TV', 'Sex', 'Porn', 'ID', 'EGO', 'Commercials',
            'Girls', 'Woman', 'Baby', 'Familie', 'Født', 'Garanti',
            'Boks', 'Fodbold', 'Fisse', 'Kusse', 'Pussy', 'Jon. Køhrsen', 'ASE'
        ]
        
        # Hent faktisk status fra rights_law_system
        status = {}
        if RIGHTS_SYSTEM_AVAILABLE and rights_law_system:
            # Get user's activated rights
            user_rights = {}
            if hasattr(rights_law_system, 'user_rights') and user_id in rights_law_system.user_rights:
                user_rights = rights_law_system.user_rights[user_id]
            
            # Check each right's status
            for rettighed in rettigheder:
                right_id = f"custom_{rettighed.lower().replace(' ', '_')}"
                # Check if right is activated for this user
                if right_id in user_rights:
                    right_data = user_rights[right_id]
                    status[rettighed] = right_data.get('active', False)
                else:
                    status[rettighed] = False
        else:
            # Fallback: returner alle som inaktive
            status = {r: False for r in rettigheder}
        
        return jsonify({
            'success': True,
            'status': status,
            'user_id': user_id,
            'total_rights': len(rettigheder),
            'active_rights': sum(1 for v in status.values() if v)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'status': {}
        }), 500

