#!/usr/bin/env python3
"""Find all module-level print statements in Python files"""
import os
import re

def find_module_level_prints(file_path):
    """Find print statements at module level (not indented)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        module_prints = []
        in_class = False
        in_function = False
        indent_level = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            
            # Track if we're in a class or function
            if stripped.startswith('class '):
                in_class = True
                indent_level = len(line) - len(stripped)
            elif stripped.startswith('def '):
                in_function = True
                indent_level = len(line) - len(stripped)
            elif line.strip() and not line.strip().startswith('#'):
                current_indent = len(line) - len(stripped)
                # Check if we've left the class/function
                if current_indent <= indent_level and (stripped.startswith('def ') or stripped.startswith('class ')):
                    in_class = False
                    in_function = False
            
            # Check for print statements at module level
            if 'print(' in line and not line.strip().startswith('#'):
                line_indent = len(line) - len(stripped)
                # Module level = not indented (or only minimal indentation for continuation)
                if line_indent == 0 or (line_indent < 4 and not in_class and not in_function):
                    # Make sure it's not in a try/except at module level (those are still module level)
                    module_prints.append((i, line.strip()))
        
        return module_prints
    except Exception as e:
        return []

def scan_directory(directory):
    """Scan directory for Python files with module-level prints"""
    results = {}
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.venv', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                prints = find_module_level_prints(file_path)
                if prints:
                    results[file_path] = prints
    
    return results

# Scan key directories
directories = ['src', 'backend']

print("=" * 70)
print("SCANNING FOR MODULE-LEVEL PRINT STATEMENTS")
print("=" * 70)

all_results = {}
for directory in directories:
    if os.path.exists(directory):
        print(f"\nScanning {directory}/...")
        results = scan_directory(directory)
        all_results.update(results)

if all_results:
    print(f"\n⚠️  Found module-level print statements in {len(all_results)} files:")
    for file_path, prints in all_results.items():
        print(f"\n{file_path}:")
        for line_num, line in prints[:10]:  # Show first 10
            print(f"  Line {line_num}: {line[:80]}")
else:
    print("\n✅ No module-level print statements found")

