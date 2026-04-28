"""
Script to check which backend/services files are actually used
"""
import os
import re
from pathlib import Path
from collections import defaultdict

def find_all_python_files(root_dir):
    """Find all Python files in the codebase"""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.venv', 'venv']]
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def get_service_files(services_dir):
    """Get all service files"""
    service_files = []
    for file in os.listdir(services_dir):
        if file.endswith('.py') and file != '__init__.py':
            service_files.append(file.replace('.py', ''))
    return service_files

def check_imports_in_file(file_path, service_name):
    """Check if a service is imported in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Skip if it's the service file itself
        if service_name in file_path.replace('\\', '/').split('/')[-1]:
            return True
            
        # Check for explicit import patterns only
        patterns = [
            rf'from\s+backend\.services\.{re.escape(service_name)}\s+import',
            rf'from\s+backend\.services\.{re.escape(service_name)}\s+import\s+[\w\s,]+',
            rf'import\s+backend\.services\.{re.escape(service_name)}',
            rf'importlib\.import_module\([\'"]backend\.services\.{re.escape(service_name)}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        return False
    except Exception as e:
        return False

def main():
    project_root = Path(__file__).parent.parent
    services_dir = project_root / 'backend' / 'services'
    
    # Get all service files
    service_files = get_service_files(services_dir)
    print(f"Found {len(service_files)} service files")
    
    # Find all Python files
    python_files = find_all_python_files(project_root)
    print(f"Scanning {len(python_files)} Python files...")
    
    # Check usage
    used_services = set()
    unused_services = []
    
    for service_name in service_files:
        is_used = False
        for py_file in python_files:
            if check_imports_in_file(py_file, service_name):
                is_used = True
                used_services.add(service_name)
                break
        
        if not is_used:
            unused_services.append(service_name)
    
    print(f"\n{'='*60}")
    print(f"USAGE SUMMARY")
    print(f"{'='*60}")
    print(f"Total service files: {len(service_files)}")
    print(f"Used services: {len(used_services)}")
    print(f"Unused services: {len(unused_services)}")
    
    print(f"\n{'='*60}")
    print(f"UNUSED SERVICES (can be deleted):")
    print(f"{'='*60}")
    for service in sorted(unused_services):
        print(f"  - {service}.py")
    
    print(f"\n{'='*60}")
    print(f"USED SERVICES (keep these):")
    print(f"{'='*60}")
    for service in sorted(used_services):
        print(f"  - {service}.py")
    
    # Write to file
    output_file = project_root / 'unused_services.txt'
    with open(output_file, 'w') as f:
        f.write("UNUSED SERVICES (can be deleted):\n")
        f.write("="*60 + "\n")
        for service in sorted(unused_services):
            f.write(f"{service}.py\n")
    
    print(f"\nResults written to: {output_file}")

if __name__ == '__main__':
    main()
