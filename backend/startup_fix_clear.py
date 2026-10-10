"""
Startup Fix and Clear Script
Runs fix/clear endpoints on server startup
"""
import requests
import time
import os
from typing import Dict, Any

# Configuration
API_BASE = os.getenv('API_BASE', 'http://localhost:5000/vidgenerator/api')
MAX_RETRIES = 3
RETRY_DELAY = 2


def run_startup_fixes():
    """Run fix and clear endpoints on startup"""
    print("=" * 70)
    print("Startup Fix and Clear Script")
    print("=" * 70)
    
    fixes_applied = []
    errors_fixed = []
    
    # Wait for server to be ready
    print("\n[1/4] Waiting for server to be ready...")
    for i in range(MAX_RETRIES):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=5)
            if response.status_code == 200:
                print("  [OK] Server is ready")
                break
        except:
            if i < MAX_RETRIES - 1:
                print(f"  [WAIT] Retrying in {RETRY_DELAY} seconds... ({i+1}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                print("  [WARN] Server not ready, continuing anyway...")
    
    # Fix error hash tracking
    print("\n[2/4] Fixing error hash tracking issues...")
    try:
        response = requests.post(
            f"{API_BASE}/error-hash/fix",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                fixes = data.get('fixes_applied', [])
                fixes_applied.extend(fixes)
                errors_fixed.append({
                    'type': 'error_hash_fix',
                    'fixes': len(fixes),
                    'remaining': data.get('remaining_errors', 0)
                })
                print(f"  [OK] Applied {len(fixes)} fixes")
                print(f"  [INFO] Remaining errors: {data.get('remaining_errors', 0)}")
            else:
                print(f"  [WARN] Fix returned success=False: {data.get('error', 'Unknown')}")
        else:
            print(f"  [WARN] Fix endpoint returned status {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] Failed to fix error hash tracking: {e}")
    
    # Clear old errors (older than 7 days)
    print("\n[3/4] Clearing old errors (7+ days)...")
    try:
        response = requests.post(
            f"{API_BASE}/error-hash/clear",
            json={'days': 7},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                cleared = data.get('cleared_count', 0)
                print(f"  [OK] Cleared {cleared} old errors")
                errors_fixed.append({
                    'type': 'clear_old_errors',
                    'cleared': cleared
                })
            else:
                print(f"  [WARN] Clear returned success=False")
        else:
            print(f"  [WARN] Clear endpoint returned status {response.status_code}")
    except Exception as e:
        print(f"  [ERROR] Failed to clear old errors: {e}")
    
    # Summary
    print("\n[4/4] Startup fixes complete!")
    print("=" * 70)
    print(f"Total fixes applied: {len(fixes_applied)}")
    print(f"Errors fixed: {len(errors_fixed)}")
    print("=" * 70)
    
    return {
        'success': True,
        'fixes_applied': fixes_applied,
        'errors_fixed': errors_fixed
    }


if __name__ == '__main__':
    run_startup_fixes()

