#!/usr/bin/env python3
"""
Retest URLs to verify application is working after errno 11 fix
"""
import os
import sys
import paramiko
import requests
from urllib.parse import urljoin

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"
BASE_URL = f"https://{SERVER_HOST}"

# URLs to test
URLS_TO_TEST = [
    # Main pages
    "/vidgenerator/",
    "/vidgenerator/dashboard/",
    "/vidgenerator/generator/",
    "/vidgenerator/debugger/",
    "/vidgenerator/gallery/",
    
    # API endpoints
    "/vidgenerator/api/stats/summary",
    "/vidgenerator/api/url-checker/check-navigation",
    
    # Health check
    "/vidgenerator/api/health",
]

def test_url_via_curl(ssh_client, url):
    """Test URL via curl on server"""
    full_url = urljoin(BASE_URL, url)
    try:
        cmd = f"curl -s -o /dev/null -w '%{{http_code}}|%{{time_total}}|%{{size_download}}' -k '{full_url}' --max-time 10 2>&1"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='ignore').strip()
        error = stderr.read().decode('utf-8', errors='ignore').strip()
        
        if output and '|' in output:
            parts = output.split('|')
            if len(parts) >= 3:
                http_code = parts[0]
                time_total = parts[1]
                size = parts[2]
                return {
                    'url': url,
                    'full_url': full_url,
                    'status_code': int(http_code) if http_code.isdigit() else None,
                    'time': float(time_total) if time_total.replace('.', '').isdigit() else None,
                    'size': int(size) if size.isdigit() else None,
                    'error': error if error else None
                }
        
        return {
            'url': url,
            'full_url': full_url,
            'status_code': None,
            'error': output + (f" | {error}" if error else "")
        }
    except Exception as e:
        return {
            'url': url,
            'full_url': full_url,
            'status_code': None,
            'error': str(e)
        }

def test_url_via_requests(url):
    """Test URL via requests library"""
    full_url = urljoin(BASE_URL, url)
    try:
        response = requests.get(full_url, timeout=10, verify=False, allow_redirects=True)
        return {
            'url': url,
            'full_url': full_url,
            'status_code': response.status_code,
            'time': response.elapsed.total_seconds(),
            'size': len(response.content),
            'headers': dict(response.headers),
            'error': None
        }
    except Exception as e:
        return {
            'url': url,
            'full_url': full_url,
            'status_code': None,
            'error': str(e)
        }

def check_application_status(ssh_client):
    """Check if application is running"""
    print("=" * 70)
    print("CHECKING APPLICATION STATUS")
    print("=" * 70)
    
    # Check uWSGI processes
    try:
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep uwsgi | grep -v grep | wc -l")
        process_count = stdout.read().decode('utf-8', errors='ignore').strip()
        if process_count.isdigit():
            count = int(process_count)
            print(f"✅ uWSGI processes: {count}")
        else:
            print("⚠️  Could not count uWSGI processes")
    except:
        print("⚠️  Could not check uWSGI processes")
    
    # Check service status
    try:
        stdin, stdout, stderr = ssh_client.exec_command("systemctl is-active uwsgi")
        status = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"✅ uWSGI service: {status}")
    except:
        print("⚠️  Could not check service status")
    
    # Check if port is listening
    try:
        stdin, stdout, stderr = ssh_client.exec_command("netstat -tlnp 2>/dev/null | grep ':5000' || ss -tlnp 2>/dev/null | grep ':5000' || echo 'Could not check port'")
        port_info = stdout.read().decode('utf-8', errors='ignore').strip()
        if '5000' in port_info and 'LISTEN' in port_info:
            print(f"✅ Port 5000: Listening")
        else:
            print(f"⚠️  Port 5000: {port_info[:100] if port_info else 'Not found'}")
    except:
        print("⚠️  Could not check port")

def test_all_urls(ssh_client):
    """Test all URLs"""
    print("\n" + "=" * 70)
    print("TESTING URLs")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = []
    
    for url in URLS_TO_TEST:
        print(f"Testing: {url}")
        result = test_url_via_curl(ssh_client, url)
        results.append(result)
        
        if result['status_code']:
            status = result['status_code']
            time_str = f"{result['time']:.2f}s" if result['time'] else "N/A"
            size_str = f"{result['size']} bytes" if result['size'] else "N/A"
            
            if status == 200:
                print(f"  ✅ {status} ({time_str}, {size_str})")
            elif status in [301, 302, 303, 307, 308]:
                print(f"  🔄 {status} Redirect ({time_str})")
            elif status == 404:
                print(f"  ❌ {status} Not Found")
            elif status == 500:
                print(f"  ❌ {status} Server Error")
            else:
                print(f"  ⚠️  {status} ({time_str})")
        else:
            error = result.get('error', 'Unknown error')
            print(f"  ❌ Error: {error[:100]}")
        print()
    
    return results

def print_summary(results):
    """Print summary of test results"""
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    success = len([r for r in results if r.get('status_code') == 200])
    redirects = len([r for r in results if r.get('status_code') in [301, 302, 303, 307, 308]])
    not_found = len([r for r in results if r.get('status_code') == 404])
    server_errors = len([r for r in results if r.get('status_code') == 500])
    errors = len([r for r in results if r.get('status_code') is None])
    
    print(f"Total URLs tested: {total}")
    print(f"✅ Success (200): {success}")
    print(f"🔄 Redirects: {redirects}")
    print(f"❌ Not Found (404): {not_found}")
    print(f"❌ Server Error (500): {server_errors}")
    print(f"❌ Errors: {errors}")
    
    success_rate = (success / total * 100) if total > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if not_found > 0:
        print(f"\n⚠️  URLs returning 404:")
        for r in results:
            if r.get('status_code') == 404:
                print(f"  - {r['url']}")
    
    if server_errors > 0:
        print(f"\n❌ URLs returning 500:")
        for r in results:
            if r.get('status_code') == 500:
                print(f"  - {r['url']}")
    
    if errors > 0:
        print(f"\n❌ URLs with errors:")
        for r in results:
            if r.get('status_code') is None:
                print(f"  - {r['url']}: {r.get('error', 'Unknown error')[:80]}")
    
    print("=" * 70)

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("URL RETEST AFTER ERRNO 11 FIX")
        print("=" * 70)
        print()
        
        # Check application status
        check_application_status(ssh_client)
        
        # Test all URLs
        results = test_all_urls(ssh_client)
        
        # Print summary
        print_summary(results)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()

