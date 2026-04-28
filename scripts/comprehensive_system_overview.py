#!/usr/bin/env python3
"""
Comprehensive System Overview
Analyzes the entire system for issues, loose ends, and potential problems
"""
import os
import json
import requests
from datetime import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "https://masternoder.dk"

def analyze_system():
    """Comprehensive system analysis"""
    print("=" * 70)
    print("COMPREHENSIVE SYSTEM OVERVIEW")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    issues = defaultdict(list)
    warnings = defaultdict(list)
    recommendations = []
    
    # 1. Check API Endpoints
    print("[1/8] Analyzing API Endpoints...")
    api_endpoints = [
        '/vidgenerator/api/points/all?user_id=default_user',
        '/vidgenerator/api/stats/summary?user_id=default_user',
        '/vidgenerator/api/game/stats?user_id=default_user',
        '/vidgenerator/api/battle/stats?user_id=default_user',
        '/vidgenerator/api/user/profile/default_user/display',
        '/vidgenerator/api/user/profile/default_user/stats',
        '/vidgenerator/api/game/achievements?user_id=default_user',
        '/vidgenerator/api/shop/currency?user_id=default_user',
    ]
    
    endpoint_status = {}
    for endpoint in api_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            status = response.status_code
            endpoint_status[endpoint] = status
            
            if status == 404:
                issues['Missing Endpoints'].append(endpoint)
            elif status >= 500:
                issues['Server Errors'].append(f"{endpoint} ({status})")
            elif status == 200:
                try:
                    data = response.json()
                    if not data.get('success', True):
                        warnings['API Warnings'].append(f"{endpoint}: {data.get('error', 'Unknown error')}")
                except:
                    pass
        except Exception as e:
            issues['Connection Errors'].append(f"{endpoint}: {str(e)[:50]}")
    
    print(f"  Tested {len(api_endpoints)} endpoints")
    print(f"  OK: {sum(1 for s in endpoint_status.values() if s == 200)}")
    print(f"  Issues: {sum(1 for s in endpoint_status.values() if s != 200)}")
    print()
    
    # 2. Check Frontend Files
    print("[2/8] Analyzing Frontend Files...")
    frontend_files = [
        'vidgenerator/profile/index.html',
        'vidgenerator/dashboard/index.html',
        'vidgenerator/unified_dashboard/index.html',
        'vidgenerator/static/js/backend-connector.js',
        'vidgenerator/static/js/agent-behavior-widget.js',
        'vidgenerator/static/js/unified-point-counters.js',
    ]
    
    missing_files = []
    for file_path in frontend_files:
        full_path = os.path.join(BASE_DIR, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
            issues['Missing Files'].append(file_path)
    
    if missing_files:
        print(f"  [WARN] {len(missing_files)} files missing")
    else:
        print(f"  [OK] All {len(frontend_files)} frontend files exist")
    print()
    
    # 3. Check Backend Routes
    print("[3/8] Analyzing Backend Routes...")
    route_files = [
        'backend/routes/user_profile_routes.py',
        'backend/routes/points_routes.py',
        'backend/routes/missing_endpoints_routes.py',
        'backend/routes/dashboard_page_routes.py',
        'backend/services/user_onboarding.py',
        'backend/services/unified_points_database.py',
    ]
    
    missing_routes = []
    for file_path in route_files:
        full_path = os.path.join(BASE_DIR, file_path)
        if not os.path.exists(full_path):
            missing_routes.append(file_path)
            issues['Missing Backend Files'].append(file_path)
    
    if missing_routes:
        print(f"  [WARN] {len(missing_routes)} route files missing")
    else:
        print(f"  [OK] All {len(route_files)} route files exist")
    print()
    
    # 4. Check for Common Issues
    print("[4/8] Checking for Common Issues...")
    
    # Check for default_user issues
    if 'default_user' in str(endpoint_status):
        warnings['User Management'].append("default_user is still being used - consider migrating to proper user IDs")
    
    # Check for hardcoded values
    import re
    backend_connector = os.path.join(BASE_DIR, 'vidgenerator/static/js/backend-connector.js')
    if os.path.exists(backend_connector):
        with open(backend_connector, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'default_user' in content:
                warnings['Hardcoded Values'].append("backend-connector.js contains 'default_user'")
    
    # Check for TODO/FIXME comments
    todo_count = 0
    for root, dirs, files in os.walk(os.path.join(BASE_DIR, 'backend')):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        todo_count += content.count('TODO') + content.count('FIXME') + content.count('XXX')
                except:
                    pass
    
    if todo_count > 0:
        warnings['Code Quality'].append(f"Found {todo_count} TODO/FIXME comments in backend code")
    
    print(f"  [INFO] Found {len(warnings)} warning categories")
    print()
    
    # 5. Check Database/Storage
    print("[5/8] Checking Database/Storage...")
    storage_paths = [
        'logs/user_profiles',
        'logs/unified_points',
        'logs/user_identifiers',
        'logs/onboarding_progress',
    ]
    
    missing_storage = []
    for path in storage_paths:
        full_path = os.path.join(BASE_DIR, path)
        if not os.path.exists(full_path):
            missing_storage.append(path)
            warnings['Storage'].append(f"Storage directory missing: {path}")
    
    if missing_storage:
        print(f"  [WARN] {len(missing_storage)} storage directories missing")
    else:
        print(f"  [OK] All storage directories exist")
    print()
    
    # 6. Check Configuration
    print("[6/8] Checking Configuration...")
    config_files = [
        'backend/register_blueprints.py',
        '178_systems_config.json',
    ]
    
    config_issues = []
    for file_path in config_files:
        full_path = os.path.join(BASE_DIR, file_path)
        if not os.path.exists(full_path):
            config_issues.append(file_path)
            issues['Configuration'].append(f"Missing config file: {file_path}")
    
    if config_issues:
        print(f"  [WARN] {len(config_issues)} config files missing")
    else:
        print(f"  [OK] Configuration files exist")
    print()
    
    # 7. Check for Error Patterns
    print("[7/8] Analyzing Error Patterns...")
    
    # Check for common error patterns in diagnostics
    diagnostics_file = os.path.join(os.path.expanduser('~'), 'Downloads', 'eh-lab-diagnostics-1768997131610.json')
    if os.path.exists(diagnostics_file):
        try:
            with open(diagnostics_file, 'r', encoding='utf-8') as f:
                diag = json.load(f)
            
            # Analyze network events
            network_events = diag.get('networkEvents', [])
            error_404 = sum(1 for e in network_events if e.get('status') == 404)
            error_500 = sum(1 for e in network_events if e.get('status') >= 500)
            total_requests = len(network_events)
            
            if error_404 > 0:
                issues['404 Errors'].append(f"{error_404}/{total_requests} requests returned 404")
            if error_500 > 0:
                issues['500 Errors'].append(f"{error_500}/{total_requests} requests returned 500+")
            
            # Analyze console errors
            console_errors = diag.get('consoleErrors', [])
            if console_errors:
                unique_errors = set()
                for err in console_errors:
                    if 'args' in err and len(err['args']) > 1:
                        error_msg = str(err['args'][1])[:100]
                        unique_errors.add(error_msg)
                
                if unique_errors:
                    issues['Console Errors'].append(f"{len(unique_errors)} unique console errors found")
                    for err in list(unique_errors)[:5]:
                        warnings['Console Errors'].append(err[:80])
            
            print(f"  [INFO] Analyzed diagnostics: {total_requests} requests, {error_404} 404s, {error_500} 500s")
        except Exception as e:
            warnings['Analysis'].append(f"Could not analyze diagnostics: {e}")
    else:
        warnings['Analysis'].append("Diagnostics file not found - skipping error pattern analysis")
    
    print()
    
    # 8. Generate Recommendations
    print("[8/8] Generating Recommendations...")
    
    if issues.get('Missing Endpoints'):
        recommendations.append("Create missing API endpoints or add fallback handlers")
    
    if issues.get('404 Errors'):
        recommendations.append("Fix 404 errors by implementing missing routes or updating frontend calls")
    
    if issues.get('Server Errors'):
        recommendations.append("Investigate and fix server errors (500+) in API endpoints")
    
    if warnings.get('User Management'):
        recommendations.append("Implement proper user identification system (IP, fingerprint, email-based)")
    
    if warnings.get('Hardcoded Values'):
        recommendations.append("Replace hardcoded 'default_user' with dynamic user identification")
    
    if issues.get('Console Errors'):
        recommendations.append("Fix JavaScript console errors to improve user experience")
    
    recommendations.append("Add comprehensive error logging and monitoring")
    recommendations.append("Implement rate limiting for API endpoints")
    recommendations.append("Add API response caching where appropriate")
    recommendations.append("Create automated testing for critical endpoints")
    
    print(f"  Generated {len(recommendations)} recommendations")
    print()
    
    # Summary Report
    print("=" * 70)
    print("SYSTEM OVERVIEW SUMMARY")
    print("=" * 70)
    print()
    
    print("ISSUES FOUND:")
    total_issues = sum(len(v) for v in issues.values())
    if total_issues > 0:
        for category, items in issues.items():
            if items:
                print(f"  [{category}] ({len(items)} issues)")
                for item in items[:5]:
                    print(f"    - {item}")
                if len(items) > 5:
                    print(f"    ... and {len(items) - 5} more")
        print()
    else:
        print("  [OK] No critical issues found!")
        print()
    
    print("WARNINGS:")
    total_warnings = sum(len(v) for v in warnings.values())
    if total_warnings > 0:
        for category, items in warnings.items():
            if items:
                print(f"  [{category}] ({len(items)} warnings)")
                for item in items[:3]:
                    print(f"    - {item}")
                if len(items) > 3:
                    print(f"    ... and {len(items) - 3} more")
        print()
    else:
        print("  [OK] No warnings!")
        print()
    
    print("RECOMMENDATIONS:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    print()
    
    # Save report
    report = {
        'timestamp': datetime.now().isoformat(),
        'issues': dict(issues),
        'warnings': dict(warnings),
        'recommendations': recommendations,
        'endpoint_status': endpoint_status,
        'summary': {
            'total_issues': total_issues,
            'total_warnings': total_warnings,
            'total_recommendations': len(recommendations)
        }
    }
    
    report_file = os.path.join(BASE_DIR, 'system_overview_report.json')
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"Full report saved to: {report_file}")
    print()
    print("=" * 70)
    print("OVERVIEW COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    analyze_system()
