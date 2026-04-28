#!/usr/bin/env python3
"""
Analyze Deployment Status
Compares local files with deploy.py to identify what needs deployment
"""
import os
from pathlib import Path

def get_all_python_files(directory):
    """Get all Python files in directory"""
    files = []
    for root, dirs, filenames in os.walk(directory):
        # Skip __pycache__ and .pyc files
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for filename in filenames:
            if filename.endswith('.py') and not filename.endswith('.pyc'):
                rel_path = os.path.relpath(os.path.join(root, filename))
                files.append(rel_path.replace('\\', '/'))
    return sorted(files)

def analyze_deployment():
    """Analyze deployment status"""
    print("="*80)
    print("DEPLOYMENT STATUS ANALYSIS")
    print("="*80)
    print()
    
    # Read deploy.py to see what's currently deployed
    deploy_file = 'deploy.py'
    if os.path.exists(deploy_file):
        with open(deploy_file, 'r', encoding='utf-8') as f:
            deploy_content = f.read()
        
        # Extract FILES_TO_DEPLOY list
        files_deployed = []
        in_list = False
        for line in deploy_content.split('\n'):
            if 'FILES_TO_DEPLOY = [' in line:
                in_list = True
                continue
            if in_list:
                if line.strip().startswith(']'):
                    break
                # Extract file path from line
                if '"' in line or "'" in line:
                    # Find quoted string
                    for quote in ['"', "'"]:
                        if quote in line:
                            start = line.find(quote) + 1
                            end = line.find(quote, start)
                            if end > start:
                                file_path = line[start:end]
                                if file_path and not file_path.startswith('#'):
                                    files_deployed.append(file_path)
        
        print(f"[1/4] Files in deploy.py: {len(files_deployed)}")
        print()
    else:
        print("[ERROR] deploy.py not found")
        return
    
    # Get all service files
    print("[2/4] Scanning local files...")
    services_dir = 'backend/services'
    routes_dir = 'backend/routes'
    
    all_services = get_all_python_files(services_dir) if os.path.exists(services_dir) else []
    all_routes = get_all_python_files(routes_dir) if os.path.exists(routes_dir) else []
    
    print(f"  Services found: {len(all_services)}")
    print(f"  Routes found: {len(all_routes)}")
    print()
    
    # Categorize files
    print("[3/4] Categorizing files...")
    
    services_in_deploy = [f for f in files_deployed if 'backend/services/' in f]
    routes_in_deploy = [f for f in files_deployed if 'backend/routes/' in f]
    frontend_in_deploy = [f for f in files_deployed if 'vidgenerator/' in f]
    core_in_deploy = [f for f in files_deployed if f.startswith('src/') or f.startswith('backend/register')]
    
    print(f"  Services in deploy.py: {len(services_in_deploy)}")
    print(f"  Routes in deploy.py: {len(routes_in_deploy)}")
    print(f"  Frontend in deploy.py: {len(frontend_in_deploy)}")
    print(f"  Core files in deploy.py: {len(core_in_deploy)}")
    print()
    
    # Find missing services
    print("[4/4] Identifying missing files...")
    print()
    
    missing_services = []
    for service in all_services:
        if service not in services_in_deploy:
            # Check if it's a critical service
            critical_keywords = [
                'unified', 'point', 'agent', 'battle', 'leaderboard',
                'monetization', 'tech_tree', 'energy', 'reward', 'trophy',
                'shop', 'analytics', 'calculator', 'game', 'profile'
            ]
            is_critical = any(keyword in service.lower() for keyword in critical_keywords)
            missing_services.append((service, is_critical))
    
    missing_routes = []
    for route in all_routes:
        if route not in routes_in_deploy:
            critical_keywords = [
                'unified', 'point', 'agent', 'battle', 'leaderboard',
                'monetization', 'tech_tree', 'energy', 'reward', 'trophy',
                'shop', 'analytics', 'calculator', 'game', 'profile',
                'dashboard', 'api'
            ]
            is_critical = any(keyword in route.lower() for keyword in critical_keywords)
            missing_routes.append((route, is_critical))
    
    # Sort by criticality
    missing_services.sort(key=lambda x: (not x[1], x[0]))
    missing_routes.sort(key=lambda x: (not x[1], x[0]))
    
    print("="*80)
    print("DEPLOYMENT GAP ANALYSIS")
    print("="*80)
    print()
    print(f"Currently Deployed: {len(files_deployed)} files")
    print(f"Total Services: {len(all_services)}")
    print(f"Total Routes: {len(all_routes)}")
    print()
    print(f"Missing Services: {len(missing_services)}")
    print(f"  Critical: {sum(1 for _, crit in missing_services if crit)}")
    print(f"  Non-Critical: {sum(1 for _, crit in missing_services if not crit)}")
    print()
    print(f"Missing Routes: {len(missing_routes)}")
    print(f"  Critical: {sum(1 for _, crit in missing_routes if crit)}")
    print(f"  Non-Critical: {sum(1 for _, crit in missing_routes if not crit)}")
    print()
    
    # Show critical missing files
    if missing_services:
        print("CRITICAL MISSING SERVICES (first 20):")
        critical_services = [s for s, crit in missing_services if crit][:20]
        for service in critical_services:
            print(f"  - {service}")
        if len([s for s, crit in missing_services if crit]) > 20:
            print(f"  ... and {len([s for s, crit in missing_services if crit]) - 20} more")
        print()
    
    if missing_routes:
        print("CRITICAL MISSING ROUTES (first 20):")
        critical_routes = [r for r, crit in missing_routes if crit][:20]
        for route in critical_routes:
            print(f"  - {route}")
        if len([r for r, crit in missing_routes if crit]) > 20:
            print(f"  ... and {len([r for r, crit in missing_routes if crit]) - 20} more")
        print()
    
    # Calculate deployment percentage
    total_critical = len([s for s, crit in missing_services if crit]) + len([r for r, crit in missing_routes if crit])
    total_files = len(all_services) + len(all_routes)
    deployed_files = len(services_in_deploy) + len(routes_in_deploy)
    deployment_percentage = (deployed_files / total_files * 100) if total_files > 0 else 0
    
    print("="*80)
    print("DEPLOYMENT STATISTICS")
    print("="*80)
    print(f"Deployment Coverage: {deployment_percentage:.1f}%")
    print(f"Files Deployed: {deployed_files}/{total_files}")
    print(f"Critical Files Missing: {total_critical}")
    print()
    
    return {
        'deployed': files_deployed,
        'missing_services': missing_services,
        'missing_routes': missing_routes,
        'deployment_percentage': deployment_percentage
    }

if __name__ == "__main__":
    analyze_deployment()
