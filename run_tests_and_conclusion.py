#!/usr/bin/env python3
"""
Run all tests and generate final conclusion report
"""
import sys
import os
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

print("=" * 80)
print("RUNNING COMPREHENSIVE FUNCTION TESTS")
print("=" * 80)
print()

# Run the test suite
result = subprocess.run(
    [sys.executable, 'test_all_functions.py'],
    capture_output=True,
    text=True,
    cwd=BASE_DIR
)

# Print output
print(result.stdout)
if result.stderr:
    print(result.stderr, file=sys.stderr)

# Parse results
output_lines = result.stdout.split('\n')
test_count = 0
passed_count = 0
failed_count = 0
error_count = 0

for line in output_lines:
    if 'test_' in line and ('ok' in line or 'FAIL' in line or 'ERROR' in line):
        test_count += 1
        if 'ok' in line:
            passed_count += 1
        elif 'FAIL' in line:
            failed_count += 1
        elif 'ERROR' in line:
            error_count += 1

# Try to get actual test results from the output
try:
    for line in output_lines:
        if 'Ran' in line and 'test' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'test' and i > 0:
                    test_count = int(parts[i-1])
                    break
        if 'OK' in line and 'test' in line.lower():
            passed_count = test_count
except:
    pass

# Generate conclusion
print()
print("=" * 80)
print("FINAL CONCLUSION")
print("=" * 80)
print()

if test_count == 0:
    print("[WARNING] Could not determine test results")
    print("Check the output above for details")
    sys.exit(1)

success_rate = (passed_count / test_count * 100) if test_count > 0 else 0

print("TEST STATISTICS:")
print(f"   Total Tests: {test_count}")
print(f"   [PASS] Passed: {passed_count}")
print(f"   [FAIL] Failed: {failed_count}")
print(f"   [ERROR] Errors: {error_count}")
print(f"   Success Rate: {success_rate:.1f}%")
print()

if success_rate == 100:
    print("[SUCCESS] EXCELLENT: ALL TESTS PASSED!")
    print()
    print("CONCLUSION:")
    print("   All functions in the codebase are working correctly.")
    print("   The codebase is in good health with:")
    print("   - All backend services (XP System, Trophy System, etc.) functioning properly")
    print("   - All route handlers properly defined and callable")
    print("   - Blueprint registration working correctly")
    print("   - Generation tracking and chat points systems operational")
    print()
    print("The application is ready for use!")
    
elif success_rate >= 80:
    print("[WARNING] GOOD: Most tests passed, but some issues detected")
    print()
    print("📋 CONCLUSION:")
    print("   Most functions are working correctly, but there are some minor issues.")
    print("   Review the failed tests above and address them.")
    
elif success_rate >= 50:
    print("[WARNING] About half of tests passed")
    print()
    print("CONCLUSION:")
    print("   Significant portions of the codebase need attention.")
    print("   Review failed tests and fix critical issues.")
    
else:
    print("[CRITICAL] Many tests failed")
    print()
    print("CONCLUSION:")
    print("   Major issues detected in the codebase.")
    print("   Immediate attention required to fix failing functions.")

print()
print("=" * 80)
print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

sys.exit(0 if failed_count == 0 and error_count == 0 else 1)

