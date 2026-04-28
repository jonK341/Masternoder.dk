#!/usr/bin/env python3
"""
Continuous Test Runner
Keep running tests and database operations continuously
"""
import subprocess
import time
import sys
from datetime import datetime

def run_test(script_name):
    """Run a test script"""
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def main():
    """Run tests continuously"""
    print("=" * 70)
    print("CONTINUOUS TEST RUNNER")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Database Operations", "scripts/run_database_operations.py"),
        ("Backend APIs", "scripts/test_all_backend_apis.py"),
        ("Functions & Tables", "scripts/check_and_fix_functions_tables.py"),
    ]
    
    iteration = 0
    while True:
        iteration += 1
        print(f"\n{'='*70}")
        print(f"ITERATION {iteration} - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}\n")
        
        for test_name, script in tests:
            print(f"Running {test_name}...")
            success, stdout, stderr = run_test(script)
            
            if success:
                print(f"  ✓ {test_name} passed")
                # Show summary lines
                for line in stdout.split('\n'):
                    if any(keyword in line for keyword in ['Success rate', 'Summary', 'COMPLETE', 'records']):
                        print(f"    {line.strip()}")
            else:
                print(f"  ✗ {test_name} failed")
                if stderr:
                    print(f"    Error: {stderr[:100]}")
        
        print(f"\nWaiting 30 seconds before next iteration...")
        time.sleep(30)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        sys.exit(0)
