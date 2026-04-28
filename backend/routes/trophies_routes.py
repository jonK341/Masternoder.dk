"""
Trophies Routes
Routes for trophy display and management
Supports both /trophies (plural) and /trophie (singular) for compatibility
All endpoints resolve user_id via session > query > identification.
"""
from flask import Blueprint, jsonify, request
import os


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')

trophies_bp = Blueprint('trophies', __name__)

@trophies_bp.route('/vidgenerator/trophies')
@trophies_bp.route('/vidgenerator/trophies/')
@trophies_bp.route('/trophies')
@trophies_bp.route('/trophies/')
# Also support singular for backwards compatibility
@trophies_bp.route('/vidgenerator/trophie')
@trophies_bp.route('/vidgenerator/trophie/')
@trophies_bp.route('/trophie')
@trophies_bp.route('/trophie/')
def trophies_index():
    """Trophies page - serves the HTML file"""
    try:
        # Get the base path (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        trophies_path = os.path.join(base_path, 'vidgenerator', 'trophies', 'index.html')
        
        if os.path.exists(trophies_path):
            with open(trophies_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML if file doesn't exist
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trophies - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/navigation-toolbar.css">
    <style>
        body { 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }
        .trophies-container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .trophies-header {
            text-align: center;
            padding: 40px 20px;
            margin-bottom: 40px;
        }
        .trophies-header h1 {
            font-size: 4rem;
            font-weight: 900;
            margin: 0;
            background: linear-gradient(135deg, #FFD700, #FFA500);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .trophy-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 20px; 
            margin-top: 20px; 
        }
        .trophy-card { 
            padding: 20px; 
            border: 2px solid rgba(255, 215, 0, 0.3); 
            border-radius: 8px; 
            text-align: center;
            background: rgba(21, 21, 32, 0.8);
        }
        .trophy-card h3 {
            color: #FFD700;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div id="navigation-toolbar"></div>
    <div class="trophies-container">
        <div class="trophies-header">
            <h1>🏆 Trophies</h1>
            <p>Your achievements and accomplishments</p>
        </div>
        <div id="trophies-container">
            <p>Loading trophies...</p>
        </div>
    </div>
    <script src="/vidgenerator/static/js/navigation-toolbar.js"></script>
    <script>
        // Load trophies
        fetch('/api/trophies/list')
            .then(r => r.json())
            .catch(() => fetch('/api/trophie/list'))
            .then(r => r.json())
            .then(data => {
                const container = document.getElementById('trophies-container');
                if (data.success && data.trophies) {
                    container.innerHTML = '<div class="trophy-grid">' + 
                        data.trophies.map(t => `<div class="trophy-card"><h3>${t.name || t}</h3></div>`).join('') +
                        '</div>';
                } else {
                    container.innerHTML = '<p>No trophies found. Start earning trophies by playing!</p>';
                }
            })
            .catch(e => {
                console.error('Error loading trophies:', e);
                document.getElementById('trophies-container').innerHTML = 
                    '<p>Error loading trophies. Please try again later.</p>';
            });
    </script>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading trophies page: {str(e)}", 500

@trophies_bp.route('/api/trophies/list')
# Also support singular for backwards compatibility
@trophies_bp.route('/api/trophie/list')
def list_trophies_api():
    """List all trophies API (from DB when migration run, else legacy)."""
    try:
        user_id = _resolve_uid()
        trophies = []
        definitions = {}
        try:
            from backend.services.trophies_db_service import get_trophy_definitions, get_user_trophies
            definitions_list = get_trophy_definitions()
            trophies = get_user_trophies(user_id)
            definitions = {d['id']: d for d in definitions_list} if definitions_list else {}
        except Exception:
            pass
        if not definitions and not trophies:
            try:
                from backend.services.trophy_system import trophy_system
                trophies = trophy_system.get_user_trophies(user_id)
                definitions = getattr(trophy_system, 'trophy_definitions', {})
            except ImportError:
                pass
        # When DB and legacy have nothing, return a minimal list so the frontend always gets data
        if not trophies and not definitions:
            fallback = [
                {'id': 'first_video', 'name': 'First Video', 'description': 'Generate your first video', 'category': 'generation', 'icon': '\uD83C\uDFAC', 'rarity': 'common'},
                {'id': 'first_battle', 'name': 'First Battle', 'description': 'Complete your first battle', 'category': 'battle', 'icon': '\u2694\uFE0F', 'rarity': 'common'},
                {'id': 'first_trophy', 'name': 'Trophy Collector', 'description': 'Earn your first trophy', 'category': 'milestones', 'icon': '\uD83C\uDFC6', 'rarity': 'common'},
            ]
            return jsonify({
                'success': True,
                'trophies': [],
                'definitions': {t['id']: t for t in fallback},
                'user_id': user_id,
                'source': 'fallback'
            }), 200
        return jsonify({
            'success': True,
            'trophies': trophies,
            'definitions': definitions,
            'user_id': user_id
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@trophies_bp.route('/api/trophies/award', methods=['POST'])
# Also support singular for backwards compatibility
@trophies_bp.route('/api/trophie/award', methods=['POST'])
def award_trophy_api():
    """Award a trophy to a user (recorded in DB when migration run)."""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        trophy_id = data.get('trophy_id')
        if not trophy_id:
            return jsonify({'success': False, 'error': 'trophy_id is required'}), 400
        recorded = False
        try:
            from backend.services.trophies_db_service import award_trophy
            recorded = award_trophy(user_id, trophy_id)
        except Exception:
            pass
        result = {'message': 'Trophy awarded' if recorded else 'Trophy awarded (simulated)'}
        try:
            from backend.services.trophy_system import trophy_system
            result = trophy_system.award_trophy(user_id, trophy_id)
        except ImportError:
            pass
        return jsonify({
            'success': True,
            'user_id': user_id,
            'trophy_id': trophy_id,
            **result
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
