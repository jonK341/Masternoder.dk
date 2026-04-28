#!/usr/bin/env python3
"""
Deploy Profile Fixes
Deploys all profile page fixes and enhancements
"""
import os
import sys
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def deploy_profile_fixes():
    """Deploy all profile fixes"""
    print("=" * 70)
    print("DEPLOYING PROFILE FIXES")
    print("=" * 70)
    
    files_to_deploy = [
        ('vidgenerator/profile/index.html', 'vidgenerator/profile/index.html'),
        ('backend/services/user_profile.py', 'backend/services/user_profile.py'),
        ('scripts/fix_and_update_all_user_profiles.py', 'scripts/fix_and_update_all_user_profiles.py'),
    ]
    
    deployed = []
    failed = []
    
    for src, dst in files_to_deploy:
        src_path = os.path.join(BASE_DIR, src)
        dst_path = os.path.join(BASE_DIR, dst)
        
        if os.path.exists(src_path):
            try:
                shutil.copy2(src_path, dst_path)
                deployed.append(src)
                print(f"  [OK] {src}")
            except Exception as e:
                failed.append(f"{src}: {e}")
                print(f"  [FAIL] {src}: {e}")
        else:
            failed.append(f"{src}: File not found")
            print(f"  [FAIL] {src}: File not found")
    
    print("\n" + "=" * 70)
    print("DEPLOYMENT SUMMARY")
    print("=" * 70)
    print(f"Deployed: {len(deployed)}")
    print(f"Failed: {len(failed)}")
    
    if failed:
        print("\nFailures:")
        for f in failed:
            print(f"  - {f}")
    
    print("\n✓ Profile fixes deployed")
    return len(failed) == 0

if __name__ == '__main__':
    success = deploy_profile_fixes()
    sys.exit(0 if success else 1)
