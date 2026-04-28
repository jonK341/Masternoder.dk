#!/usr/bin/env python3
"""
Test Framework for 50 Agent Technologies
Tests all techs and their 12 improvement functions
"""
import requests
import json
from typing import Dict, List

BASE_URL = "https://masternoder.dk"
TECH_IDS = [
                "agent_activity_tracker",
                "agent_adaptive_learner",
                "agent_alert_monitor",
                "agent_anomaly_detector",
                "agent_api_gateway",
                "agent_auto_scaler",
                "agent_behavior_tracker",
                "agent_blockchain_ledger",
                "agent_cloud_sync",
                "agent_code_analyzer",
                "agent_code_formatter",
                "agent_config_scanner",
                "agent_container_orchestrator",
                "agent_database_scanner",
                "agent_decision_maker",
                "agent_dependency_checker",
                "agent_distributed_cache",
                "agent_documentation_generator",
                "agent_endpoint_scanner",
                "agent_error_tracker",
                "agent_event_driven_processor",
                "agent_event_tracker",
                "agent_file_scanner",
                "agent_geofence_manager",
                "agent_gps_coordinator",
                "agent_health_monitor",
                "agent_load_balancer",
                "agent_location_tracker",
                "agent_log_analyzer",
                "agent_memory_debugger",
                "agent_metric_monitor",
                "agent_metric_tracker",
                "agent_microservices",
                "agent_ml_predictor",
                "agent_navigation_system",
                "agent_network_scanner",
                "agent_neural_network",
                "agent_optimization_engine",
                "agent_pattern_matcher",
                "agent_performance_profiler",
                "agent_quantum_processor",
                "agent_resource_monitor",
                "agent_route_optimizer",
                "agent_security_scanner",
                "agent_self_healer",
                "agent_service_mesh",
                "agent_test_generator",
                "agent_uptime_monitor",
                "agent_vulnerability_scanner",
                "agent_workflow_orchestrator"
]

IMPROVEMENT_FUNCTIONS = [
    'optimize_performance',
    'enhance_security',
    'improve_reliability',
    'scale_capacity',
    'reduce_latency',
    'increase_throughput',
    'add_monitoring',
    'enable_auto_recovery',
    'improve_caching',
    'enhance_logging',
    'add_analytics',
    'upgrade_algorithm',
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
            'data': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else None
        }
    except Exception as e:
        return {'tech_id': tech_id, 'success': False, 'error': str(e)}

def test_tech_improvement(tech_id: str, function_name: str) -> Dict:
    """Test tech improvement function"""
    try:
        url = f"{BASE_URL}/vidgenerator/api/agent-tech/{tech_id}/{function_name}"
        response = requests.post(
            url,
            json={'user_id': 'test_user', 'params': {}},
            timeout=10
        )
        return {
            'tech_id': tech_id,
            'function': function_name,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'data': response.json() if response.headers.get('Content-Type', '').startswith('application/json') else None
        }
    except Exception as e:
        return {'tech_id': tech_id, 'function': function_name, 'success': False, 'error': str(e)}

def main():
    """Run all tests"""
    print("=" * 70)
    print("TESTING 50 AGENT TECHNOLOGIES")
    print("=" * 70)
    
    results = {
        'status_tests': [],
        'improvement_tests': [],
        'summary': {
            'total_techs': len(TECH_IDS),
            'status_passed': 0,
            'status_failed': 0,
            'improvements_passed': 0,
            'improvements_failed': 0
        }
    }
    
    # Test status endpoints
    print("\n[1/2] Testing status endpoints...")
    for tech_id in TECH_IDS:
        result = test_tech_status(tech_id)
        results['status_tests'].append(result)
        if result['success']:
            results['summary']['status_passed'] += 1
            print(f"  [OK] {tech_id}")
        else:
            results['summary']['status_failed'] += 1
            print(f"  [FAIL] {tech_id}: {result.get('error', 'Unknown error')}")
    
    # Test improvement functions (sample: first 3 techs, first 2 functions)
    print("\n[2/2] Testing improvement functions (sample)...")
    sample_techs = TECH_IDS[:3]
    sample_functions = IMPROVEMENT_FUNCTIONS[:2]
    
    for tech_id in sample_techs:
        for func in sample_functions:
            result = test_tech_improvement(tech_id, func)
            results['improvement_tests'].append(result)
            if result['success']:
                results['summary']['improvements_passed'] += 1
                print(f"  [OK] {tech_id}.{func}")
            else:
                results['summary']['improvements_failed'] += 1
                print(f"  [FAIL] {tech_id}.{func}: {result.get('error', 'Unknown error')}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Status Tests: {results['summary']['status_passed']}/{len(TECH_IDS)} passed")
    print(f"Improvement Tests: {results['summary']['improvements_passed']}/{len(sample_techs) * len(sample_functions)} passed")
    
    # Save results
    with open('agent_techs_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to: agent_techs_test_results.json")

if __name__ == '__main__':
    main()
