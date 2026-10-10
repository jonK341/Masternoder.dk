"""
Trophie/Trophy Routes
Routes for trophy display and management with leaderboard integration
"""
from flask import Blueprint, render_template_string, jsonify, request
from backend.services.trophy_system import trophy_system
import os

trophie_bp = Blueprint('trophie', __name__)

@trophie_bp.route('/trophie')
@trophie_bp.route('/trophie/')
@trophie_bp.route('/vidgenerator/trophie')
@trophie_bp.route('/vidgenerator/trophie/')
def trophie_index():
    """Trophie/Trophy page with full template engine integration"""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        trophie_path = os.path.join(base_path, 'vidgenerator', 'trophie', 'index.html')
        
        if os.path.exists(trophie_path):
            with open(trophie_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML with template engine integration
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trophies - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/template-effects.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/image-support.css">
    <link rel="stylesheet" href="/vidgenerator/static/css/agent-skill-sets.css">
    <script src="/vidgenerator/static/js/template-engine-core.js"></script>
    <script src="/vidgenerator/static/js/template-effects.js"></script>
    <script src="/vidgenerator/static/js/image-support.js"></script>
    <script src="/vidgenerator/static/js/agent-skill-sets.js"></script>
    <style>
        body { 
            padding: 20px; 
            font-family: Arial, sans-serif; 
            background: var(--bg-primary, #0a0a0a);
            color: var(--text-primary, #fff);
        }
        .trophy-header {
            text-align: center;
            margin-bottom: 40px;
        }
        .trophy-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); 
            gap: 20px; 
            margin-top: 20px; 
        }
        .trophy-card { 
            padding: 20px; 
            border: 1px solid var(--border-primary, #333); 
            border-radius: 8px; 
            text-align: center;
            background: var(--bg-card, #1a1a1a);
            transition: all 0.3s ease;
        }
        .trophy-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.3);
            border-color: #ffd700;
        }
        .trophy-icon {
            font-size: 3em;
            margin-bottom: 10px;
        }
        .leaderboard-section {
            margin-top: 40px;
            padding: 20px;
            background: var(--bg-card, #1a1a1a);
            border-radius: 8px;
        }
        .leaderboard-item {
            padding: 10px;
            border-bottom: 1px solid var(--border-primary, #333);
            display: flex;
            justify-content: space-between;
        }
    </style>
</head>
<body>
    <div class="trophy-header">
        <h1>🏆 Trophies & Achievements</h1>
        <p>Your collection of victories and achievements</p>
    </div>
    
    <div id="trophies-container">
        <p>Loading trophies...</p>
    </div>
    
    <div class="leaderboard-section">
        <h2>🏅 Trophy Leaderboard</h2>
        <div id="leaderboard-container">
            <p>Loading leaderboard...</p>
        </div>
    </div>
    
    <script>
        // Load trophies
        async function loadTrophies() {
            try {
                const response = await fetch('/vidgenerator/api/trophie/list?user_id=default');
                const data = await response.json();
                
                const container = document.getElementById('trophies-container');
                if (data.success && data.trophies) {
                    const trophies = Array.isArray(data.trophies) ? data.trophies : Object.values(data.trophies);
                    container.innerHTML = '<div class="trophy-grid">' + 
                        trophies.map(t => {
                            const trophy = typeof t === 'string' ? {name: t, description: ''} : t;
                            return `<div class="trophy-card">
                                <div class="trophy-icon">🏆</div>
                                <h3>${trophy.name || trophy}</h3>
                                <p>${trophy.description || ''}</p>
                            </div>`;
                        }).join('') +
                        '</div>';
                } else {
                    container.innerHTML = '<p>No trophies yet. Start playing to earn trophies!</p>';
                }
            } catch (e) {
                console.error('Error loading trophies:', e);
                document.getElementById('trophies-container').innerHTML = '<p>Error loading trophies. Please try again later.</p>';
            }
        }
        
        // Load leaderboard
        async function loadLeaderboard() {
            try {
                const response = await fetch('/vidgenerator/api/leaderboard/trophies');
                const data = await response.json();
                
                const container = document.getElementById('leaderboard-container');
                if (data.success && data.leaderboard) {
                    container.innerHTML = data.leaderboard.map((item, index) => 
                        `<div class="leaderboard-item">
                            <span>#${index + 1} ${item.user_id || 'Unknown'}</span>
                            <span>${item.trophy_count || 0} trophies</span>
                        </div>`
                    ).join('');
                } else {
                    container.innerHTML = '<p>Leaderboard data not available.</p>';
                }
            } catch (e) {
                console.error('Error loading leaderboard:', e);
                document.getElementById('leaderboard-container').innerHTML = '<p>Error loading leaderboard.</p>';
            }
        }
        
        // Initialize
        loadTrophies();
        loadLeaderboard();
        
        // Refresh every 30 seconds
        setInterval(() => {
            loadTrophies();
            loadLeaderboard();
        }, 30000);
    </script>
</body>
</html>"""
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading trophie page: {str(e)}", 500

@trophie_bp.route('/api/trophie/list')
@trophie_bp.route('/vidgenerator/api/trophie/list')
def list_trophies_api():
    """List all trophies API with leaderboard integration"""
    try:
        user_id = request.args.get('user_id', 'default')
        
        # Get user trophies
        try:
            trophies = trophy_system.get_user_trophies(user_id)
        except:
            trophies = []
        
        # Get trophy definitions
        definitions = trophy_system.trophy_definitions
        
        return jsonify({
            'success': True,
            'trophies': trophies if isinstance(trophies, list) else list(trophies) if trophies else [],
            'definitions': definitions,
            'user_id': user_id
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@trophie_bp.route('/api/trophie/award', methods=['POST'])
@trophie_bp.route('/vidgenerator/api/trophie/award', methods=['POST'])
def award_trophy_api():
    """Award a trophy to a user"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', request.args.get('user_id', 'default'))
        trophy_type = data.get('trophy_type')
        
        if not trophy_type:
            return jsonify({
                'success': False,
                'error': 'Trophy type required'
            }), 400
        
        result = trophy_system.award_trophy(user_id, trophy_type, data.get('metadata', {}))
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
