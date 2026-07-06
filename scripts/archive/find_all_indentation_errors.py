#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find all indentation errors in battle.py
"""
import re

with open('backend/routes/battle.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=" * 80)
print("FINDING ALL INDENTATION ERRORS")
print("=" * 80)
print()

errors = []
for i, line in enumerate(lines, 1):
    # Check for if statement followed by unindented code
    if re.match(r'^\s+if\s+.*:\s*$', line):
        # Next line should be indented more
        if i < len(lines):
            next_line = lines[i]
            # Check if next line starts with same or less indentation
            current_indent = len(line) - len(line.lstrip())
            next_indent = len(next_line) - len(next_line.lstrip())
            
            # If next line is not indented more, it's an error
            if next_line.strip() and not next_line.strip().startswith('#') and next_line.strip() != '':
                if next_indent <= current_indent and not next_line.strip().startswith('else') and not next_line.strip().startswith('elif'):
                    errors.append((i, line.strip(), next_line.strip()))

if errors:
    print(f"Found {len(errors)} potential indentation errors:")
    print()
    for line_num, if_line, next_line in errors[:20]:  # Show first 20
        print(f"Line {line_num}:")
        print(f"  {if_line}")
        print(f"  {next_line}  <-- NOT INDENTED!")
        print()
else:
    print("No obvious indentation errors found")
    print()

# Also try to compile and show actual errors
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'backend/routes/battle.py'], 
                        capture_output=True, text=True)
if result.returncode != 0:
    print("=" * 80)
    print("ACTUAL COMPILATION ERRORS:")
    print("=" * 80)
    print(result.stderr)
