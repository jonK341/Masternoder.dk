#!/usr/bin/env python3
"""
Find Duplicate Blueprint Registrations
Checks for blueprints registered multiple times
"""
import re
from collections import defaultdict

def find_duplicates():
    """Find duplicate blueprint registrations"""
    print("="*80)
    print("FINDING DUPLICATE BLUEPRINT REGISTRATIONS")
    print("="*80)
    print()
    
    with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all blueprint registrations
    blueprint_pattern = r"from\s+backend\.routes\.(\w+)\s+import\s+(\w+_bp)"
    imports = re.findall(blueprint_pattern, content)
    
    # Find all register_blueprint calls
    register_pattern = r"app\.register_blueprint\((\w+_bp)\)"
    registrations = re.findall(register_pattern, content)
    
    # Count occurrences
    blueprint_counts = defaultdict(int)
    for bp_name in registrations:
        blueprint_counts[bp_name] += 1
    
    # Find duplicates
    duplicates = {bp: count for bp, count in blueprint_counts.items() if count > 1}
    
    if duplicates:
        print("DUPLICATE BLUEPRINT REGISTRATIONS FOUND:")
        print("-" * 80)
        for bp_name, count in duplicates.items():
            print(f"  {bp_name}: registered {count} times")
        print()
        return duplicates
    else:
        print("  [OK] No duplicate blueprint registrations found")
        print()
        return {}

if __name__ == "__main__":
    find_duplicates()
