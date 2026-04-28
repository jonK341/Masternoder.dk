#!/usr/bin/env python3
"""
Register Expanded Triggers
Registers all additional triggers for 178 point systems
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.expanded_triggers_system import expanded_triggers_system

def main():
    """Register all expanded triggers"""
    print("=" * 80)
    print("REGISTERING EXPANDED TRIGGERS")
    print("=" * 80)
    
    try:
        count = expanded_triggers_system.register_all_triggers()
        print(f"\n✅ Successfully registered {count} additional triggers")
        print(f"📊 Total triggers now: {count + 100} (100 base + {count} expanded)")
        print("\n" + "=" * 80)
        return 0
    except Exception as e:
        print(f"\n❌ Error registering triggers: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
