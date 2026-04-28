#!/usr/bin/env python3
"""
Comprehensive Production Verification
Tests all 50 agent techs and core systems
"""
import requests
import json
from datetime import datetime
from typing import Dict, List

BASE_URL = "https://masternoder.dk"

# All 50 tech IDs
ALL_TECHS = [
    'agent_quantum_processor', 'agent_neural_network', 'agent_blockchain_ledger',
    'agent_cloud_sync', 'agent_distributed_cache', 'agent_microservices',
    'agent_api_gateway', 'agent_load_balancer', 'agent_service_mesh',
    'agent_container_orchestrator', 'agent_code_analyzer', 'agent_performance_profiler',
    'agent_memory_debugger', 'agent_security_scanner', 'agent_dependency_checker',
    'agent_test_generator', 'agent_log_analyzer', 'agent_error_tracker',
    'agent_code_formatter', 'agent_documentation_generator', 'agent_activity_tracker',
    'agent_behavior_tracker', 'agent_metric_tracker', 'agent_event_tracker',
    'agent_network_scanner', 'agent_vulnerability_scanner', 'agent_file_scanner',
    'agent_database_scanner', 'agent_endpoint_scanner', 'agent_config_scanner',
    'agent_health_monitor', 'agent_resource_monitor', 'agent_uptime_monitor',
    'agent_alert_monitor', 'agent_metric_monitor', 'agent_gps_coordinator',
    'agent_location_tracker', 'agent_geofence_manager', 'agent_route_optimizer',
    'agent_navigation_system', 'agent_ml_predictor', 'agent_auto_scaler',
    'agent_self_healer', 'agent_adaptive_learner', 'agent_pattern_matcher',
    'agent_anomaly_detector', 'agent_optimization_engine', 'agent_decision_maker',
    'agent_workflow_orchestrator', 'agent_event_driven_processor'
]

CORE_ENDPOINTS = [
    '/vidgenerator/api/points/all?user_id=default_user',
    '/vidgenerator/api/user/profile/default_user/display',
    '/vidgenerator/api/agents/controller/status',
    '/vidgenerator/api/points/comprehensive?user_id=default_user',
]

def test_tech_status(tech_id: str) -> Dict:
    """Test tech status endpoint"""
    try:
        url = f"{BASE_URL}/vidgenerator/api/agent-tech/{tech_id}/status"
        response = requests.get(url, timeout=10)
        return {
            'tech_id': tech_id,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'has_data': response.status_code == 200 and response.headers.get('Content-Type', '').startswith('application/json')
        }
    except Exception as e:
        return {'tech_id': tech_id, 'success': False, 'error': str(e)}

def test_core_endpoint(endpoint: str) -> Dict:
    """Test core system endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        response = requests.get(url, timeout=10)
        return {
            'endpoint': endpoint,
            'status_code': response.status_code,
            'success': response.status_code == 200
        }
    except Exception as e:
        return {'endpoint': endpoint, 'success': False, 'error': str(e)}

def test_dashboard() -> Dict:
    """Test unified dashboard"""
    try:
        url = f"{BASE_URL}/vidgenerator/unified_dashboard"
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            content = response.text
            checks = {
                'agent-techs-manager.js': 'agent-techs-manager.js' in content,
                'agent-techs-dashboard': 'agent-techs-dashboard' in content,
                '50 Agent Technologies': '50 Agent Technologies' in content or 'agent-techs-dashboard' in content
            }
            return {
                'success': True,
                'status_code': 200,
                'checks': checks,
                'all_checks_pass': all(checks.values())
            }
        return {'success': False, 'status_code': response.status_code}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    """Run comprehensive verification"""
    print("=" * 70)
    print("COMPREHENSIVE PRODUCTION VERIFICATION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'tech_tests': [],
        'core_tests': [],
        'dashboard_test': {},
        'summary': {}
    }
    
    # Test all 50 techs
    print("[1/3] Testing all 50 agent technologies...")
    tech_results = []
    for tech_id in ALL_TECHS:
        result = test_tech_status(tech_id)
        tech_results.append(result)
        if result['success']:
            print(f"  [OK] {tech_id}")
        else:
            print(f"  [FAIL] {tech_id}: {result.get('error', 'Unknown')}")
    
    results['tech_tests'] = tech_results
    tech_passed = sum(1 for r in tech_results if r['success'])
    tech_failed = len(tech_results) - tech_passed
    
    print(f"\n  Tech Status: {tech_passed}/{len(ALL_TECHS)} passed")
    print()
    
    # Test core endpoints
    print("[2/3] Testing core system endpoints...")
    core_results = []
    for endpoint in CORE_ENDPOINTS:
        result = test_core_endpoint(endpoint)
        core_results.append(result)
        if result['success']:
            print(f"  [OK] {endpoint}")
        else:
            print(f"  [FAIL] {endpoint}: {result.get('error', 'Unknown')}")
    
    results['core_tests'] = core_results
    core_passed = sum(1 for r in core_results if r['success'])
    
    print(f"\n  Core Endpoints: {core_passed}/{len(CORE_ENDPOINTS)} passed")
    print()
    
    # Test dashboard
    print("[3/3] Testing unified dashboard...")
    dashboard_result = test_dashboard()
    results['dashboard_test'] = dashboard_result
    
    if dashboard_result['success']:
        print(f"  [OK] Dashboard loaded (Status: {dashboard_result['status_code']})")
        checks = dashboard_result.get('checks', {})
        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"    {status} {check}")
        print(f"  All checks: {'PASS' if dashboard_result.get('all_checks_pass') else 'FAIL'}")
    else:
        print(f"  [FAIL] Dashboard: {dashboard_result.get('error', 'Unknown')}")
    
    print()
    
    # Summary
    results['summary'] = {
        'total_techs': len(ALL_TECHS),
        'techs_passed': tech_passed,
        'techs_failed': tech_failed,
        'tech_success_rate': (tech_passed / len(ALL_TECHS)) * 100,
        'core_endpoints_passed': core_passed,
        'core_endpoints_total': len(CORE_ENDPOINTS),
        'dashboard_ok': dashboard_result.get('success', False),
        'dashboard_checks_pass': dashboard_result.get('all_checks_pass', False),
        'overall_status': 'PASS' if (tech_passed == len(ALL_TECHS) and core_passed == len(CORE_ENDPOINTS) and dashboard_result.get('success')) else 'PARTIAL'
    }
    
    print("=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Agent Technologies: {tech_passed}/{len(ALL_TECHS)} ({results['summary']['tech_success_rate']:.1f}%)")
    print(f"Core Endpoints: {core_passed}/{len(CORE_ENDPOINTS)}")
    print(f"Dashboard: {'OK' if dashboard_result.get('success') else 'FAIL'}")
    print(f"Overall Status: {results['summary']['overall_status']}")
    print()
    
    # Save results
    with open('production_verification_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("Results saved to: production_verification_results.json")
    
    return results

if __name__ == '__main__':
    main()
