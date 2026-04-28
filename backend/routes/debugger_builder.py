"""
Debugger Builder - Custom debugger creation and download
Awards points to hunters game
"""
from flask import Blueprint, jsonify, request, send_file, make_response
import json
import os
import tempfile
import zipfile
from datetime import datetime

debugger_builder_bp = Blueprint('debugger_builder', __name__)

@debugger_builder_bp.route('/api/debugger-builder/create', methods=['POST'])
def create_debugger():
    """Create custom debugger and award points"""
    try:
        data = request.get_json() or {}
        
        # Get debugger configuration
        debugger_name = data.get('name', 'custom_debugger')
        debugger_type = data.get('type', 'python')  # python, bash, powershell
        features = data.get('features', [])
        user_id = data.get('user_id', 'anonymous')
        
        # Create debugger code
        debugger_code = generate_debugger_code(debugger_name, debugger_type, features)
        
        # Create package (zip file)
        package_path = create_debugger_package(debugger_name, debugger_code, debugger_type)
        
        # Award points to hunters game
        points_awarded = award_debugger_points(user_id, len(features))
        
        return jsonify({
            'success': True,
            'message': f'Debugger "{debugger_name}" created successfully!',
            'debugger_name': debugger_name,
            'package_url': f'/api/debugger-builder/download/{debugger_name}',
            'points_awarded': points_awarded,
            'total_points': points_awarded.get('total_points', 0) if isinstance(points_awarded, dict) else 0
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger-builder/download/<debugger_name>', methods=['GET'])
def download_debugger(debugger_name):
    """Download debugger package"""
    try:
        # Create temp package
        debugger_code = generate_debugger_code(debugger_name, 'python', [])
        package_path = create_debugger_package(debugger_name, debugger_code, 'python')
        
        if os.path.exists(package_path):
            return send_file(
                package_path,
                as_attachment=True,
                download_name=f'{debugger_name}.zip',
                mimetype='application/zip'
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Package not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def generate_debugger_code(name, debugger_type, features):
    """Generate debugger code based on type and features"""
    
    if debugger_type == 'python':
        code = f'''#!/usr/bin/env python3
"""
Custom Debugger: {name}
Generated: {datetime.now().isoformat()}
"""
import sys
import json
import requests

def debug_api_endpoint(url):
    """Debug API endpoint"""
    try:
        if requests:
            response = requests.get(url, timeout=10)
            return {{
                'url': url,
                'status': response.status_code,
                'success': response.ok,
                'content_type': response.headers.get('Content-Type', ''),
                'response_preview': response.text[:500] if response.text else ''
            }}
        else:
            return {{
                'url': url,
                'error': 'requests library not available',
                'success': False
            }}
    except Exception as e:
        return {{
            'url': url,
            'error': str(e),
            'success': False
        }}

def main():
    """Main debugger function"""
    print("=" * 60)
    print(f"Custom Debugger: {name}")
    print("=" * 60)
    print()
    
    # Test endpoints
    endpoints = {json.dumps(features, indent=4) if features else '[]'}
    
    for endpoint in endpoints:
        print(f"Testing: {{endpoint}}")
        result = debug_api_endpoint(endpoint)
        print(f"  Status: {{result.get('status', 'ERROR')}}")
        print()

if __name__ == '__main__':
    main()
'''
    elif debugger_type == 'bash':
        code = f'''#!/bin/bash
# Custom Debugger: {name}
# Generated: {datetime.now().isoformat()}

echo "============================================================"
echo "Custom Debugger: {name}"
echo "============================================================"
echo ""

# Test endpoints
endpoints=({json.dumps(features) if features else '()'})

for endpoint in "${{endpoints[@]}}"; do
    echo "Testing: $endpoint"
    response=$(curl -s -w "\\n%{{http_code}}" "$endpoint")
    echo "$response"
    echo ""
done
'''
    else:  # powershell
        code = f'''# Custom Debugger: {name}
# Generated: {datetime.now().isoformat()}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Custom Debugger: {name}" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Test endpoints
$endpoints = @({json.dumps(features) if features else '()'})

foreach ($endpoint in $endpoints) {{
    Write-Host "Testing: $endpoint" -ForegroundColor Yellow
    try {{
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -TimeoutSec 10
        Write-Host "  Success!" -ForegroundColor Green
    }} catch {{
        Write-Host "  Error: $_" -ForegroundColor Red
    }}
    Write-Host ""
}}
'''
    
    return code

def create_debugger_package(name, code, debugger_type):
    """Create zip package with debugger files"""
    temp_dir = tempfile.mkdtemp()
    
    # Determine file extension
    ext = {
        'python': '.py',
        'bash': '.sh',
        'powershell': '.ps1'
    }.get(debugger_type, '.py')
    
    # Write debugger file
    debugger_file = os.path.join(temp_dir, f'{name}{ext}')
    with open(debugger_file, 'w', encoding='utf-8') as f:
        f.write(code)
    
    # Create README
    readme_file = os.path.join(temp_dir, 'README.md')
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(f'''# {name}

Custom Debugger Package

## Installation

### Python
```bash
python {name}.py
```

### Bash
```bash
chmod +x {name}.sh
./{name}.sh
```

### PowerShell
```powershell
.\{name}.ps1
```

## Generated
{datetime.now().isoformat()}
''')
    
    # Create zip file
    zip_path = os.path.join(temp_dir, f'{name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(debugger_file, f'{name}{ext}')
        zipf.write(readme_file, 'README.md')
    
    return zip_path

def award_debugger_points(user_id, feature_count):
    """Award points to hunters game for creating debugger"""
    try:
        # Base points for creating debugger
        base_points = 50
        
        # Bonus points per feature
        feature_bonus = feature_count * 10
        
        # Total points
        total_points = base_points + feature_bonus
        
        # Try to award via XP system
        try:
            from backend.services.xp_system import XPSystem
            xp_system = XPSystem()
            
            result = xp_system.award_xp(
                user_id=user_id,
                action='create_debugger',
                base_xp=total_points,
                metadata={
                    'debugger_type': 'custom',
                    'feature_count': feature_count
                }
            )
            
            return {
                'points_awarded': total_points,
                'total_points': result.get('total_xp', total_points),
                'level': result.get('level', 1),
                'leveled_up': result.get('leveled_up', False)
            }
        except ImportError:
            # XP system not available, return basic points
            return {
                'points_awarded': total_points,
                'total_points': total_points,
                'message': 'XP system not available'
            }
            
    except Exception as e:
        return {
            'points_awarded': 0,
            'error': str(e)
        }

# ========== AGENT FIXING FUNCTIONS ==========

@debugger_builder_bp.route('/api/debugger/agent/fix-personality', methods=['POST'])
def fix_agent_personality():
    """Fix agent personality issues"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Get current personality
        current = master_fix_agent_skills.skill_get_personality()
        
        # Fix common issues
        fixes = []
        personality = current.get('personality', {})
        
        if 'name' not in personality or not personality['name']:
            personality['name'] = 'Master Fix Agent'
            fixes.append('Added missing name')
        
        if 'personality_type' not in personality:
            personality['personality_type'] = 'analytical'
            fixes.append('Set default personality type')
        
        if 'traits' not in personality or not personality['traits']:
            personality['traits'] = ['methodical', 'thorough', 'detail-oriented']
            fixes.append('Added default traits')
        
        if 'experience_level' not in personality:
            personality['experience_level'] = 0
            fixes.append('Initialized experience level')
        
        # Update personality
        result = master_fix_agent_skills.skill_update_personality(personality)
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes,
            'personality': result.get('personality', {})
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger/agent/fix-missions', methods=['POST'])
def fix_agent_missions():
    """Fix agent mission issues"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Get missions
        missions_result = master_fix_agent_skills.skill_get_missions()
        missions = missions_result.get('missions', [])
        
        fixes = []
        
        # Fix orphaned missions
        for mission in missions:
            if mission.get('status') == 'active':
                # Check if mission is stale (older than 7 days)
                created = mission.get('created_at', '')
                if created:
                    from datetime import datetime, timedelta
                    try:
                        created_date = datetime.fromisoformat(created)
                        if datetime.now() - created_date > timedelta(days=7):
                            mission['status'] = 'stale'
                            fixes.append(f"Marked stale mission: {mission.get('name')}")
                    except:
                        pass
        
        # Create default maintenance mission if none exist
        if not missions:
            default_mission = master_fix_agent_skills.skill_create_mission(
                'System Maintenance',
                'Regular system maintenance and monitoring',
                [
                    'Check blueprint registration',
                    'Verify database integrity',
                    'Scan for missing methods',
                    'Monitor API structure',
                    'Check file integrity'
                ]
            )
            fixes.append('Created default maintenance mission')
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes,
            'missions_count': len(missions)
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger/agent/fix-quests', methods=['POST'])
def fix_agent_quests():
    """Fix agent quest issues"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Get quests
        quests_result = master_fix_agent_skills.skill_get_quests()
        quests = quests_result.get('quests', [])
        
        fixes = []
        
        # Fix incomplete quests
        for quest in quests:
            if quest.get('status') == 'in_progress':
                # Check if quest is stuck
                started = quest.get('started_at', '')
                if started:
                    from datetime import datetime, timedelta
                    try:
                        started_date = datetime.fromisoformat(started)
                        if datetime.now() - started_date > timedelta(days=30):
                            quest['status'] = 'abandoned'
                            fixes.append(f"Marked abandoned quest: {quest.get('name')}")
                    except:
                        pass
        
        # Create default quests if none exist
        if not quests:
            # Create starter quest
            starter_quest = master_fix_agent_skills.skill_create_quest(
                'First Steps',
                'Complete your first diagnostic',
                [
                    {'id': 'run_diagnostic', 'description': 'Run full system diagnostic', 'target': 1},
                    {'id': 'check_blueprints', 'description': 'Check blueprint registration', 'target': 1}
                ],
                {'experience': 50, 'achievement': 'First Steps'}
            )
            fixes.append('Created starter quest')
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes,
            'quests_count': len(quests)
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger/agent/fix-history', methods=['POST'])
def fix_agent_history():
    """Fix agent history issues"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Get history
        history_result = master_fix_agent_skills.skill_get_history(limit=1000)
        history = history_result.get('history', [])
        
        fixes = []
        
        # Clean up invalid entries
        valid_history = []
        for entry in history:
            if entry.get('skill') and entry.get('timestamp'):
                valid_history.append(entry)
            else:
                fixes.append('Removed invalid history entry')
        
        # Limit history size
        if len(valid_history) > 1000:
            valid_history = valid_history[-1000:]
            fixes.append('Trimmed history to 1000 entries')
        
        # Save cleaned history
        import json
        import os
        history_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'logs', 'agent_skills', 'skill_history.json'
        )
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(valid_history, f, indent=2, default=str)
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes,
            'history_count': len(valid_history)
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger/agent/fix-behavior', methods=['POST'])
def fix_agent_behavior():
    """Fix agent behavior patterns"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        data = request.get_json() or {}
        pattern = data.get('pattern', 'balanced')
        
        # Apply behavior pattern
        result = master_fix_agent_skills.skill_apply_behavior_pattern(pattern)
        
        # Get updated personality
        personality_result = master_fix_agent_skills.skill_get_personality()
        
        return jsonify({
            'success': True,
            'pattern_applied': pattern,
            'personality': personality_result.get('personality', {})
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_builder_bp.route('/api/debugger/agent/fix-all', methods=['POST'])
def fix_agent_all():
    """Fix all agent issues"""
    try:
        all_fixes = []
        
        # Fix personality
        try:
            result = fix_agent_personality()
            if result[0].get_json().get('success'):
                all_fixes.append('Personality fixed')
        except Exception as e:
            all_fixes.append(f'Personality fix failed: {str(e)[:50]}')
        
        # Fix missions
        try:
            result = fix_agent_missions()
            if result[0].get_json().get('success'):
                all_fixes.append('Missions fixed')
        except Exception as e:
            all_fixes.append(f'Missions fix failed: {str(e)[:50]}')
        
        # Fix quests
        try:
            result = fix_agent_quests()
            if result[0].get_json().get('success'):
                all_fixes.append('Quests fixed')
        except Exception as e:
            all_fixes.append(f'Quests fix failed: {str(e)[:50]}')
        
        # Fix history
        try:
            result = fix_agent_history()
            if result[0].get_json().get('success'):
                all_fixes.append('History fixed')
        except Exception as e:
            all_fixes.append(f'History fix failed: {str(e)[:50]}')
        
        # Fix behavior
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            master_fix_agent_skills.skill_apply_behavior_pattern('balanced')
            all_fixes.append('Behavior pattern reset')
        except Exception as e:
            all_fixes.append(f'Behavior fix failed: {str(e)[:50]}')
        
        return jsonify({
            'success': True,
            'fixes_applied': all_fixes,
            'total_fixes': len([f for f in all_fixes if 'failed' not in f])
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
