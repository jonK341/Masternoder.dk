"""
Better script to find truly unused service files
Checks for actual imports, not just file name matches
"""
import os
import re
from pathlib import Path
from collections import defaultdict

def get_all_service_files(services_dir):
    """Get all service files"""
    return [f.replace('.py', '') for f in os.listdir(services_dir) 
            if f.endswith('.py') and f != '__init__.py']

def find_imports_in_codebase(root_dir, service_name):
    """Find actual imports of a service"""
    imports_found = []
    
    # Patterns to match
    patterns = [
        rf'from\s+backend\.services\.{re.escape(service_name)}\s+import',
        rf'import\s+backend\.services\.{re.escape(service_name)}',
        rf'importlib\.import_module\([\'"]backend\.services\.{re.escape(service_name)}',
    ]
    
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', '.venv', 'venv', 'scripts']):
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            
            # Skip the service file itself
            if service_name in file_path.replace('\\', '/').split('/')[-1]:
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
    services_dir = project_root / 'backend' / 'services'
    
    service_files = get_all_service_files(services_dir)
    print(f"Analyzing {len(service_files)} service files...\n")
    
    unused = []
    used = []
    
    for service_name in sorted(service_files):
        imports = find_imports_in_codebase(project_root, service_name)
        
        if imports:
            used.append((service_name, len(imports)))
        else:
            unused.append(service_name)
    
    print("="*70)
    print(f"RESULTS")
    print("="*70)
    print(f"Total services: {len(service_files)}")
    print(f"Used services: {len(used)}")
    print(f"Unused services: {len(unused)}")
    print()
    
    if unused:
        print("="*70)
        print("UNUSED SERVICES (can be deleted):")
        print("="*70)
        for service in unused:
            print(f"  backend/services/{service}.py")
        
        # Write deletion script
        delete_script = project_root / 'delete_unused_services.py'
        with open(delete_script, 'w') as f:
            f.write("#!/usr/bin/env python\n")
            f.write('"""Script to delete unused service files"""\n')
            f.write("import os\n")
            f.write("from pathlib import Path\n\n")
            f.write("project_root = Path(__file__).parent\n")
            f.write("services_dir = project_root / 'backend' / 'services'\n\n")
            f.write("unused_files = [\n")
            for service in unused:
                f.write(f"    '{service}.py',\n")
            f.write("]\n\n")
            f.write("deleted = []\n")
            f.write("for filename in unused_files:\n")
            f.write("    filepath = services_dir / filename\n")
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
        print("No unused services found!")
    
    print("\n" + "="*70)
    print("USED SERVICES (most frequently used):")
    print("="*70)
    for service_name, count in sorted(used, key=lambda x: x[1], reverse=True)[:20]:
        print(f"  {service_name}.py ({count} imports)")

if __name__ == '__main__':
    main()
