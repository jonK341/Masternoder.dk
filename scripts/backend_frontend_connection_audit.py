#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backend-to-Frontend Connection Audit
Identifies loose ends, missing connections, and routes without UI integration
"""
import os
import re
import sys
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Fix Windows encoding issues
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent.parent
BACKEND_ROUTES_DIR = BASE_DIR / 'backend' / 'routes'
BACKEND_SERVICES_DIR = BASE_DIR / 'backend' / 'services'
FRONTEND_DIR = BASE_DIR / 'vidgenerator'
FRONTEND_JS_DIR = BASE_DIR / 'vidgenerator' / 'static' / 'js'

# Patterns to extract API endpoints
ROUTE_PATTERNS = [
    r'@\w+_bp\.route\([\'"]([^\'"]+)[\'"]',
    r'@app\.route\([\'"]([^\'"]+)[\'"]',
    r'route\([\'"]([^\'"]+)[\'"]',
]

API_CALL_PATTERNS = [
    r'fetch\([\'"`]([^\'"`]+api[^\'"`]+)[\'"`]',
    r'axios\.(get|post|put|delete)\([\'"`]([^\'"`]+api[^\'"`]+)[\'"`]',
    r'\.get\([\'"`]([^\'"`]+api[^\'"`]+)[\'"`]',
    r'\.post\([\'"`]([^\'"`]+api[^\'"`]+)[\'"`]',
    r'url:\s*[\'"`]([^\'"`]+api[^\'"`]+)[\'"`]',
]

def extract_routes_from_file(file_path: Path) -> List[Tuple[str, str, str]]:
    """Extract route definitions from a Python file"""
    routes = []
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        
        # Extract blueprint name
        blueprint_match = re.search(r'(\w+_bp)\s*=\s*Blueprint', content)
        blueprint_name = blueprint_match.group(1) if blueprint_match else 'unknown'
        
        # Extract routes
        for pattern in ROUTE_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                route = match.group(1)
                # Extract method if available
                method_match = re.search(r'methods\s*=\s*\[([^\]]+)\]', content[max(0, match.start()-100):match.end()+100])
                methods = method_match.group(1).strip().strip('"\'').split(',') if method_match else ['GET']
                for method in methods:
                    method = method.strip().strip('"\'').upper()
                    routes.append((route, method, blueprint_name))
    except Exception as e:
        print(f"  [ERROR] Error reading {file_path}: {e}", flush=True)
    return routes

def extract_api_calls_from_file(file_path: Path) -> Set[str]:
    """Extract API calls from a frontend file (HTML/JS)"""
    api_calls = set()
    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
        
        for pattern in API_CALL_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) > 1:
                    api_call = match.group(2) if match.group(2) else match.group(1)
                else:
                    api_call = match.group(1)
                
                # Normalize the API call
                api_call = api_call.strip().strip('"\'').strip('`')
                # Remove BASE_URL or ${BASE_URL} prefix
                api_call = re.sub(r'^.*?(\/api|\/vidgenerator)', r'\1', api_call)
                # Remove query parameters for matching
                api_call = api_call.split('?')[0]
                
                if '/api' in api_call or '/vidgenerator' in api_call:
                    api_calls.add(api_call)
    except Exception as e:
        pass
    return api_calls

def normalize_route(route: str, blueprint_prefix: str = '') -> str:
    """Normalize route path for matching"""
    # Remove leading slashes
    route = route.lstrip('/')
    # Remove vidgenerator prefix if present (will be added by blueprint)
    route = route.replace('/vidgenerator/', '/')
    # Combine with blueprint prefix
    if blueprint_prefix and not route.startswith(blueprint_prefix):
        if blueprint_prefix.startswith('/'):
            route = blueprint_prefix + '/' + route.lstrip('/')
        else:
            route = '/' + blueprint_prefix + '/' + route.lstrip('/')
    # Ensure leading slash
    if not route.startswith('/'):
        route = '/' + route
    return route

def scan_backend_routes() -> Dict[str, List[Tuple[str, str, str]]]:
    """Scan all backend route files"""
    print("Scanning backend routes...")
    all_routes = defaultdict(list)
    
    if not BACKEND_ROUTES_DIR.exists():
        print(f"  [ERROR] Backend routes directory not found: {BACKEND_ROUTES_DIR}")
        return all_routes
    
    route_files = list(BACKEND_ROUTES_DIR.glob('*.py'))
    print(f"  Found {len(route_files)} route files")
    
    for route_file in route_files:
        if route_file.name == '__init__.py':
            continue
        
        routes = extract_routes_from_file(route_file)
        if routes:
            all_routes[route_file.name].extend(routes)
            print(f"  {route_file.name}: {len(routes)} routes")
    
    total_routes = sum(len(routes) for routes in all_routes.values())
    print(f"  Total routes found: {total_routes}\n")
    return all_routes

def scan_frontend_api_calls() -> Set[str]:
    """Scan all frontend files for API calls"""
    print("Scanning frontend API calls...")
    all_api_calls = set()
    
    # Scan HTML files
    if FRONTEND_DIR.exists():
        html_files = list(FRONTEND_DIR.rglob('*.html'))
        print(f"  Found {len(html_files)} HTML files")
        
        for html_file in html_files:
            api_calls = extract_api_calls_from_file(html_file)
            if api_calls:
                all_api_calls.update(api_calls)
                print(f"  {html_file.relative_to(BASE_DIR)}: {len(api_calls)} API calls")
    
    # Scan JS files
    if FRONTEND_JS_DIR.exists():
        js_files = list(FRONTEND_JS_DIR.glob('*.js'))
        print(f"  Found {len(js_files)} JS files")
        
        for js_file in js_files:
            api_calls = extract_api_calls_from_file(js_file)
            if api_calls:
                all_api_calls.update(api_calls)
                print(f"  {js_file.name}: {len(api_calls)} API calls")
    
    print(f"  Total unique API calls found: {len(all_api_calls)}\n")
    return all_api_calls

def find_blueprint_prefixes() -> Dict[str, str]:
    """Find blueprint URL prefixes from register_blueprints.py"""
    prefixes = {}
    register_file = BASE_DIR / 'backend' / 'register_blueprints.py'
    
    if not register_file.exists():
        return prefixes
    
    try:
        content = register_file.read_text(encoding='utf-8', errors='replace')
        
        # Find blueprint registrations with url_prefix
        pattern = r'from\s+backend\.routes\.(\w+)\s+import\s+(\w+_bp).*?app\.register_blueprint\((\w+_bp)(?:,\s*url_prefix=[\'"]([^\'"]+)[\'"])?'
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            route_module = match.group(1)
            blueprint_name = match.group(2)
            url_prefix = match.group(4) if match.group(4) else ''
            prefixes[route_module] = url_prefix
    except Exception as e:
        print(f"  [WARN] Could not extract blueprint prefixes: {e}")
    
    return prefixes

def match_routes_to_calls(backend_routes: Dict[str, List[Tuple[str, str, str]]], 
                          frontend_calls: Set[str],
                          blueprint_prefixes: Dict[str, str]) -> Tuple[Dict, Dict, Dict]:
    """Match backend routes to frontend API calls"""
    print("Matching routes to API calls...")
    
    connected = {}  # Route -> [API calls that match]
    loose_ends = {}  # Route -> (file, method, blueprint)
    missing_frontend = {}  # API call -> [routes that could match]
    
    # Build route map
    route_map = {}
    for route_file, routes in backend_routes.items():
        route_module = route_file.replace('_routes.py', '').replace('.py', '')
        prefix = blueprint_prefixes.get(route_module, '')
        
        for route, method, blueprint in routes:
            # Normalize route
            normalized = normalize_route(route, prefix)
            route_key = f"{method} {normalized}"
            
            # Handle routes with /vidgenerator prefix
            variants = [normalized, normalized.replace('/vidgenerator', ''), '/vidgenerator' + normalized]
            if not normalized.startswith('/vidgenerator'):
                variants.append('/vidgenerator' + normalized)
            
            route_map[route_key] = (route_file, route, method, blueprint, variants)
    
    # Match frontend calls to routes
    for api_call in frontend_calls:
        matched = False
        # Normalize API call
        normalized_call = api_call if api_call.startswith('/') else '/' + api_call
        normalized_call_no_prefix = normalized_call.replace('/vidgenerator', '')
        
        for route_key, (route_file, route, method, blueprint, variants) in route_map.items():
            # Check if API call matches any variant of the route
            if any(variant in normalized_call or normalized_call_no_prefix in variant for variant in variants):
                if route_key not in connected:
                    connected[route_key] = []
                connected[route_key].append(api_call)
                matched = True
                break
        
        if not matched:
            # Try to find potential matches (loose matching)
            potential_matches = []
            for route_key, (route_file, route, method, blueprint, variants) in route_map.items():
                # Check if route path contains API call path or vice versa
                call_path = normalized_call.split('/')[-1] if '/' in normalized_call else normalized_call
                route_path = route.split('/')[-1] if '/' in route else route
                
                if call_path in route_path or route_path in call_path:
                    potential_matches.append((route_key, route_file, route, method))
            
            if potential_matches:
                missing_frontend[api_call] = potential_matches
    
    # Find loose ends (routes with no frontend calls)
    for route_key, (route_file, route, method, blueprint, variants) in route_map.items():
        if route_key not in connected:
            loose_ends[route_key] = (route_file, route, method, blueprint)
    
    print(f"  Connected routes: {len(connected)}")
    print(f"  Loose ends (no frontend): {len(loose_ends)}")
    print(f"  Missing frontend implementations: {len(missing_frontend)}\n")
    
    return connected, loose_ends, missing_frontend

def generate_report(connected: Dict, loose_ends: Dict, missing_frontend: Dict,
                   backend_routes: Dict, frontend_calls: Set) -> str:
    """Generate comprehensive report"""
    report = []
    report.append("# Backend-to-Frontend Connection Audit Report\n")
    report.append(f"**Generated:** {os.popen('date /t' if os.name == 'nt' else 'date').read().strip()}\n")
    report.append("=" * 70 + "\n\n")
    
    # Summary
    report.append("## 📊 Summary\n\n")
    report.append(f"- **Total Backend Routes:** {sum(len(routes) for routes in backend_routes.values())}\n")
    report.append(f"- **Total Frontend API Calls:** {len(frontend_calls)}\n")
    report.append(f"- **Connected Routes:** {len(connected)} ✅\n")
    report.append(f"- **Loose Ends (No Frontend):** {len(loose_ends)} ⚠️\n")
    report.append(f"- **Missing Frontend Implementations:** {len(missing_frontend)} ❌\n\n")
    
    # Connected Routes
    report.append("## ✅ Connected Routes (Backend ↔ Frontend)\n\n")
    report.append(f"**Total:** {len(connected)} routes with frontend integration\n\n")
    
    for route_key, api_calls in sorted(connected.items())[:50]:  # Top 50
        report.append(f"### {route_key}\n")
        report.append(f"- **Frontend Calls:** {len(api_calls)}\n")
        for call in api_calls[:3]:  # Show first 3
            report.append(f"  - `{call}`\n")
        if len(api_calls) > 3:
            report.append(f"  - ... and {len(api_calls) - 3} more\n")
        report.append("\n")
    
    if len(connected) > 50:
        report.append(f"*... and {len(connected) - 50} more connected routes*\n\n")
    
    # Loose Ends
    report.append("## ⚠️ Loose Ends (Backend Routes Without Frontend)\n\n")
    report.append(f"**Total:** {len(loose_ends)} routes without frontend integration\n\n")
    
    # Group by file
    loose_by_file = defaultdict(list)
    for route_key, (route_file, route, method, blueprint) in loose_ends.items():
        loose_by_file[route_file].append((route_key, route, method, blueprint))
    
    for route_file in sorted(loose_by_file.keys())[:20]:  # Top 20 files
        routes_in_file = loose_by_file[route_file]
        report.append(f"### {route_file} ({len(routes_in_file)} routes)\n\n")
        for route_key, route, method, blueprint in routes_in_file[:10]:  # Top 10 per file
            report.append(f"- **{method}** `{route}` (Blueprint: {blueprint})\n")
        if len(routes_in_file) > 10:
            report.append(f"- ... and {len(routes_in_file) - 10} more routes\n")
        report.append("\n")
    
    if len(loose_by_file) > 20:
        report.append(f"*... and {len(loose_by_file) - 20} more files with loose ends*\n\n")
    
    # Missing Frontend
    report.append("## ❌ Missing Frontend Implementations\n\n")
    report.append(f"**Total:** {len(missing_frontend)} frontend API calls without matching backend routes\n\n")
    
    for api_call, potential_matches in sorted(missing_frontend.items())[:30]:  # Top 30
        report.append(f"### `{api_call}`\n")
        report.append(f"- **Potential Matches:** {len(potential_matches)}\n")
        for route_key, route_file, route, method in potential_matches[:3]:
            report.append(f"  - **{method}** `{route}` in `{route_file}`\n")
        if len(potential_matches) > 3:
            report.append(f"  - ... and {len(potential_matches) - 3} more potential matches\n")
        report.append("\n")
    
    if len(missing_frontend) > 30:
        report.append(f"*... and {len(missing_frontend) - 30} more missing frontend implementations*\n\n")
    
    # Statistics by category
    report.append("## 📈 Statistics by Category\n\n")
    
    # Count routes by category
    categories = defaultdict(int)
    for routes in backend_routes.values():
        for route, method, blueprint in routes:
            if 'battle' in route.lower() or 'battle' in blueprint.lower():
                categories['Battle'] += 1
            elif 'shop' in route.lower() or 'shop' in blueprint.lower():
                categories['Shop'] += 1
            elif 'trophy' in route.lower() or 'trophy' in blueprint.lower():
                categories['Trophy'] += 1
            elif 'leaderboard' in route.lower() or 'leaderboard' in blueprint.lower():
                categories['Leaderboard'] += 1
            elif 'point' in route.lower() or 'point' in blueprint.lower():
                categories['Points'] += 1
            elif 'game' in route.lower() or 'game' in blueprint.lower():
                categories['Game'] += 1
            else:
                categories['Other'] += 1
    
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        report.append(f"- **{category}:** {count} routes\n")
    
    report.append("\n")
    report.append("=" * 70 + "\n")
    report.append("**End of Report**\n")
    
    return ''.join(report)

def main():
    """Main audit routine"""
    print("\n" + "=" * 70)
    print("BACKEND-TO-FRONTEND CONNECTION AUDIT".center(70))
    print("=" * 70 + "\n")
    
    # Step 1: Scan backend routes
    backend_routes = scan_backend_routes()
    
    # Step 2: Scan frontend API calls
    frontend_calls = scan_frontend_api_calls()
    
    # Step 3: Find blueprint prefixes
    print("Extracting blueprint prefixes...")
    blueprint_prefixes = find_blueprint_prefixes()
    print(f"  Found {len(blueprint_prefixes)} blueprint prefixes\n")
    
    # Step 4: Match routes to calls
    connected, loose_ends, missing_frontend = match_routes_to_calls(
        backend_routes, frontend_calls, blueprint_prefixes
    )
    
    # Step 5: Generate report
    print("Generating report...")
    report = generate_report(connected, loose_ends, missing_frontend, backend_routes, frontend_calls)
    
    # Save report
    report_file = BASE_DIR / 'BACKEND_FRONTEND_CONNECTION_AUDIT.md'
    report_file.write_text(report, encoding='utf-8')
    print(f"  Report saved to: {report_file}\n")
    
    # Save JSON data for further analysis
    json_file = BASE_DIR / 'backend_frontend_connections.json'
    json_data = {
        'connected': {k: list(v) for k, v in connected.items()},
        'loose_ends': {k: list(v) for k, v in loose_ends.items()},
        'missing_frontend': {k: [list(m) for m in v] for k, v in missing_frontend.items()},
        'statistics': {
            'total_routes': sum(len(routes) for routes in backend_routes.values()),
            'total_api_calls': len(frontend_calls),
            'connected_count': len(connected),
            'loose_ends_count': len(loose_ends),
            'missing_frontend_count': len(missing_frontend)
        }
    }
    json_file.write_text(json.dumps(json_data, indent=2), encoding='utf-8')
    print(f"  JSON data saved to: {json_file}\n")
    
    # Print summary
    print("=" * 70)
    print("AUDIT COMPLETE".center(70))
    print("=" * 70 + "\n")
    print(f"✅ Connected Routes: {len(connected)}")
    print(f"⚠️  Loose Ends: {len(loose_ends)}")
    print(f"❌ Missing Frontend: {len(missing_frontend)}\n")
    print(f"📄 Report: {report_file}")
    print(f"📊 JSON Data: {json_file}\n")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
