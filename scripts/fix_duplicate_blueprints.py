#!/usr/bin/env python3
"""
Fix Duplicate Blueprint Registrations
Removes duplicate blueprint registrations from register_blueprints.py
"""
import re

def fix_duplicates():
    """Fix duplicate blueprint registrations"""
    print("="*80)
    print("FIXING DUPLICATE BLUEPRINT REGISTRATIONS")
    print("="*80)
    print()
    
    with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track seen blueprints
    seen_blueprints = set()
    lines = content.split('\n')
    new_lines = []
    removed_count = 0
    
    for i, line in enumerate(lines):
        # Check for register_blueprint calls
        match = re.search(r'app\.register_blueprint\((\w+_bp)\)', line)
        if match:
            bp_name = match.group(1)
            if bp_name in seen_blueprints:
                # Skip duplicate
                print(f"  [REMOVED] Duplicate: {bp_name} (line {i+1})")
                removed_count += 1
                # Also remove the import if it's right before
                if i > 0 and 'from backend.routes' in lines[i-1] and bp_name.replace('_bp', '') in lines[i-1]:
                    print(f"  [REMOVED] Duplicate import (line {i})")
                    continue
                continue
            else:
                seen_blueprints.add(bp_name)
        
        new_lines.append(line)
    
    # Write back
    with open('backend/register_blueprints.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print()
    print("="*80)
    print("DUPLICATE FIX COMPLETE")
    print("="*80)
    print(f"Removed: {removed_count} duplicate registrations")
    print()

if __name__ == "__main__":
    fix_duplicates()
