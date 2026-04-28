#!/usr/bin/env python3
"""
Restart webserver and check dashboard route for 404/500 errors
"""
import os
import sys
import paramiko
import requests
import time
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"
BASE_URL = "https://masternoder.dk"

def restart_webserver(ssh_client):
    """Restart webserver services"""
    print("=" * 70)
    print("RESTARTING WEBSERVER")
    print("=" * 70)
    
    services_to_restart = ['uwsgi', 'python-proxy', 'apache2', 'nginx']
    restarted = []
    
    for service in services_to_restart:
        try:
            # Check if service exists
            stdin, stdout, stderr = ssh_client.exec_command(f"systemctl list-unit-files | grep -q ^{service}.service && echo 'EXISTS' || echo 'NOT_FOUND'")
            exists = stdout.read().decode().strip() == 'EXISTS'
            
            if exists:
                print(f"Restarting {service}...")
                stdin, stdout, stderr = ssh_client.exec_command(f"systemctl restart {service}")
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"[OK] {service} restarted")
                    restarted.append(service)
                    time.sleep(2)  # Wait a bit between restarts
                else:
                    error = stderr.read().decode('utf-8', errors='ignore')
                    print(f"[WARN] {service} restart had issues: {error[:100]}")
            else:
                print(f"[SKIP] {service} service not found")
        except Exception as e:
            print(f"[ERROR] Failed to restart {service}: {str(e)}")
    
    # Also touch WSGI file to trigger reload
    try:
        wsgi_files = [
            f"{REMOTE_PATH}/wsgi.py",
            f"{REMOTE_PATH}/src/app.py",
        ]
        for wsgi_file in wsgi_files:
            stdin, stdout, stderr = ssh_client.exec_command(f"test -f {wsgi_file} && touch {wsgi_file} && echo 'TOUCHED' || echo 'NOT_FOUND'")
            if stdout.read().decode().strip() == 'TOUCHED':
                print(f"[OK] Touched {wsgi_file} to trigger reload")
    except Exception as e:
        print(f"[WARN] Could not touch WSGI file: {str(e)}")
    
    return restarted

def check_dashboard_route():
    """Check dashboard route for 404/500 errors"""
    print("\n" + "=" * 70)
    print("CHECKING DASHBOARD ROUTE")
    print("=" * 70)
    
    dashboard_urls = [
        f"{BASE_URL}/vidgenerator/dashboard",
        f"{BASE_URL}/vidgenerator/dashboard/",
        f"{BASE_URL}/vidgenerator/dashboard/index.html",
    ]
    
    results = {}
    
    for url in dashboard_urls:
        try:
            print(f"\nTesting: {url}")
            response = requests.get(url, timeout=10, allow_redirects=True)
            status_code = response.status_code
            results[url] = {
                'status': status_code,
                'success': status_code == 200,
                'content_length': len(response.content),
                'error': None
            }
            
            if status_code == 200:
                print(f"[OK] Status: {status_code}, Content Length: {len(response.content)} bytes")
                
                # Check for error messages in HTML
                content = response.text
                if '500' in content or 'Internal Server Error' in content or 'Error loading' in content:
                    print(f"[WARN] Page contains error messages!")
                    # Extract error message
                    import re
                    error_match = re.search(r'Error[^<]*', content, re.IGNORECASE)
                    if error_match:
                        print(f"  Error message: {error_match.group(0)[:200]}")
                    results[url]['error'] = 'Error message found in HTML'
            elif status_code == 404:
                print(f"[404] Page not found")
                results[url]['error'] = '404 Not Found'
            elif status_code == 500:
                print(f"[500] Internal Server Error")
                # Try to get error details
                try:
                    error_content = response.text[:500]
                    print(f"  Error content: {error_content}")
                except:
                    pass
                results[url]['error'] = '500 Internal Server Error'
            else:
                print(f"[{status_code}] Unexpected status code")
                results[url]['error'] = f'Status {status_code}'
                
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request failed: {str(e)}")
            results[url] = {
                'status': None,
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            print(f"[ERROR] Unexpected error: {str(e)}")
            results[url] = {
                'status': None,
                'success': False,
                'error': str(e)
            }
    
    return results

def check_dashboard_resources():
    """Check dashboard page resources (CSS, JS, API endpoints)"""
    print("\n" + "=" * 70)
    print("CHECKING DASHBOARD RESOURCES")
    print("=" * 70)
    
    # First get the dashboard page to extract resource URLs
    try:
        response = requests.get(f"{BASE_URL}/vidgenerator/dashboard", timeout=10)
        if response.status_code != 200:
            print("[SKIP] Cannot check resources - dashboard page not accessible")
            return {}
        
        html = response.text
        import re
        
        # Find CSS files
        css_pattern = r'href=["\']([^"\']+\.css[^"\']*)["\']'
        css_files = re.findall(css_pattern, html)
        
        # Find JS files
        js_pattern = r'src=["\']([^"\']+\.js[^"\']*)["\']'
        js_files = re.findall(js_pattern, html)
        
        # Find API endpoints (fetch calls)
        fetch_pattern = r'fetch\(["\']([^"\']+/api/[^"\']+)["\']'
        api_endpoints = re.findall(fetch_pattern, html)
        
        all_resources = []
        for css in css_files:
            if not css.startswith('http') and not css.startswith('//'):
                all_resources.append(('css', urljoin(BASE_URL, css)))
            else:
                all_resources.append(('css', css))
        
        for js in js_files:
            if not js.startswith('http') and not js.startswith('//'):
                all_resources.append(('js', urljoin(BASE_URL, js)))
            else:
                all_resources.append(('js', js))
        
        for api in api_endpoints:
            if not api.startswith('http') and not api.startswith('//'):
                all_resources.append(('api', urljoin(BASE_URL, api)))
            else:
                all_resources.append(('api', api))
        
        print(f"\nFound {len(all_resources)} resources to check")
        
        resource_results = {}
        for resource_type, url in all_resources[:20]:  # Limit to first 20
            try:
                method = 'HEAD' if resource_type != 'api' else 'GET'
                response = requests.request(method, url, timeout=5, allow_redirects=True)
                
                status = response.status_code
                if status == 200:
                    print(f"[OK] {resource_type.upper()}: {url}")
                elif status == 404:
                    print(f"[404] {resource_type.upper()}: {url}")
                    resource_results[url] = {'status': 404, 'error': '404 Not Found'}
                elif status == 500:
                    print(f"[500] {resource_type.upper()}: {url}")
                    resource_results[url] = {'status': 500, 'error': '500 Internal Server Error'}
                else:
                    print(f"[{status}] {resource_type.upper()}: {url}")
                    resource_results[url] = {'status': status, 'error': f'Status {status}'}
            except Exception as e:
                print(f"[ERROR] {resource_type.upper()}: {url} - {str(e)}")
                resource_results[url] = {'status': None, 'error': str(e)}
        
        return resource_results
        
    except Exception as e:
        print(f"[ERROR] Failed to check resources: {str(e)}")
        return {}

def main():
    """Main function"""
    print("=" * 70)
    print("WEBSERVER RESTART & DASHBOARD CHECK")
    print("=" * 70)
    print(f"Server: {SERVER_HOST}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    ssh_client = None
    try:
        # Step 1: Connect and restart webserver
        print("Connecting to server...")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        # Restart webserver
        restarted = restart_webserver(ssh_client)
        
        # Wait for services to fully restart
        print("\nWaiting 5 seconds for services to restart...")
        time.sleep(5)
        
        # Step 2: Check dashboard route
        dashboard_results = check_dashboard_route()
        
        # Step 3: Check dashboard resources
        resource_results = check_dashboard_resources()
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Services Restarted: {len(restarted)} ({', '.join(restarted) if restarted else 'None'})")
        
        working_urls = sum(1 for r in dashboard_results.values() if r.get('success'))
        total_urls = len(dashboard_results)
        print(f"Dashboard URLs: {working_urls}/{total_urls} working")
        
        broken_resources = len(resource_results)
        print(f"Broken Resources: {broken_resources}")
        
        # List any errors
        errors_found = False
        for url, result in dashboard_results.items():
            if not result.get('success') or result.get('error'):
                if not errors_found:
                    print("\nErrors Found:")
                    errors_found = True
                print(f"  {url}: {result.get('error', 'Unknown error')}")
        
        for url, result in resource_results.items():
            if not errors_found:
                print("\nResource Errors:")
                errors_found = True
            print(f"  {url}: {result.get('error', 'Unknown error')}")
        
        if not errors_found:
            print("\n[OK] No errors found!")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if ssh_client:
            ssh_client.close()
    
    return True

if __name__ == "__main__":
    main()

