#!/usr/bin/env python3
"""
Analyze Nginx Bottlenecks
Checks nginx configuration for bottlenecks and missing routes
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def analyze_nginx():
    """Analyze nginx configuration"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Get nginx config
        print("[1/4] Getting nginx configuration...")
        stdin, stdout, stderr = ssh.exec_command(
            "cat /etc/nginx/sites-available/masternoder.dk 2>/dev/null || cat /etc/nginx/nginx.conf",
            timeout=10
        )
        config = stdout.read().decode('utf-8', errors='ignore')
        
        print()
        print("[2/4] Analyzing nginx configuration...")
        print()
        
        # Check for location blocks
        location_blocks = []
        in_location = False
        current_location = None
        for line in config.split('\n'):
            if 'location' in line and '{' in line:
                in_location = True
                current_location = line.strip()
                location_blocks.append({'block': current_location, 'content': []})
            elif in_location:
                if line.strip() == '}':
                    in_location = False
                    current_location = None
                elif current_location:
                    location_blocks[-1]['content'].append(line)
        
        print(f"Found {len(location_blocks)} location blocks:")
        for block in location_blocks:
            print(f"  - {block['block']}")
        print()
        
        # Check for /vidgenerator/ location
        vidgenerator_location = None
        for block in location_blocks:
            if '/vidgenerator' in block['block']:
                vidgenerator_location = block
                break
        
        if vidgenerator_location:
            print("[3/4] Analyzing /vidgenerator/ location block...")
            print()
            content = '\n'.join(vidgenerator_location['content'])
            
            # Check for rewrite rule
            if 'rewrite' in content:
                print("  ✅ Rewrite rule found")
                rewrite_lines = [l.strip() for l in content.split('\n') if 'rewrite' in l]
                for line in rewrite_lines:
                    print(f"    {line}")
            else:
                print("  ❌ Rewrite rule NOT found")
            
            # Check for proxy_pass
            if 'proxy_pass' in content:
                print("  ✅ proxy_pass found")
                proxy_lines = [l.strip() for l in content.split('\n') if 'proxy_pass' in l]
                for line in proxy_lines:
                    print(f"    {line}")
            else:
                print("  ❌ proxy_pass NOT found")
            
            # Check for buffer settings
            if 'proxy_buffering off' in content:
                print("  ✅ Buffer settings optimized (buffering off)")
            else:
                print("  ⚠️  Buffer settings may cause bottlenecks")
            
            # Check for timeouts
            timeout_settings = [l.strip() for l in content.split('\n') if 'timeout' in l.lower()]
            if timeout_settings:
                print("  ✅ Timeout settings found:")
                for line in timeout_settings:
                    print(f"    {line}")
            else:
                print("  ⚠️  No timeout settings found (may cause bottlenecks)")
        else:
            print("  ❌ /vidgenerator/ location block NOT found")
        
        print()
        print("[4/4] Checking for static file location blocks...")
        
        static_locations = [b for b in location_blocks if 'static' in b['block'].lower()]
        if static_locations:
            print(f"  ✅ Found {len(static_locations)} static file location blocks:")
            for block in static_locations:
                print(f"    - {block['block']}")
        else:
            print("  ⚠️  No dedicated static file location blocks found")
            print("  ⚠️  Static files may be proxied through Flask (bottleneck)")
        
        print()
        print("="*80)
        print("BOTTLENECK ANALYSIS")
        print("="*80)
        print()
        
        # Identify potential bottlenecks
        bottlenecks = []
        
        if not vidgenerator_location:
            bottlenecks.append("Missing /vidgenerator/ location block")
        
        if vidgenerator_location:
            content = '\n'.join(vidgenerator_location['content'])
            if 'proxy_buffering on' in content or 'proxy_buffering' not in content:
                bottlenecks.append("Proxy buffering may be enabled (slows responses)")
            
            if 'proxy_read_timeout' not in content:
                bottlenecks.append("No proxy_read_timeout (may cause hangs)")
            
            if 'proxy_connect_timeout' not in content:
                bottlenecks.append("No proxy_connect_timeout (may cause connection issues)")
        
        if not static_locations:
            bottlenecks.append("Static files proxied through Flask (should use nginx directly)")
        
        if bottlenecks:
            print("POTENTIAL BOTTLENECKS FOUND:")
            for i, bottleneck in enumerate(bottlenecks, 1):
                print(f"  {i}. {bottleneck}")
        else:
            print("✅ No obvious bottlenecks found in nginx configuration")
        
        ssh.close()
        return bottlenecks
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    analyze_nginx()
