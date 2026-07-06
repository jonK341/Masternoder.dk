#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unlock Death Portal Technologies
Unlocks all available technologies for both portals
"""
import sys
import os
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.services.death_portal_manager import death_portal_manager

def unlock_all_tech():
    """Unlock all available technologies for both portals"""
    print("Unlocking Death Portal Technologies...")
    print("=" * 80)
    
    # Get available tech
    tech_result = death_portal_manager.get_available_portal_tech()
    if not tech_result.get('success'):
        print("❌ Failed to get available tech")
        return
    
    available_tech = tech_result.get('tech', {})
    print(f"📋 Found {len(available_tech)} technologies\n")
    
    # Portal 1 - Can unlock all tech (at Common Mind site)
    print("Portal 1 (Alpha) - Unlocking technologies...")
    print("-" * 80)
    
    for tech_name, tech_info in available_tech.items():
        # Skip Common Mind Integration for Portal 2 (requires specific location)
        if tech_name == 'common_mind_integration':
            print(f"  [SKIP] Skipping {tech_info['name']} (Portal 1 only)")
            continue
        
        result = death_portal_manager.unlock_portal_tech('portal_1', tech_name)
        if result.get('success'):
            print(f"  [OK] Unlocked: {tech_info['name']}")
            print(f"     Power: +{tech_info['power_boost']} | Force: +{tech_info['force_boost']}")
        else:
            error = result.get('error', 'Unknown error')
            if 'already unlocked' in error.lower():
                print(f"  [INFO] Already unlocked: {tech_info['name']}")
            else:
                print(f"  [WARN] Failed: {tech_info['name']} - {error}")
    
    # Unlock Common Mind Integration for Portal 1 (requires Common Mind site)
    print("\n  Unlocking Common Mind Integration for Portal 1...")
    result = death_portal_manager.unlock_portal_tech('portal_1', 'common_mind_integration')
    if result.get('success'):
        print(f"  [OK] Unlocked: Common Mind Integration")
        print(f"     Power: +50 | Force: +45")
    else:
        error = result.get('error', 'Unknown error')
        if 'already unlocked' in error.lower():
            print(f"  [INFO] Already unlocked: Common Mind Integration")
        else:
            print(f"  [WARN] Failed: Common Mind Integration - {error}")
    
    # Portal 2 - Can unlock most tech (except Common Mind Integration)
    print("\nPortal 2 (Beta) - Unlocking technologies...")
    print("-" * 80)
    
    for tech_name, tech_info in available_tech.items():
        # Skip Common Mind Integration (requires Portal 1 location)
        if tech_name == 'common_mind_integration':
            print(f"  [SKIP] Skipping {tech_info['name']} (Portal 1 only - requires Common Mind site)")
            continue
        
        result = death_portal_manager.unlock_portal_tech('portal_2', tech_name)
        if result.get('success'):
            print(f"  [OK] Unlocked: {tech_info['name']}")
            print(f"     Power: +{tech_info['power_boost']} | Force: +{tech_info['force_boost']}")
        else:
            error = result.get('error', 'Unknown error')
            if 'already unlocked' in error.lower():
                print(f"  [INFO] Already unlocked: {tech_info['name']}")
            else:
                print(f"  [WARN] Failed: {tech_info['name']} - {error}")
    
    # Get final status
    print("\n" + "=" * 80)
    print("📊 Final Status:")
    print("-" * 80)
    
    for portal_id in ['portal_1', 'portal_2']:
        portal_result = death_portal_manager.get_portal(portal_id)
        if portal_result.get('success'):
            portal = portal_result['portal']
            print(f"\n{portal['name']}:")
            print(f"  Tech Level: {portal['tech_integration']['tech_level']}")
            print(f"  Unlocked Tech: {len(portal['tech_integration']['unlocked_tech'])}")
            for tech_name in portal['tech_integration']['unlocked_tech']:
                tech = available_tech.get(tech_name, {})
                if tech:
                    print(f"    - {tech['name']} (+{tech['power_boost']} power, +{tech['force_boost']} force)")
    
    print("\n[SUCCESS] Technology unlocking complete!")

if __name__ == "__main__":
    unlock_all_tech()

