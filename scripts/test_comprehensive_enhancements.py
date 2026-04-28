#!/usr/bin/env python3
"""
Test Comprehensive Enhancements
Tests all new features: Master Dashboard, AI Intelligence, Movie Generation, etc.
"""
import os
import sys
import requests
import json
import codecs
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_master_dashboard_top10():
    """Test Master Dashboard Top10 endpoint"""
    print("=" * 80)
    print("TESTING: Master Dashboard Top10")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/master-dashboard/top10"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                top10 = data.get('top10', [])
                print(f"[OK] Top10 endpoint working - {len(top10)} items")
                for item in top10[:5]:  # Show first 5
                    print(f"  - #{item.get('rank')}: {item.get('title')} = {item.get('value')}")
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_master_dashboard_stats():
    """Test Master Dashboard stats endpoint"""
    print("=" * 80)
    print("TESTING: Master Dashboard Stats")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/master-dashboard/stats"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('stats', {})
                print(f"[OK] Stats endpoint working")
                print(f"  - System: {stats.get('system', {})}")
                print(f"  - Agents: {stats.get('agents', {})}")
                print(f"  - Points: {stats.get('points', {})}")
                print(f"  - Migration: {stats.get('migration', {})}")
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_ai_intelligence_top10():
    """Test AI Intelligence Top10 endpoint"""
    print("=" * 80)
    print("TESTING: AI Intelligence Top10")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/ai-intelligence/top10"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                top10 = data.get('top10', [])
                print(f"[OK] Top10 endpoint working - {len(top10)} items")
                for item in top10[:5]:  # Show first 5
                    print(f"  - #{item.get('rank')}: {item.get('title')} = {item.get('value')}")
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_ai_intelligence_stats():
    """Test AI Intelligence stats endpoint"""
    print("=" * 80)
    print("TESTING: AI Intelligence Stats")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/ai-intelligence/stats"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('stats', {})
                print(f"[OK] Stats endpoint working")
                print(f"  - Intelligence: {stats.get('intelligence', {})}")
                print(f"  - Predictions: {stats.get('predictions', {})}")
                print(f"  - Insights: {stats.get('insights', {})}")
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_movie_generation():
    """Test The End War movie generation"""
    print("=" * 80)
    print("TESTING: The End War Movie Generation")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/movie/the-end-war/generate"
        response = requests.post(url, json={}, timeout=10, verify=False)
        
        if response.status_code == 202:
            data = response.json()
            if data.get('success'):
                job_id = data.get('job_id')
                print(f"[OK] Movie generation started - Job ID: {job_id}")
                print(f"  - Status: {data.get('status')}")
                print(f"  - Points: {data.get('points_awarded', {})}")
                
                # Test status endpoint
                status_url = f"{API_BASE}/movie/the-end-war/status/{job_id}"
                status_response = requests.get(status_url, timeout=10, verify=False)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"  - Status check: {status_data.get('status')}")
                    print(f"  - Progress: {status_data.get('progress', 0)}%")
                
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_error_migration_stats():
    """Test error migration statistics"""
    print("=" * 80)
    print("TESTING: Error Migration Statistics")
    print("=" * 80)
    
    try:
        url = f"{API_BASE}/errors/tasks/stats"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                stats = data.get('stats', {})
                print(f"[OK] Migration stats working")
                print(f"  - Total Files: {stats.get('total_files', 0)}")
                print(f"  - Files Migrated: {stats.get('files_migrated', 0)}")
                print(f"  - Files Remaining: {stats.get('files_remaining', 0)}")
                print(f"  - Progress: {stats.get('migration_percent', 0)}%")
                
                tasks_available = stats.get('tasks_available', {})
                print(f"  - Tasks Available: {tasks_available.get('total', 0)}")
                return True
            else:
                print(f"[FAIL] API returned success=False: {data.get('error')}")
                return False
        else:
            print(f"[FAIL] HTTP {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


def test_agent_skills():
    """Test that new agent skills are accessible"""
    print("=" * 80)
    print("TESTING: Agent Skills")
    print("=" * 80)
    
    try:
        from backend.services.agent_skillset import AgentSkillset
        skillset = AgentSkillset()
        
        # Check for new agents
        agents = skillset.skillsets.get('agents', {})
        
        new_agents = ['error_migration_agent', 'master_dashboard_agent', 'ai_intelligence_agent']
        found_agents = []
        
        for agent_id in new_agents:
            if agent_id in agents:
                agent = agents[agent_id]
                skills = agent.get('skills', [])
                found_agents.append(agent_id)
                print(f"[OK] {agent_id} found with {len(skills)} skills")
                print(f"  - Skills: {', '.join(skills[:5])}...")
            else:
                print(f"[WARN] {agent_id} not found in skillsets")
        
        if len(found_agents) == len(new_agents):
            print(f"[OK] All new agents found!")
            return True
        else:
            print(f"[WARN] Only {len(found_agents)}/{len(new_agents)} agents found")
            return False
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print()
    print("=" * 80)
    print("COMPREHENSIVE ENHANCEMENTS TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'master_dashboard_top10': test_master_dashboard_top10(),
        'master_dashboard_stats': test_master_dashboard_stats(),
        'ai_intelligence_top10': test_ai_intelligence_top10(),
        'ai_intelligence_stats': test_ai_intelligence_stats(),
        'movie_generation': test_movie_generation(),
        'error_migration_stats': test_error_migration_stats(),
        'agent_skills': test_agent_skills()
    }
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print("[WARN] Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
