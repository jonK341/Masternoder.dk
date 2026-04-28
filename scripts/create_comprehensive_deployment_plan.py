#!/usr/bin/env python3
"""
Create Comprehensive Deployment Plan
Generates a deployment plan for all missing services and routes
"""
import os
from pathlib import Path

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
    
    return files_deployed

def categorize_files(files):
    """Categorize files by type and priority"""
    categories = {
        'critical_services': [],
        'important_services': [],
        'other_services': [],
        'critical_routes': [],
        'important_routes': [],
        'other_routes': [],
        'frontend': [],
        'core': []
    }
    
    critical_keywords = {
        'services': ['unified', 'point', 'agent', 'battle', 'leaderboard', 'monetization', 
                    'tech_tree', 'energy', 'reward', 'trophy', 'shop', 'analytics', 
                    'calculator', 'game', 'profile', 'database', 'counter', 'storage'],
        'routes': ['unified', 'point', 'agent', 'battle', 'leaderboard', 'monetization',
                  'tech_tree', 'energy', 'reward', 'trophy', 'shop', 'analytics',
                  'calculator', 'game', 'profile', 'dashboard', 'api']
    }
    
    important_keywords = {
        'services': ['system', 'manager', 'controller', 'handler', 'tracker', 'monitor'],
        'routes': ['routes', 'page', 'api']
    }
    
    for file in files:
        if 'backend/services/' in file:
            file_lower = file.lower()
            if any(kw in file_lower for kw in critical_keywords['services']):
                categories['critical_services'].append(file)
            elif any(kw in file_lower for kw in important_keywords['services']):
                categories['important_services'].append(file)
            else:
                categories['other_services'].append(file)
        elif 'backend/routes/' in file:
            file_lower = file.lower()
            if any(kw in file_lower for kw in critical_keywords['routes']):
                categories['critical_routes'].append(file)
            elif any(kw in file_lower for kw in important_keywords['routes']):
                categories['important_routes'].append(file)
            else:
                categories['other_routes'].append(file)
        elif 'vidgenerator/' in file:
            categories['frontend'].append(file)
        elif file.startswith('src/') or 'register_blueprints' in file:
            categories['core'].append(file)
    
    return categories

def main():
    """Main function"""
    print("="*80)
    print("COMPREHENSIVE DEPLOYMENT PLAN GENERATOR")
    print("="*80)
    print()
    
    # Get current deployment list
    print("[1/5] Reading current deployment list...")
    deployed = read_deploy_list()
    print(f"  Currently deployed: {len(deployed)} files")
    print()
    
    # Get all local files
    print("[2/5] Scanning local files...")
    all_services = get_all_python_files('backend/services')
    all_routes = get_all_python_files('backend/routes')
    all_frontend = []
    for root, dirs, files in os.walk('vidgenerator'):
        if '__pycache__' in root:
            continue
        for file in files:
            if file.endswith(('.html', '.js', '.css')):
                rel_path = os.path.relpath(os.path.join(root, file))
                all_frontend.append(rel_path.replace('\\', '/'))
    
    print(f"  Services: {len(all_services)}")
    print(f"  Routes: {len(all_routes)}")
    print(f"  Frontend: {len(all_frontend)}")
    print()
    
    # Find missing files
    print("[3/5] Identifying missing files...")
    all_files = all_services + all_routes + all_frontend + ['src/app.py', 'backend/register_blueprints.py']
    missing = [f for f in all_files if f not in deployed and os.path.exists(f)]
    
    print(f"  Missing files: {len(missing)}")
    print()
    
    # Categorize missing files
    print("[4/5] Categorizing missing files...")
    categories = categorize_files(missing)
    
    print(f"  Critical services: {len(categories['critical_services'])}")
    print(f"  Important services: {len(categories['important_services'])}")
    print(f"  Other services: {len(categories['other_services'])}")
    print(f"  Critical routes: {len(categories['critical_routes'])}")
    print(f"  Important routes: {len(categories['important_routes'])}")
    print(f"  Other routes: {len(categories['other_routes'])}")
    print(f"  Frontend: {len(categories['frontend'])}")
    print()
    
    # Generate deployment plan
    print("[5/5] Generating deployment plan...")
    
    # Create TODO list
    todos = []
    
    # Phase 1: Critical services
    if categories['critical_services']:
        todos.append({
            'id': 'deploy-1',
            'content': f"Deploy {len(categories['critical_services'])} critical services",
            'status': 'pending',
            'files': categories['critical_services'][:30]  # First 30
        })
    
    # Phase 2: Critical routes
    if categories['critical_routes']:
        todos.append({
            'id': 'deploy-2',
            'content': f"Deploy {len(categories['critical_routes'])} critical routes",
            'status': 'pending',
            'files': categories['critical_routes'][:30]
        })
    
    # Phase 3: Important services
    if categories['important_services']:
        todos.append({
            'id': 'deploy-3',
            'content': f"Deploy {len(categories['important_services'])} important services",
            'status': 'pending',
            'files': categories['important_services'][:30]
        })
    
    # Phase 4: Important routes
    if categories['important_routes']:
        todos.append({
            'id': 'deploy-4',
            'content': f"Deploy {len(categories['important_routes'])} important routes",
            'status': 'pending',
            'files': categories['important_routes'][:30]
        })
    
    # Phase 5: Other files
    other_count = len(categories['other_services']) + len(categories['other_routes'])
    if other_count > 0:
        todos.append({
            'id': 'deploy-5',
            'content': f"Deploy {other_count} other services/routes",
            'status': 'pending',
            'files': (categories['other_services'] + categories['other_routes'])[:30]
        })
    
    # Phase 6: Frontend updates
    if categories['frontend']:
        todos.append({
            'id': 'deploy-6',
            'content': f"Deploy {len(categories['frontend'])} frontend files",
            'status': 'pending',
            'files': categories['frontend'][:30]
        })
    
    # Save deployment plan
    plan_file = 'DEPLOYMENT_PLAN.md'
    with open(plan_file, 'w', encoding='utf-8') as f:
        f.write("# Comprehensive Deployment Plan\n\n")
        f.write(f"**Generated:** {os.popen('date /t').read().strip() if os.name == 'nt' else ''}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Currently Deployed:** {len(deployed)} files\n")
        f.write(f"- **Total Local Files:** {len(all_files)} files\n")
        f.write(f"- **Missing Files:** {len(missing)} files\n")
        f.write(f"- **Deployment Coverage:** {len(deployed)/len(all_files)*100:.1f}%\n\n")
        f.write("## Deployment Phases\n\n")
        
        for i, todo in enumerate(todos, 1):
            f.write(f"### Phase {i}: {todo['content']}\n\n")
            f.write(f"**Files to deploy:** {len(todo['files'])}\n\n")
            f.write("```python\n")
            for file in todo['files']:
                f.write(f'    "{file}",\n')
            f.write("```\n\n")
    
    print(f"  [OK] Deployment plan saved to {plan_file}")
    print()
    
    # Print summary
    print("="*80)
    print("DEPLOYMENT PLAN SUMMARY")
    print("="*80)
    print(f"Total missing files: {len(missing)}")
    print(f"Deployment phases: {len(todos)}")
    print()
    for i, todo in enumerate(todos, 1):
        print(f"Phase {i}: {todo['content']}")
    print()
    print(f"Plan saved to: {plan_file}")
    print("="*80)
    
    return todos

if __name__ == "__main__":
    main()
