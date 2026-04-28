"""Fix social auth routes by adding them as direct routes in src/app.py
This adds the auth routes with highest priority (same pattern as generator routes)
"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)
sftp = ssh.open_sftp()

print("=" * 60)
print("FIX: Adding direct social auth routes to src/app.py")
print("=" * 60)

# Step 1: Backup current app.py
print("\n[STEP 1] Backing up src/app.py...")
import datetime
backup_name = f"/var/www/html/src/app.py.backup.{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
stdin, stdout, stderr = ssh.exec_command(f"cp /var/www/html/src/app.py {backup_name}")
stdout.channel.recv_exit_status()
print(f"  [OK] Backed up to {backup_name}")

# Step 2: Read current app.py
print("\n[STEP 2] Reading current src/app.py...")
with sftp.open("/var/www/html/src/app.py", "r") as f:
    content = f.read().decode('utf-8')
print(f"  [OK] Read {len(content)} bytes")

# Step 3: Find the insertion point (after the direct generator routes, before register_all_blueprints)
# Look for the line "print("[App] Direct generator routes registered FIRST with highest priority"
marker = '[App] Direct generator routes registered FIRST with highest priority'
if marker not in content:
    print(f"  [ERROR] Could not find marker: {marker}")
    print("  Trying alternative approach...")
    # Alternative: find the register_all_blueprints call
    marker = "from backend.register_blueprints import register_all_blueprints"
    
if marker in content:
    print(f"  [OK] Found insertion marker")
else:
    print(f"  [ERROR] Could not find any insertion marker!")
    ssh.close()
    sys.exit(1)

# Step 4: Insert direct auth routes
# We'll add them right after the direct generator routes section
auth_routes_code = '''
    # ============================================================
    # Direct Social Auth Routes - HIGHEST PRIORITY
    # Registered directly on app to bypass any blueprint routing issues
    # ============================================================
    try:
        from flask import jsonify
        
        @app.route('/api/auth/providers', methods=['GET'], strict_slashes=False)
        @app.route('/vidgenerator/api/auth/providers', methods=['GET'], strict_slashes=False)
        def direct_auth_providers():
            """Direct auth providers route - HIGHEST PRIORITY"""
            try:
                from backend.services.social_auth_service import list_providers
                _SOCIAL_PROVIDER_LOCK = "github"
                data = list_providers()
                providers = data.get("providers", []) if isinstance(data, dict) else []
                github = next((p for p in providers if p.get("id") == _SOCIAL_PROVIDER_LOCK), {})
                return jsonify({
                    "success": True,
                    "provider": _SOCIAL_PROVIDER_LOCK,
                    "enabled": bool(github.get("enabled")),
                    "configured": bool(github.get("configured")),
                    "start_path": f"/api/auth/{_SOCIAL_PROVIDER_LOCK}/start",
                    "callback_path": f"/api/auth/{_SOCIAL_PROVIDER_LOCK}/callback",
                }), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/auth/<provider>/start', methods=['GET'], strict_slashes=False)
        @app.route('/vidgenerator/api/auth/<provider>/start', methods=['GET'], strict_slashes=False)
        def direct_auth_start(provider):
            """Direct auth start route - HIGHEST PRIORITY"""
            try:
                from backend.services.social_auth_service import build_start_url, validate_return_url
                from flask import request, redirect
                _SOCIAL_PROVIDER_LOCK = "github"
                if provider != _SOCIAL_PROVIDER_LOCK:
                    return jsonify({"success": False, "error": f"{provider} login disabled", "allowed_provider": _SOCIAL_PROVIDER_LOCK}), 400
                user_id_hint = request.args.get("user_id_hint")
                return_url = request.args.get("return_url")
                do_redirect = (request.args.get("redirect") or "").lower() in ("1", "true", "yes")
                result = build_start_url(provider, user_id_hint=user_id_hint, return_url=return_url)
                if not result.get("success"):
                    return jsonify(result), 400
                if do_redirect:
                    return redirect(result["auth_url"], code=302)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        @app.route('/api/auth/<provider>/callback', methods=['GET'], strict_slashes=False)
        @app.route('/vidgenerator/api/auth/<provider>/callback', methods=['GET'], strict_slashes=False)
        def direct_auth_callback(provider):
            """Direct auth callback route - HIGHEST PRIORITY"""
            try:
                from backend.services.social_auth_service import handle_callback, validate_return_url
                from backend.services.account_resolution_service import set_session_user
                from flask import request, redirect
                _SOCIAL_PROVIDER_LOCK = "github"
                if provider != _SOCIAL_PROVIDER_LOCK:
                    return jsonify({"success": False, "error": f"{provider} callback disabled"}), 400
                code = request.args.get("code")
                state = request.args.get("state")
                if not code or not state:
                    return jsonify({"success": False, "error": "Missing code/state"}), 400
                result = handle_callback(provider, code, state)
                if not result.get("success"):
                    return jsonify(result), 400
                user_id = result.get("user_id")
                if user_id:
                    set_session_user(user_id)
                    result["session_bound"] = True
                return_url = result.get("return_url")
                safe_return_url = validate_return_url(return_url)
                if safe_return_url:
                    sep = "&" if "?" in return_url else "?"
                    url = f"{safe_return_url}{sep}auth_success=1&provider={provider}&user_id={result.get('user_id')}"
                    return redirect(url, code=302)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500
        
        print("[App] Direct social auth routes registered with highest priority", flush=True)
    except Exception as e:
        print(f"WARNING: Could not register direct social auth routes: {e}", flush=True)
'''

# Insert after the generator routes section
insert_after = '[App] Direct generator routes registered FIRST with highest priority'
if insert_after in content:
    # Find the except block that follows (the full try/except for generator routes)
    # We need to insert after the except Exception block
    idx = content.index(insert_after)
    # Find the next "except Exception as e:" after the marker
    search_start = idx
    # Find the print line
    print_idx = content.index("print(f\"WARNING: Could not register direct generator routes:", search_start)
    # Find the end of that except block (next blank line or next section)
    # Go past the traceback.print_exc() line
    traceback_idx = content.index("traceback.print_exc()", print_idx)
    # Find the end of the line after traceback
    end_of_block = content.index('\n', traceback_idx)
    # Insert our code after the generator routes section
    new_content = content[:end_of_block + 1] + auth_routes_code + content[end_of_block + 1:]
    print(f"  [OK] Inserted auth routes after generator section")
else:
    # Fallback: insert before register_all_blueprints
    insert_before = "from backend.register_blueprints import register_all_blueprints"
    idx = content.index(insert_before)
    # Find the try: block before this import
    try_idx = content.rfind('try:', 0, idx)
    new_content = content[:try_idx] + auth_routes_code + '\n' + content[try_idx:]
    print(f"  [OK] Inserted auth routes before blueprint registration")

# Step 5: Write updated app.py
print("\n[STEP 3] Writing updated src/app.py...")
with sftp.open("/var/www/html/src/app.py", "w") as f:
    f.write(new_content)
print(f"  [OK] Written {len(new_content)} bytes")

sftp.close()

# Step 6: Clear cache and restart
print("\n[STEP 4] Clearing cache and restarting...")
stdin, stdout, stderr = ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; rm -f /var/www/html/logs/auto_fix_endpoints/fixed_endpoints.json")
stdout.channel.recv_exit_status()

stdin, stdout, stderr = ssh.exec_command("systemctl stop uwsgi && sleep 2 && systemctl start uwsgi")
stdout.channel.recv_exit_status()
print("  [OK] Services restarted")

print("\n[WAIT] Waiting 10 seconds for initialization...")
time.sleep(10)

# Step 7: Test
print("\n[STEP 5] Testing endpoints...")
tests = [
    ('https://masternoder.dk/api/auth/providers', 'Auth Providers (public)'),
    ('https://masternoder.dk/vidgenerator/api/auth/providers', 'Auth Providers (vidgen)'),
    ('http://127.0.0.1:5000/api/auth/providers', 'Auth Providers (direct)'),
    ('https://masternoder.dk/api/user/index?user_id=test', 'User Index'),
    ('https://masternoder.dk/api/user/account-control?user_id=test', 'Account Control'),
]

all_ok = True
for url, name in tests:
    cmd = f"curl -s -w '\\nHTTP_CODE:%{{http_code}}' '{url}'"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8', errors='replace')
    lines = output.strip().split('\n')
    code_line = [l for l in lines if l.startswith('HTTP_CODE:')]
    code = code_line[0].split(':')[1] if code_line else '?'
    body = '\n'.join([l for l in lines if not l.startswith('HTTP_CODE:')])[:300]
    is_auto_fix = 'auto_fixed' in body
    is_real = not is_auto_fix and 'Not Found' not in body and 'Route not found' not in body and code == '200'
    
    status = "OK" if is_real else "AUTO-FIX" if is_auto_fix else f"FAIL({code})"
    print(f"  [{status}] {name}")
    if not is_real:
        all_ok = False
        print(f"         {body[:200]}")

print("\n" + "=" * 60)
if all_ok:
    print("[SUCCESS] All user account / social auth endpoints working!")
else:
    print("[PARTIAL] Some endpoints still have issues")
    # Check uwsgi log for errors
    stdin, stdout, stderr = ssh.exec_command("grep -i 'error\\|fail\\|auth' /var/www/html/vidgenerator/uwsgi.log | tail -10")
    output = stdout.read().decode('utf-8', errors='replace')
    if output.strip():
        print("  Recent errors:")
        print(output)
print("=" * 60)

ssh.close()
