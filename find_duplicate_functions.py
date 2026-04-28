#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find all duplicate function names in battle.py
"""
import re
from collections import Counter

with open('backend/routes/battle.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all function definitions
functions = []
for i, line in enumerate(lines, 1):
    match = re.match(r'^def (\w+)\(', line)
    if match:
        func_name = match.group(1)
        functions.append((i, func_name))

# Count occurrences
func_counts = Counter([name for _, name in functions])

# Find duplicates
duplicates = {name: count for name, count in func_counts.items() if count > 1}

if duplicates:
    print("=" * 80)
    print("DUPLICATE FUNCTION NAMES FOUND")
    print("=" * 80)
    print()
    for func_name, count in duplicates.items():
        print(f"{func_name}: {count} occurrences")
        for line_num, name in functions:
            if name == func_name:
                print(f"  Line {line_num}")
        print()
else:
    print("No duplicate function names found!")
