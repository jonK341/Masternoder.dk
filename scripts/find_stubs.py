import re, sys

with open('backend/routes/missing_endpoints_routes.py', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print(f"Total lines: {len(lines)}")

# Find route + function pairs
route_pattern = re.compile(r"@missing_endpoints_bp\.route\('([^']+)'")
def_pattern   = re.compile(r"^def (\w+)\(")

routes = []
for i, line in enumerate(lines):
    m = route_pattern.search(line)
    if m:
        for j in range(i, min(i+5, len(lines))):
            dm = def_pattern.match(lines[j].strip())
            if dm:
                routes.append((i+1, m.group(1), dm.group(1)))
                break

print(f"Routes found: {len(routes)}")

# Identify stubs - look for functions that return immediately with simple stub data
stub_keywords = ['stub', 'placeholder', 'TODO', 'not implemented', 'coming soon', '"status": "ok"', '"data": []', '"items": []']
stub_routes = []
for linenum, path, fname in routes:
    # Get function body (next ~10 lines)
    body = '\n'.join(lines[linenum:linenum+15])
    is_stub = any(kw.lower() in body.lower() for kw in stub_keywords)
    if is_stub:
        stub_routes.append((linenum, path, fname))

print(f"\nStub routes (likely): {len(stub_routes)}")
for ln, path, fn in stub_routes[:30]:
    print(f"  L{ln:4d}  {fn:40s}  {path}")
