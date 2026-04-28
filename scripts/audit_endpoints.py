"""Audit missing_endpoints_routes.py - show function names, paths, and body size."""
import re

with open('backend/routes/missing_endpoints_routes.py', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')

# Find all route definitions (double-route pattern)
i = 0
routes = []
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('@missing_endpoints_bp.route(') or line.startswith("@missing_endpoints_bp.route('"):
        # Collect all decorators
        path = re.search(r"route\(['\"]([^'\"]+)['\"]", line)
        if path:
            # Find the def line
            for j in range(i, min(i+8, len(lines))):
                dm = re.match(r'\s*def (\w+)\(', lines[j])
                if dm:
                    # Count body lines (until next blank or decorator)
                    body_start = j + 1
                    body_len = 0
                    for k in range(body_start, min(body_start+30, len(lines))):
                        bline = lines[k].strip()
                        if bline and not bline.startswith('@') and not bline.startswith('def '):
                            body_len += 1
                        elif k > body_start and (bline.startswith('@') or bline.startswith('def ')):
                            break
                    routes.append({
                        'line': i+1,
                        'path': path.group(1),
                        'fn': dm.group(1),
                        'body_lines': body_len,
                    })
                    break
    i += 1

# Deduplicate by function name (same fn often has 2 routes)
seen = set()
unique = []
for r in routes:
    if r['fn'] not in seen:
        seen.add(r['fn'])
        unique.append(r)

print(f"Unique functions: {len(unique)}")
print(f"\n{'Lines':>6}  {'Function':<45}  Path")
print("-" * 90)

# Group by body size - smallest first = most stubby
for r in sorted(unique, key=lambda x: x['body_lines'])[:40]:
    print(f"{r['body_lines']:>6}  {r['fn']:<45}  {r['path']}")
