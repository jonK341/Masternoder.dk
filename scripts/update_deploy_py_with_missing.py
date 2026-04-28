#!/usr/bin/env python3
"""
Update deploy.py with Missing Files
Adds critical missing services and routes to deploy.py
"""
import os
import re

def get_all_python_files(directory):
    """Get all Python files in directory"""
    files = []
    if not os.path.exists(directory):
        return files
    for root, dirs, filenames in os.walk(directory):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for filename in filenames:
            if filename.endswith('.py') and not filename.endswith('.pyc'):
                rel_path = os.path.relpath(os.path.join(root, filename))
                files.append(rel_path.replace('\\', '/'))
    return sorted(files)

def read_deploy_list():
    """Read current deploy.py FILES_TO_DEPLOY list"""
    deploy_file = 'deploy.py'
    if not os.path.exists(deploy_file):
        return []
    
    with open(deploy_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    files_deployed = []
    in_list = False
    for line in content.split('\n'):
        if 'FILES_TO_DEPLOY = [' in line:
            in_list = True
            continue
        if in_list:
            if line.strip().startswith(']'):
                break
            for quote in ['"', "'"]:
                if quote in line:
                    start = line.find(quote) + 1
                    end = line.find(quote, start)
                    if end > start:
                        file_path = line[start:end]
                        if file_path and not file_path.startswith('#') and file_path.strip():
                            files_deployed.append(file_path.strip())
    
    return files_deployed, content

def get_critical_missing_files(deployed_list):
    """Get critical missing files"""
    all_services = get_all_python_files('backend/services')
    all_routes = get_all_python_files('backend/routes')
    
    critical_keywords = {
        'services': ['unified', 'point', 'agent', 'battle', 'leaderboard', 'monetization',
                    'tech_tree', 'energy', 'reward', 'trophy', 'shop', 'analytics',
                    'calculator', 'game', 'profile', 'database', 'counter', 'storage',
                    'system_json', 'connector', 'controller', 'mechanics'],
        'routes': ['unified', 'point', 'agent', 'battle', 'leaderboard', 'monetization',
                  'tech_tree', 'energy', 'reward', 'trophy', 'shop', 'analytics',
                  'calculator', 'game', 'profile', 'dashboard', 'api', 'controller',
                  'mechanics', 'systems']
    }
    
    missing_critical = []
    
    # Check services
    for service in all_services:
        if service not in deployed_list:
            service_lower = service.lower()
            if any(kw in service_lower for kw in critical_keywords['services']):
                missing_critical.append(service)
    
    # Check routes
    for route in all_routes:
        if route not in deployed_list:
            route_lower = route.lower()
            if any(kw in route_lower for kw in critical_keywords['routes']):
                missing_critical.append(route)
    
    return sorted(missing_critical)

def update_deploy_py():
    """Update deploy.py with missing critical files"""
    print("="*80)
    print("UPDATING deploy.py WITH MISSING FILES")
    print("="*80)
    print()
    
    # Read current deploy.py
    print("[1/4] Reading deploy.py...")
    deployed_list, deploy_content = read_deploy_list()
    print(f"  Currently deployed: {len(deployed_list)} files")
    print()
    
    # Find critical missing files
    print("[2/4] Finding critical missing files...")
    missing_critical = get_critical_missing_files(deployed_list)
    print(f"  Found {len(missing_critical)} critical missing files")
    print()
    
    if not missing_critical:
        print("  ✅ No critical files missing!")
        return
    
    # Show first 20
    print("  First 20 critical missing files:")
    for f in missing_critical[:20]:
        print(f"    - {f}")
    if len(missing_critical) > 20:
        print(f"    ... and {len(missing_critical) - 20} more")
    print()
    
    # Update deploy.py
    print("[3/4] Updating deploy.py...")
    
    # Find the FILES_TO_DEPLOY list in the content
    # Find where the list ends (before the closing bracket)
    list_start = deploy_content.find('FILES_TO_DEPLOY = [')
    if list_start == -1:
        print("  ❌ Could not find FILES_TO_DEPLOY list")
        return
    
    # Find the closing bracket
    lines = deploy_content.split('\n')
    list_start_line = deploy_content[:list_start].count('\n')
    list_end_line = None
    
    for i in range(list_start_line, len(lines)):
        if lines[i].strip() == ']':
            list_end_line = i
            break
    
    if list_end_line is None:
        print("  ❌ Could not find end of FILES_TO_DEPLOY list")
        return
    
    # Add missing files before the closing bracket
    new_lines = []
    indent = '    '  # 4 spaces
    
    # Add comment
    new_lines.append(f"{indent}# Critical missing services and routes")
    new_lines.append(f"{indent}# Added automatically - {len(missing_critical)} files")
    
    # Add files
    for file in missing_critical:
        new_lines.append(f'{indent}"{file}",')
    
    # Insert before closing bracket
    updated_lines = lines[:list_end_line] + new_lines + lines[list_end_line:]
    updated_content = '\n'.join(updated_lines)
    
    # Write updated content
    print("[4/4] Writing updated deploy.py...")
    with open('deploy.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"  ✅ Added {len(missing_critical)} files to deploy.py")
    print()
    print("="*80)
    print("UPDATE COMPLETE")
    print("="*80)
    print(f"Total files in deploy.py: {len(deployed_list) + len(missing_critical)}")
    print()

if __name__ == "__main__":
    update_deploy_py()
