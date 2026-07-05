#!/usr/bin/env python3
"""
Start Calculator Automation
Starts the automatic calculation system
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.services.calculator_automation import calculator_automation
    
    print("=" * 80)
    print("STARTING CALCULATOR AUTOMATION")
    print("=" * 80)
    print()
    
    # Start automation
    result = calculator_automation.start()
    
    if result.get('success'):
        print("[OK] Calculator automation started successfully!")
        print(f"   Interval: {result.get('interval_seconds', 300)} seconds (5 minutes)")
        print(f"   Message: {result.get('message', '')}")
        print()
        print("The calculator will now automatically:")
        print("  - Calculate stats for all users every 5 minutes")
        print("  - Monitor behavior patterns")
        print("  - Save data to encrypted JSON")
        print("  - Track changes and anomalies")
        print()
        print("To stop, use: POST /api/calculator-automation/stop")
        print("To check status: GET /api/calculator-automation/status")
        print()
        
        # Get initial status
        status = calculator_automation.get_status()
        print(f"Current Status:")
        print(f"  Running: {status.get('is_running', False)}")
        print(f"  Interval: {status.get('interval_seconds', 0)} seconds")
        print(f"  Users calculated: {status.get('users_calculated', 0)}")
        print()
        
    else:
        print(f"[ERROR] Failed to start calculator automation: {result.get('error', 'Unknown error')}")
        sys.exit(1)
        
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    print("Make sure all dependencies are installed:")
    print("  - backend.services.calculator_automation")
    print("  - backend.services.advanced_intelligent_calculator")
    print("  - backend.services.behavior_pattern_monitor")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Error starting calculator automation: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 80)
print("CALCULATOR AUTOMATION STARTED")
print("=" * 80)

