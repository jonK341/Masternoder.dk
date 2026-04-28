#!/usr/bin/env python3
"""Remove all @bp.route('/vidgenerator/api/...') decorator lines from backend/routes."""
import re
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
routes_dir = os.path.join(BASE, "backend", "routes")

# Match a line that is only a route decorator for /vidgenerator/api/
pattern = re.compile(r'^\s*@\w+.*\.route\s*\(\s*["\']/vidgenerator/api/')

removed_total = 0
for f in os.listdir(routes_dir):
    if not f.endswith(".py"):
        continue
    path = os.path.join(routes_dir, f)
    with open(path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    new_lines = [L for L in lines if not pattern.match(L)]
    removed = len(lines) - len(new_lines)
    if removed:
        with open(path, "w", encoding="utf-8") as file:
            file.writelines(new_lines)
        print("Removed", removed, "from", path)
        removed_total += removed
print("Done. Total lines removed:", removed_total)
