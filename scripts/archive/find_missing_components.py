#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find Missing Components and Lost Tech
"""
import os
import re
from pathlib import Path

def find_missing_components():
    """Find missing components and lost tech"""
    
    print("=" * 80)
    print("MISSING COMPONENTS & LOST TECH ANALYSIS")
    print("=" * 80)
    print()
    
    # Check for lost tech services
    lost_tech_services = [
        'time_disorder_device.py',
        'advanced_battle_tech.py',
        'creative_timemashine_500plus.py',
        'technology_intelligence_battle.py',
        'future_tech_integration_service.py'
    ]
    
    print("[1] Checking Lost Tech Services...")
    found_services = []
    missing_services = []
    
    for service_file in lost_tech_services:
        service_path = f"backend/services/{service_file}"
        if os.path.exists(service_path):
            print(f"  [OK] {service_file}")
            found_services.append(service_file)
        else:
            print(f"  [MISSING] {service_file}")
            missing_services.append(service_file)
    
    print()
    
    # Check for missing routes
    print("[2] Checking Missing Routes...")
    route_files = [
        'time_disorder_battle_routes.py',
        'advanced_battle_tech_routes.py'
    ]
    
    found_routes = []
    missing_routes = []
    
    for route_file in route_files:
        route_path = f"backend/routes/{route_file}"
        if os.path.exists(route_path):
            print(f"  [OK] {route_file}")
            found_routes.append(route_file)
        else:
            print(f"  [MISSING] {route_file}")
            missing_routes.append(route_file)
    
    print()
    
    # Check for missing JavaScript functions
    print("[3] Checking JavaScript Functions in Battle Page...")
    battle_html = "vidgenerator/battle/index.html"
    
    if os.path.exists(battle_html):
        with open(battle_html, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all function calls
        function_calls = re.findall(r'(\w+)\(', content)
        unique_calls = set(function_calls)
        
        # Find all function definitions
        function_defs = re.findall(r'function\s+(\w+)\s*\(', content)
        async_defs = re.findall(r'async\s+function\s+(\w+)\s*\(', content)
        all_defs = set(function_defs + async_defs)
        
        # Find potentially missing functions
        potentially_missing = []
        for call in unique_calls:
            if call not in all_defs and call not in ['console', 'document', 'window', 'fetch', 'JSON', 'parseInt', 'parseFloat', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval', 'Math', 'Date', 'Array', 'Object', 'String', 'Number', 'Boolean', 'Promise', 'Error', 'localStorage', 'sessionStorage', 'location', 'history', 'navigator', 'alert', 'confirm', 'prompt', 'encodeURIComponent', 'decodeURIComponent', 'btoa', 'atob']:
                if len(call) > 3 and not call.startswith('_'):  # Filter out very short names and private
                    potentially_missing.append(call)
        
        print(f"  Total function calls: {len(unique_calls)}")
        print(f"  Total function definitions: {len(all_defs)}")
        print(f"  Potentially missing functions: {len(potentially_missing)}")
        
        if potentially_missing:
            print()
            print("  Potentially Missing Functions:")
            for func in sorted(potentially_missing)[:20]:  # Show first 20
                print(f"    - {func}()")
    
    print()
    
    # Check for "coming soon" messages
    print("[4] Checking 'Coming Soon' Messages...")
    if os.path.exists(battle_html):
        with open(battle_html, 'r', encoding='utf-8') as f:
            content = f.read()
        
        coming_soon_count = content.lower().count('coming soon')
        print(f"  Found {coming_soon_count} 'coming soon' messages")
        
        # Find specific instances
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'coming soon' in line.lower():
                print(f"    Line {i}: {line.strip()[:80]}")
    
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Found Services: {len(found_services)}/{len(lost_tech_services)}")
    print(f"Missing Services: {len(missing_services)}")
    print(f"Found Routes: {len(found_routes)}/{len(route_files)}")
    print(f"Missing Routes: {len(missing_routes)}")
    print()
    
    return {
        'found_services': found_services,
        'missing_services': missing_services,
        'found_routes': found_routes,
        'missing_routes': missing_routes
    }

if __name__ == "__main__":
    find_missing_components()
