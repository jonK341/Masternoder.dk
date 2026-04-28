"""
Master Loose Ends Fix Script
Automatically fixes all loose ends once and for all
- Registers all blueprints
- Checks agent/services sector
- Reports to control board
- Fixes database issues
- Adds navigation links
- Verifies everything
"""
import os
import sys
import json
import re
import glob
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Control Board Report
CONTROL_REPORT = {
    'timestamp': datetime.now().isoformat(),
    'status': 'running',
    'sections': {},
    'errors': [],
    'warnings': [],
    'fixed': [],
    'summary': {}
}

def log_section(section, message, status='info'):
    """Log to control report"""
    if section not in CONTROL_REPORT['sections']:
        CONTROL_REPORT['sections'][section] = []
    
    CONTROL_REPORT['sections'][section].append({
        'message': message,
        'status': status,
        'timestamp': datetime.now().isoformat()
    })
    
    prefix = {
        'info': 'ℹ️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️'
    }.get(status, 'ℹ️')
    
    print(f"{prefix} [{section}] {message}")

def find_all_blueprints():
    """Find all blueprint definitions - uses API scanner if available"""
    try:
        # Try to use API scanner for more comprehensive scanning
        from backend.services.api_scanner import APIScanner
        scanner = APIScanner(BASE_DIR)
        blueprints_data = scanner.scan_blueprints()
        
        # Convert to expected format
        blueprints = []
        for bp in blueprints_data:
            if 'error' not in bp:
                blueprints.append({
                    'file': bp['file'],
                    'variable': bp['variable'],
                    'name': bp['name'],
                    'module': bp['module']
                })
        return blueprints
    except ImportError:
        # Fallback to manual scanning
        log_section('blueprints', "API scanner not available, using manual scan", 'warning')
        blueprints = []
        
        # Search backend/routes
        routes_dir = os.path.join(BASE_DIR, 'backend', 'routes')
        if os.path.exists(routes_dir):
            for file in glob.glob(os.path.join(routes_dir, '*.py')):
                if file.endswith('.backup'):
                    continue
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Find blueprint definitions
                        matches = re.findall(r'(\w+_bp)\s*=\s*Blueprint\([\'"]([\w_]+)[\'"]', content)
                        for bp_var, bp_name in matches:
                            blueprints.append({
                                'file': os.path.relpath(file, BASE_DIR),
                                'variable': bp_var,
                                'name': bp_name,
                                'module': f"backend.routes.{os.path.basename(file)[:-3]}"
                            })
                except Exception as e:
                    log_section('blueprints', f"Error reading {file}: {e}", 'error')
        
        # Search vidgenerator/src/routes
        src_routes_dir = os.path.join(BASE_DIR, 'vidgenerator', 'src', 'routes')
        if os.path.exists(src_routes_dir):
            for file in glob.glob(os.path.join(src_routes_dir, '*.py')):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = re.findall(r'(\w+_bp)\s*=\s*Blueprint\([\'"]([\w_]+)[\'"]', content)
                        for bp_var, bp_name in matches:
                            blueprints.append({
                                'file': os.path.relpath(file, BASE_DIR),
                                'variable': bp_var,
                                'name': bp_name,
                                'module': f"vidgenerator.src.routes.{os.path.basename(file)[:-3]}"
                            })
                except Exception as e:
                    log_section('blueprints', f"Error reading {file}: {e}", 'error')
        
        return blueprints

def find_blueprint_registration_file():
    """Find where blueprints are registered"""
    possible_locations = [
        'backend/register_blueprints.py',
        'vidgenerator/src/app.py',
        'src/app.py',
        'wsgi.py'
    ]
    
    for location in possible_locations:
        full_path = os.path.join(BASE_DIR, location)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'register_blueprint' in content or 'register_all_blueprints' in content:
                        return full_path
            except:
                pass
    
    return None

def register_all_blueprints_automatically():
    """Automatically register all found blueprints"""
    log_section('blueprints', "Scanning for blueprints...", 'info')
    
    blueprints = find_all_blueprints()
    log_section('blueprints', f"Found {len(blueprints)} blueprints", 'success')
    
    reg_file = find_blueprint_registration_file()
    
    if not reg_file:
        log_section('blueprints', "No registration file found - creating one", 'warning')
        reg_file = os.path.join(BASE_DIR, 'backend', 'register_blueprints.py')
        
        # Create registration file
        registration_code = '''"""
Automatic Blueprint Registration
Auto-generated by fix_all_loose_ends_master.py
"""
from flask import Flask

def register_all_blueprints(app):
    """Register all blueprints automatically"""
    registered_count = 0
    
'''
        with open(reg_file, 'w', encoding='utf-8') as f:
            f.write(registration_code)
    
    # Read existing registration file
    try:
        with open(reg_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        log_section('blueprints', f"Error reading registration file: {e}", 'error')
        return False
    
    # Check which blueprints are already registered
    registered = []
    for bp in blueprints:
        bp_pattern = bp['variable'] + '|' + bp['name'] + '_bp|from.*' + bp['module'].replace('.', r'\.')
        if re.search(bp_pattern, content, re.IGNORECASE):
            registered.append(bp['name'])
            log_section('blueprints', f"{bp['name']} already registered", 'info')
    
    # Add missing blueprints
    missing = [bp for bp in blueprints if bp['name'] not in registered]
    
    if not missing:
        log_section('blueprints', "All blueprints already registered!", 'success')
        return True
    
    log_section('blueprints', f"Registering {len(missing)} missing blueprints...", 'info')
    
    # Find insertion point (before last except or at end of function)
    insertion_point = None
    
    # Look for end of register_all_blueprints function
    match = re.search(r'(def register_all_blueprints.*?)(\n    return|\n    print|\n    \})', content, re.DOTALL)
    if match:
        insertion_point = match.end(1)
    else:
        # Add at end
        insertion_point = len(content)
    
    # Generate registration code
    registration_code = "\n    # Auto-registered blueprints\n"
    for bp in missing:
        registration_code += f'''    try:
        from {bp['module']} import {bp['variable']}
        app.register_blueprint({bp['variable']})
        registered_count += 1
        print(f"  [OK] Registered {bp['name']} blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import {bp['name']}: {{e}}")
    except Exception as e:
        print(f"  [ERROR] Error registering {bp['name']}: {{e}}")
'''
    
    # Insert code
    new_content = content[:insertion_point] + registration_code + content[insertion_point:]
    
    # Write back
    try:
        with open(reg_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        log_section('blueprints', f"Added {len(missing)} blueprint registrations", 'success')
        CONTROL_REPORT['fixed'].append(f"Registered {len(missing)} blueprints")
        return True
    except Exception as e:
        log_section('blueprints', f"Error writing registration file: {e}", 'error')
        return False

def check_agent_services():
    """Check agent/services sector"""
    log_section('agents', "Checking agent/services sector...", 'info')
    
    services_dir = os.path.join(BASE_DIR, 'backend', 'services')
    agents_found = []
    services_found = []
    
    if os.path.exists(services_dir):
        for file in glob.glob(os.path.join(services_dir, '**/*.py'), recursive=True):
            if '__pycache__' in file or file.endswith('.pyc'):
                continue
            
            rel_path = os.path.relpath(file, BASE_DIR)
            filename = os.path.basename(file)
            
            if 'agent' in filename.lower():
                agents_found.append(rel_path)
            else:
                services_found.append(rel_path)
    
    log_section('agents', f"Found {len(agents_found)} agent files", 'success')
    log_section('agents', f"Found {len(services_found)} service files", 'success')
    
    CONTROL_REPORT['sections']['agents'] = {
        'agents': agents_found,
        'services': services_found,
        'total': len(agents_found) + len(services_found)
    }
    
    return agents_found, services_found

def fix_database():
    """Run database migration"""
    log_section('database', "Running database migration...", 'info')
    
    try:
        # Try to import create_app from different locations
        app = None
        try:
            from src.app import create_app
            app = create_app()
        except ImportError:
            try:
                # Try vidgenerator/src/app
                sys.path.insert(0, os.path.join(BASE_DIR, 'vidgenerator'))
                from src.app import create_app
                app = create_app()
            except ImportError:
                # Use direct database connection
                log_section('database', "Using direct database connection", 'warning')
                import sqlite3
                db_path = os.path.join(BASE_DIR, 'vidgenerator', 'instance', 'database.db')
                if not os.path.exists(db_path):
                    db_path = os.path.join(BASE_DIR, 'instance', 'database.db')
                
                if os.path.exists(db_path):
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Create rewards tables directly
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS rewards (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            reward_type VARCHAR(50) NOT NULL,
                            reward_name VARCHAR(100) NOT NULL,
                            reward_description TEXT,
                            level_required INTEGER,
                            points_required INTEGER,
                            point_type VARCHAR(50),
                            reward_data TEXT,
                            icon VARCHAR(10) DEFAULT '🎁',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS user_rewards (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id VARCHAR(100) NOT NULL,
                            reward_id INTEGER NOT NULL,
                            claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, reward_id)
                        )
                    """)
                    
                    conn.commit()
                    conn.close()
                    log_section('database', "Database tables created via direct connection", 'success')
                    CONTROL_REPORT['fixed'].append("Database tables created")
                    return True
                else:
                    log_section('database', f"Database not found at {db_path}", 'error')
                    return False
        
        if app:
            with app.app_context():
                from scripts.migrate_hunters_game_complete import migrate_complete
                success = migrate_complete()
                if success:
                    log_section('database', "Database migration successful", 'success')
                    CONTROL_REPORT['fixed'].append("Database tables created")
                    return True
                else:
                    log_section('database', "Database migration had issues", 'warning')
                    return False
        else:
            return False
            
    except Exception as e:
        log_section('database', f"Database migration error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"Database migration: {e}")
        return False

def populate_rewards():
    """Populate initial rewards"""
    log_section('database', "Populating initial rewards...", 'info')
    
    try:
        # Try to use app context if available
        try:
            from src.app import create_app
            app = create_app()
            with app.app_context():
                from scripts.populate_initial_rewards import populate_rewards as pop_rewards
                success = pop_rewards()
        except ImportError:
            # Use direct database connection
            import sqlite3
            import json
            db_path = os.path.join(BASE_DIR, 'vidgenerator', 'instance', 'database.db')
            if not os.path.exists(db_path):
                db_path = os.path.join(BASE_DIR, 'instance', 'database.db')
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if rewards already exist
                cursor.execute("SELECT COUNT(*) FROM rewards")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Insert initial rewards (simplified version)
                    rewards = [
                        ('level', 'Level 5 Achievement', 'Reach level 5', 5, None, None, json.dumps({'stat_points': 5}), '🎨'),
                        ('points', '1,000 XP Reward', 'Earn 1,000 XP', None, 1000, 'xp', json.dumps({'stat_points': 2}), '💎'),
                    ]
                    
                    cursor.executemany("""
                        INSERT INTO rewards (reward_type, reward_name, reward_description, level_required, 
                                           points_required, point_type, reward_data, icon)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, rewards)
                    
                    conn.commit()
                    log_section('database', f"Inserted {len(rewards)} initial rewards", 'success')
                else:
                    log_section('database', f"Rewards already exist ({count} found)", 'info')
                
                conn.close()
                CONTROL_REPORT['fixed'].append("Initial rewards populated")
                return True
            else:
                log_section('database', "Database not found for rewards population", 'warning')
                return False
        
        if success:
            log_section('database', "Rewards populated successfully", 'success')
            CONTROL_REPORT['fixed'].append("Initial rewards populated")
            return True
        else:
            log_section('database', "Rewards population had issues", 'warning')
            return False
            
    except Exception as e:
        log_section('database', f"Rewards population error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"Rewards population: {e}")
        return False

def fix_navigation():
    """Add navigation links"""
    log_section('navigation', "Adding navigation links...", 'info')
    
    try:
        from scripts.add_points_link_to_navigation import find_html_files_with_navigation, add_points_link_to_file
        
        files = find_html_files_with_navigation()
        updated = 0
        
        for file_path in files:
            success, reason = add_points_link_to_file(file_path)
            if success:
                updated += 1
        
        if updated > 0:
            log_section('navigation', f"Updated {updated} navigation bars", 'success')
            CONTROL_REPORT['fixed'].append(f"Added points link to {updated} pages")
            return True
        else:
            log_section('navigation', "No navigation updates needed", 'info')
            return True
    except Exception as e:
        log_section('navigation', f"Navigation fix error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"Navigation fix: {e}")
        return False

def verify_endpoints():
    """Verify API endpoints are accessible"""
    log_section('verification', "Verifying endpoints...", 'info')
    
    try:
        from flask import Flask
        from backend.register_blueprints import register_all_blueprints
        
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        register_all_blueprints(app)
        
        # Check hunters_game endpoints
        hunters_endpoints = [
            '/api/game/hunters/level',
            '/api/game/hunters/rewards',
            '/api/game/hunters/rewards/next',
            '/api/game/hunters/rewards/by-points',
            '/api/game/hunters/rewards/claim'
        ]
        
        found = []
        for rule in app.url_map.iter_rules():
            for endpoint in hunters_endpoints:
                if endpoint in rule.rule:
                    found.append(endpoint)
                    break
        
        # Check API scanner endpoints
        scanner_endpoints = [
            '/api/debugger/scanner/scan',
            '/api/debugger/scanner/blueprints',
            '/api/debugger/scanner/missing',
            '/api/debugger/scanner/generate'
        ]
        
        scanner_found = []
        for rule in app.url_map.iter_rules():
            for endpoint in scanner_endpoints:
                if endpoint in rule.rule:
                    scanner_found.append(endpoint)
                    break
        
        # Check monitoring agent endpoints
        monitoring_endpoints = [
            '/api/agent/monitoring/status',
            '/api/agent/monitoring/scan',
            '/api/agent/monitoring/alerts'
        ]
        
        monitoring_found = []
        for rule in app.url_map.iter_rules():
            for endpoint in monitoring_endpoints:
                if endpoint in rule.rule:
                    monitoring_found.append(endpoint)
                    break
        
        if len(found) > 0:
            log_section('verification', f"Found {len(found)}/{len(hunters_endpoints)} hunters endpoints", 'success')
        else:
            log_section('verification', "No hunters endpoints found", 'warning')
        
        if len(scanner_found) > 0:
            log_section('verification', f"Found {len(scanner_found)}/{len(scanner_endpoints)} scanner endpoints", 'success')
            CONTROL_REPORT['fixed'].append(f"API Scanner endpoints verified")
        else:
            log_section('verification', "No scanner endpoints found", 'warning')
        
        if len(monitoring_found) > 0:
            log_section('verification', f"Found {len(monitoring_found)}/{len(monitoring_endpoints)} monitoring agent endpoints", 'success')
            CONTROL_REPORT['fixed'].append(f"API Monitoring Agent endpoints verified")
        else:
            log_section('verification', "No monitoring agent endpoints found", 'warning')
        
        return len(found) > 0 or len(scanner_found) > 0 or len(monitoring_found) > 0
    except Exception as e:
        log_section('verification', f"Verification error: {e}", 'error')
        return False

def run_api_scanner():
    """Run API scanner to find and optionally generate missing methods"""
    log_section('scanner', "Running API scanner...", 'info')
    
    try:
        from backend.services.api_scanner import APIScanner
        
        scanner = APIScanner(BASE_DIR)
        
        # Scan everything
        log_section('scanner', "Scanning codebase...", 'info')
        report = scanner.get_report()
        
        log_section('scanner', f"Found {report['summary']['total_blueprints']} blueprints", 'success')
        log_section('scanner', f"Found {report['summary']['total_routes']} routes", 'success')
        log_section('scanner', f"Found {report['summary']['missing_methods']} missing methods", 'info')
        
        if report['summary']['missing_methods'] > 0:
            log_section('scanner', f"Missing methods detected - use debugger to generate", 'warning')
            CONTROL_REPORT['warnings'].append(f"{report['summary']['missing_methods']} missing API methods detected")
        else:
            log_section('scanner', "No missing methods found!", 'success')
        
        CONTROL_REPORT['sections']['scanner'] = {
            'blueprints': report['summary']['total_blueprints'],
            'routes': report['summary']['total_routes'],
            'services': report['summary']['total_services'],
            'missing_methods': report['summary']['missing_methods']
        }
        
        return True
    except ImportError as e:
        log_section('scanner', f"API scanner not available: {e}", 'warning')
        return False
    except Exception as e:
        log_section('scanner', f"Scanner error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"API Scanner: {e}")
        return False

def setup_monitoring_agent():
    """Setup and initialize API Monitoring Agent"""
    log_section('monitoring', "Setting up API Monitoring Agent...", 'info')
    
    try:
        from backend.services.api_monitoring_agent import api_monitoring_agent
        
        # Get agent status
        status = api_monitoring_agent.get_status()
        
        log_section('monitoring', f"Agent enabled: {status['enabled']}", 'info')
        log_section('monitoring', f"Auto-generate enabled: {status['auto_generate_enabled']}", 'info')
        log_section('monitoring', f"Scan interval: {status['scan_interval_hours']} hours", 'info')
        log_section('monitoring', f"Previous scans: {status['scan_count']}", 'info')
        
        # Perform initial scan if needed
        if api_monitoring_agent.should_scan():
            log_section('monitoring', "Performing initial monitoring scan...", 'info')
            scan_result = api_monitoring_agent.perform_scan()
            if scan_result.get('success'):
                log_section('monitoring', "Initial scan completed", 'success')
                alerts = scan_result.get('alerts', [])
                if alerts:
                    log_section('monitoring', f"Generated {len(alerts)} alerts", 'warning')
                else:
                    log_section('monitoring', "No alerts generated", 'success')
            else:
                log_section('monitoring', f"Initial scan failed: {scan_result.get('error')}", 'error')
        else:
            log_section('monitoring', "Not time to scan yet", 'info')
        
        CONTROL_REPORT['sections']['monitoring'] = {
            'enabled': status['enabled'],
            'auto_generate_enabled': status['auto_generate_enabled'],
            'scan_count': status['scan_count'],
            'alerts_count': status['alerts_count']
        }
        
        CONTROL_REPORT['fixed'].append("API Monitoring Agent initialized")
        return True
    except ImportError as e:
        log_section('monitoring', f"Monitoring agent not available: {e}", 'warning')
        return False
    except Exception as e:
        log_section('monitoring', f"Monitoring agent error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"Monitoring Agent: {e}")
        return False

def run_agent_skills():
    """Run agent skills for comprehensive maintenance"""
    log_section('agent_skills', "Running agent skills...", 'info')
    
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Get all available skills
        skills = master_fix_agent_skills.get_all_skills()
        log_section('agent_skills', f"Found {len(skills)} agent skills", 'success')
        
        # Run key diagnostic skills
        diagnostic_skills = [
            ('check_blueprints', master_fix_agent_skills.skill_check_blueprints),
            ('verify_database', master_fix_agent_skills.skill_verify_database),
            ('check_file_integrity', master_fix_agent_skills.skill_check_file_integrity),
            ('check_navigation', master_fix_agent_skills.skill_check_navigation),
            ('scan_missing_methods', master_fix_agent_skills.skill_scan_missing_methods),
            ('check_service_health', master_fix_agent_skills.skill_check_service_health),
            ('analyze_code_quality', master_fix_agent_skills.skill_analyze_code_quality),
            ('check_dependencies', master_fix_agent_skills.skill_check_dependencies),
            ('verify_endpoints', master_fix_agent_skills.skill_verify_endpoints),
            ('monitor_api_structure', master_fix_agent_skills.skill_monitor_api_structure),
            ('monitor_system_health', master_fix_agent_skills.skill_monitor_system_health),
            ('monitor_performance', master_fix_agent_skills.skill_monitor_performance),
            ('monitor_changes', master_fix_agent_skills.skill_monitor_changes)
        ]
        
        results = {}
        successful = 0
        
        for skill_name, skill_func in diagnostic_skills:
            try:
                log_section('agent_skills', f"Running skill: {skill_name}...", 'info')
                result = skill_func()
                results[skill_name] = result
                if result.get('success', False):
                    successful += 1
                    log_section('agent_skills', f"✅ {skill_name} completed", 'success')
                else:
                    log_section('agent_skills', f"⚠️ {skill_name} had issues", 'warning')
            except Exception as e:
                results[skill_name] = {'success': False, 'error': str(e)}
                log_section('agent_skills', f"❌ {skill_name} failed: {e}", 'error')
        
        # Create maintenance mission
        try:
            mission_result = master_fix_agent_skills.skill_create_mission(
                'Master Fix Maintenance',
                'Automated maintenance and monitoring mission',
                [
                    'Register all blueprints',
                    'Verify database tables',
                    'Check file integrity',
                    'Monitor API structure',
                    'Scan for missing methods'
                ]
            )
            log_section('agent_skills', f"Created mission: {mission_result.get('mission', {}).get('name')}", 'success')
        except Exception as e:
            log_section('agent_skills', f"Mission creation failed: {e}", 'warning')
        
        # Create starter quest
        try:
            quest_result = master_fix_agent_skills.skill_create_quest(
                'System Health Check',
                'Complete comprehensive system health check',
                [
                    {'id': 'run_diagnostic', 'description': 'Run full system diagnostic', 'target': 1},
                    {'id': 'check_blueprints', 'description': 'Check blueprint registration', 'target': 1},
                    {'id': 'verify_database', 'description': 'Verify database integrity', 'target': 1}
                ],
                {'experience': 100, 'achievement': 'System Guardian'}
            )
            log_section('agent_skills', f"Created quest: {quest_result.get('quest', {}).get('name')}", 'success')
        except Exception as e:
            log_section('agent_skills', f"Quest creation failed: {e}", 'warning')
        
        # Run full diagnostic
        try:
            diagnostic = master_fix_agent_skills.skill_run_full_diagnostic()
            health_score = diagnostic.get('health_score', 0)
            log_section('agent_skills', f"Full diagnostic health score: {health_score}%", 'success' if health_score >= 80 else 'warning')
            results['full_diagnostic'] = diagnostic
        except Exception as e:
            log_section('agent_skills', f"Full diagnostic failed: {e}", 'error')
        
        CONTROL_REPORT['sections']['agent_skills'] = {
            'total_skills': len(skills),
            'skills_run': len(diagnostic_skills),
            'successful': successful,
            'results': {k: {'success': v.get('success', False)} for k, v in results.items()}
        }
        
        CONTROL_REPORT['fixed'].append(f"Agent skills executed: {successful}/{len(diagnostic_skills)} successful")
        return True
    except ImportError as e:
        log_section('agent_skills', f"Agent skills not available: {e}", 'warning')
        return False
    except Exception as e:
        log_section('agent_skills', f"Agent skills error: {e}", 'error')
        CONTROL_REPORT['errors'].append(f"Agent Skills: {e}")
        return False

def generate_control_report():
    """Generate control board report"""
    CONTROL_REPORT['status'] = 'complete'
    CONTROL_REPORT['summary'] = {
        'total_fixed': len(CONTROL_REPORT['fixed']),
        'total_errors': len(CONTROL_REPORT['errors']),
        'total_warnings': len(CONTROL_REPORT['warnings']),
        'sections_completed': len([s for s in CONTROL_REPORT['sections'].values() if s])
    }
    
    # Save report
    report_file = os.path.join(BASE_DIR, 'docs', 'CONTROL_BOARD_REPORT.json')
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(CONTROL_REPORT, f, indent=2, default=str)
    
    # Also create human-readable report
    report_md = os.path.join(BASE_DIR, 'docs', 'CONTROL_BOARD_REPORT.md')
    with open(report_md, 'w', encoding='utf-8') as f:
        f.write("# Control Board Report - Loose Ends Fix\n\n")
        f.write(f"**Generated:** {CONTROL_REPORT['timestamp']}\n")
        f.write(f"**Status:** {CONTROL_REPORT['status']}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Fixed:** {CONTROL_REPORT['summary']['total_fixed']}\n")
        f.write(f"- **Errors:** {CONTROL_REPORT['summary']['total_errors']}\n")
        f.write(f"- **Warnings:** {CONTROL_REPORT['summary']['total_warnings']}\n\n")
        
        f.write("## Fixed Issues\n\n")
        for fix in CONTROL_REPORT['fixed']:
            f.write(f"- ✅ {fix}\n")
        
        if CONTROL_REPORT['errors']:
            f.write("\n## Errors\n\n")
            for error in CONTROL_REPORT['errors']:
                f.write(f"- ❌ {error}\n")
        
        if CONTROL_REPORT['warnings']:
            f.write("\n## Warnings\n\n")
            for warning in CONTROL_REPORT['warnings']:
                f.write(f"- ⚠️ {warning}\n")
        
        f.write("\n## Section Details\n\n")
        for section, details in CONTROL_REPORT['sections'].items():
            f.write(f"### {section.title()}\n\n")
            if isinstance(details, list):
                for item in details:
                    status_icon = {'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(item.get('status', 'info'), 'ℹ️')
                    f.write(f"{status_icon} {item.get('message', '')}\n")
            elif isinstance(details, dict):
                for key, value in details.items():
                    f.write(f"- **{key}:** {value}\n")
            f.write("\n")
    
    log_section('report', f"Report saved to {report_file}", 'success')
    log_section('report', f"Markdown report saved to {report_md}", 'success')

def main():
    """Main execution"""
    print("=" * 80)
    print("MASTER LOOSE ENDS FIX - AUTOMATIC REGISTRATION")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Register all blueprints automatically")
    print("  2. Check agent/services sector")
    print("  3. Fix database issues")
    print("  4. Add navigation links")
    print("  5. Verify everything")
    print("  6. Report to control board")
    print()
    
    # Step 1: Register all blueprints
    print("=" * 80)
    print("STEP 1: Registering All Blueprints")
    print("=" * 80)
    register_all_blueprints_automatically()
    
    # Step 2: Check agents/services
    print()
    print("=" * 80)
    print("STEP 2: Checking Agent/Services Sector")
    print("=" * 80)
    agents, services = check_agent_services()
    
    # Step 3: Fix database
    print()
    print("=" * 80)
    print("STEP 3: Fixing Database")
    print("=" * 80)
    fix_database()
    populate_rewards()
    
    # Step 4: Fix navigation
    print()
    print("=" * 80)
    print("STEP 4: Fixing Navigation")
    print("=" * 80)
    fix_navigation()
    
    # Step 5: Run API Scanner
    print()
    print("=" * 80)
    print("STEP 5: Running API Scanner")
    print("=" * 80)
    run_api_scanner()
    
    # Step 6: Setup Monitoring Agent
    print()
    print("=" * 80)
    print("STEP 6: Setting Up API Monitoring Agent")
    print("=" * 80)
    setup_monitoring_agent()
    
    # Step 7: Run Agent Skills
    print()
    print("=" * 80)
    print("STEP 7: Running Agent Skills")
    print("=" * 80)
    run_agent_skills()
    
    # Step 8: Verify
    print()
    print("=" * 80)
    print("STEP 8: Verifying")
    print("=" * 80)
    verify_endpoints()
    
    # Step 9: Generate report
    print()
    print("=" * 80)
    print("STEP 9: Generating Control Board Report")
    print("=" * 80)
    generate_control_report()
    
    # Final summary
    print()
    print("=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"✅ Fixed: {len(CONTROL_REPORT['fixed'])} issues")
    print(f"❌ Errors: {len(CONTROL_REPORT['errors'])}")
    print(f"⚠️  Warnings: {len(CONTROL_REPORT['warnings'])}")
    print()
    print("Report saved to:")
    print(f"  - docs/CONTROL_BOARD_REPORT.json")
    print(f"  - docs/CONTROL_BOARD_REPORT.md")
    print()
    print("=" * 80)
    print("✅ MASTER FIX COMPLETE!")
    print("=" * 80)

if __name__ == '__main__':
    try:
        main()
        sys.exit(0)
    except Exception as e:
        log_section('main', f"Fatal error: {e}", 'error')
        CONTROL_REPORT['status'] = 'error'
        CONTROL_REPORT['errors'].append(f"Fatal: {e}")
        generate_control_report()
        import traceback
        traceback.print_exc()
        sys.exit(1)
