"""
Script to find unused route files in backend/routes
Checks for actual imports in register_blueprints.py and other files
"""
import os
import re
from pathlib import Path
from collections import defaultdict

def get_all_route_files(routes_dir):
    """Get all route files"""
    route_files = []
    for file in os.listdir(routes_dir):
        if file.endswith('.py') and file != '__init__.py':
            route_files.append(file.replace('.py', ''))
    return route_files

def find_imports_in_codebase(root_dir, route_name):
    """Find actual imports of a route"""
    imports_found = []
    
    # Patterns to match
    patterns = [
        rf'from\s+backend\.routes\.{re.escape(route_name)}\s+import',
        rf'import\s+backend\.routes\.{re.escape(route_name)}',
        rf'importlib\.import_module\([\'"]backend\.routes\.{re.escape(route_name)}',
        # Also check for blueprint name patterns
        rf'{re.escape(route_name)}_bp',
        rf'{re.escape(route_name)}_routes_bp',
        rf'{re.escape(route_name)}_page_bp',
    ]
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', '.venv', 'venv', 'scripts']):
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            
            # Skip the route file itself
            if route_name in file_path.replace('\\', '/').split('/')[-1]:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    for pattern in patterns:
                        if re.search(pattern, content):
                            imports_found.append(file_path)
                            break
            except:
                pass
    
    return imports_found

def main():
    project_root = Path(__file__).parent.parent
    routes_dir = project_root / 'backend' / 'routes'
    
    route_files = get_all_route_files(routes_dir)
    print(f"Analyzing {len(route_files)} route files...\n")
    
    unused = []
    used = []
    
    for route_name in sorted(route_files):
        imports = find_imports_in_codebase(project_root, route_name)
        
        if imports:
            used.append((route_name, len(imports)))
        else:
            unused.append(route_name)
    
    print("="*70)
    print(f"RESULTS")
    print("="*70)
    print(f"Total route files: {len(route_files)}")
    print(f"Used route files: {len(used)}")
    print(f"Unused route files: {len(unused)}")
    print()
    
    if unused:
        print("="*70)
        print("UNUSED ROUTE FILES (can be deleted):")
        print("="*70)
        for route in unused:
            print(f"  backend/routes/{route}.py")
        
        # Write deletion script
        delete_script = project_root / 'delete_unused_routes.py'
        with open(delete_script, 'w') as f:
            f.write("#!/usr/bin/env python\n")
            f.write('"""Script to delete unused route files"""\n')
            f.write("import os\n")
            f.write("from pathlib import Path\n\n")
            f.write("project_root = Path(__file__).parent\n")
            f.write("routes_dir = project_root / 'backend' / 'routes'\n\n")
            f.write("unused_files = [\n")
            for route in unused:
                f.write(f"    '{route}.py',\n")
            f.write("]\n\n")
            f.write("deleted = []\n")
            f.write("for filename in unused_files:\n")
            f.write("    filepath = routes_dir / filename\n")
            f.write("    if filepath.exists():\n")
            f.write("        os.remove(filepath)\n")
            f.write("        deleted.append(filename)\n")
            f.write("        print(f'Deleted: {filename}')\n")
            f.write("    else:\n")
            f.write("        print(f'Not found: {filename}')\n")
            f.write("\n")
            f.write("print(f'\\nDeleted {len(deleted)} files')\n")
        
        print(f"\nDeletion script created: {delete_script}")
    else:
        print("No unused route files found!")
    
    print("\n" + "="*70)
    print("USED ROUTE FILES (most frequently used):")
    print("="*70)
    for route_name, count in sorted(used, key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {route_name}.py ({count} imports)")

if __name__ == '__main__':
    main()
