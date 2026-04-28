#!/usr/bin/env python3
"""Investigate 502 Bad Gateway - check nginx, uwsgi, python-proxy, and logs."""
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE = "/var/www/html"

def run(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = stdout.read().decode(errors="replace").strip()
    except BaseException:
        out = ""
    try:
        err = stderr.read().decode(errors="replace").strip()
    except BaseException:
        err = ""
    return out, err

def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=" * 70)
    print("502 BAD GATEWAY INVESTIGATION")
    print("=" * 70)

    # 1. Service status
    print("\n[1] SERVICE STATUS")
    for svc in ["uwsgi", "uwsgi-vidgenerator", "python-proxy", "nginx"]:
        out, _ = run(ssh, f"systemctl is-active {svc} 2>/dev/null || echo 'not-found'")
        lines = (out or "").strip().splitlines()
        status = lines[0].strip() if lines else "not-found"
        print(f"  {svc}: {status}")

    # 2. Nginx error log (502 usually logged here)
    print("\n[2] NGINX ERROR LOG (last 25 lines)")
    nginx_log, _ = run(ssh, "tail -25 /var/log/nginx/error.log 2>/dev/null")
    print(nginx_log or "(empty)")

    # 3. Nginx config - where does it proxy?
    print("\n[3] NGINX PROXY CONFIG (masternoder.dk)")
    out, _ = run(ssh, "grep -E 'proxy_pass|upstream|location' /etc/nginx/sites-enabled/masternoder.dk 2>/dev/null | head -40")
    print(out or "(no masternoder.dk config)")
    out2, _ = run(ssh, "cat /etc/nginx/sites-enabled/masternoder.dk 2>/dev/null | head -80")
    if out2 and "proxy_pass" in out2:
        print("\n--- Full relevant block ---")
        print(out2[:2000])

    # 4. uWSGI config and socket/port
    print("\n[4] UWSGI CONFIG")
    out, _ = run(ssh, f"cat {REMOTE}/uwsgi.ini 2>/dev/null")
    print(out[:800] if out else "(no uwsgi.ini)")
    out, _ = run(ssh, "ls -la /etc/uwsgi/apps-enabled/ 2>/dev/null")
    print("\n  apps-enabled:", out or "(none)")

    # 5. What is listening on 5000 / socket?
    print("\n[5] LISTENING PORTS / SOCKETS")
    port_out, _ = run(ssh, "ss -tlnp | grep -E '5000|uwsgi' 2>/dev/null")
    print(port_out or "(nothing on 5000)")
    out, _ = run(ssh, "ls -la /var/www/html/*.sock /run/uwsgi/*/*.sock /var/run/uwsgi/*/*.sock 2>/dev/null")
    print("  Sockets:", out or "(none)")

    # 6. uWSGI log (startup errors, Python crashes)
    print("\n[6] UWSGI LOG (last 40 lines)")
    out, _ = run(ssh, f"tail -40 {REMOTE}/uwsgi.log 2>/dev/null")
    print(out or "(no uwsgi.log)")

    # 6b. uWSGI log – grep for crash/error (workers dying = 502 + "prematurely closed" or "recv() failed (104)")
    print("\n[6b] UWSGI LOG – errors/tracebacks (worker crashes)")
    uwsgi_log_path = f"{REMOTE}/uwsgi.log"
    crash_cmd = f"grep -E 'Traceback|Error|Exception|killed|harakiri|SIGSEGV|SIGABRT|worker.*died' {uwsgi_log_path} 2>/dev/null | tail -60"
    crash_out, _ = run(ssh, crash_cmd, timeout=10)
    print(crash_out if crash_out else "(no matches – workers may be dying without logging; run uWSGI in foreground to see traceback)")

    # 7. Direct curl tests (first request can take 2+ min with lazy-apps; use 120s timeout)
    print("\n[7] DIRECT CURL TESTS")
    curl_port_out = ""
    try:
        curl_port_out, _ = run(ssh, "curl -s -m 120 -o /dev/null -w 'Port 5000: HTTP %{http_code}\\n' http://127.0.0.1:5000/ 2>/dev/null || echo 'Port 5000: timeout or failed'", timeout=125)
        print(curl_port_out or "Port 5000: (no output)")
        out, _ = run(ssh, "curl -s -m 90 -o /dev/null -w 'HTTPS site: HTTP %{http_code}\\n' https://masternoder.dk/ 2>/dev/null || echo 'HTTPS: timeout or failed'", timeout=95)
        print(out or "HTTPS: (no output)")
        for sock in ["/var/www/html/uwsgi.sock", "/run/uwsgi/app/vidgenerator/socket"]:
            out, _ = run(ssh, f"curl -s -o /dev/null -w 'Socket {sock}: HTTP %{{http_code}}\\n' --unix-socket {sock} http://localhost/vidgenerator/ 2>/dev/null")
            if out and "HTTP 200" in out:
                print(out)
                break
            if out:
                print(out)
    except BaseException as e:
        print(f"  (curl step skipped: {type(e).__name__})")

    # 8. Python import test (stats_aggregated could crash app)
    print("\n[8] PYTHON IMPORT TEST (app + missing_endpoints)")
    out, _ = run(ssh, f"cd {REMOTE} && python3 -c \"from src.app import create_app; app=create_app(); print('OK')\" 2>&1")
    print(out[:500] if out else "(no output)")

    ssh.close()

    # Summary and recommendation
    print("\n" + "=" * 70)
    print("SUMMARY & RECOMMENDATION")
    print("=" * 70)
    has_111 = nginx_log and "111" in nginx_log and "connect() failed" in nginx_log
    has_premature = nginx_log and ("prematurely closed" in nginx_log or "recv() failed (104)" in nginx_log)
    port_5000_now = port_out and "5000" in port_out and "LISTEN" in port_out
    curl_got_000 = curl_port_out and ("000" in curl_port_out or "timeout" in (curl_port_out or "").lower())
    if has_premature:
        print("Nginx shows 'upstream prematurely closed' or 'recv() failed (104)' = uWSGI workers are")
        print("dying mid-request. Check [6b] above for Python tracebacks. To see the crash live:")
        print("  On server:  sudo systemctl stop uwsgi-vidgenerator")
        print("  Then:       cd /var/www/html && sudo -u www-data /usr/bin/uwsgi --ini uwsgi.ini")
        print("  In another terminal:  curl -s http://127.0.0.1:5000/api/points/all")
        print("  Fix the exception shown, then restart:  sudo systemctl start uwsgi-vidgenerator")
    elif port_5000_now and curl_got_000:
        print("Port 5000 is LISTENING but curl got HTTP 000 (timeout). With lazy-apps, the first")
        print("request can take 2+ minutes while workers load 123 blueprints. Options:")
        print("  • Wait 2–3 min then reload https://masternoder.dk/")
        print("  • Restart and wait:  python fix_502.py  (then give workers time to load)")
        print("  • To avoid slow first load: in uwsgi.ini set lazy-apps = false (uses more RAM)")
    elif has_111 and port_5000_now:
        print("Nginx log shows 'connect() failed (111)' = nothing was accepting on 127.0.0.1:5000")
        print("when those requests happened. Right now port 5000 IS in use (uWSGI). So the backend")
        print("was down or restarting then; it is up now. If 502/111 keeps happening:")
        print("  • Restart backend:  python fix_502.py")
        print("  • Or on server:     sudo systemctl restart uwsgi-vidgenerator")
    elif has_111 and not port_5000_now:
        print("Nginx log shows 'connect() failed (111)'. Nothing is listening on port 5000 now.")
        print("Start the backend:  python fix_502.py   (or on server: systemctl start uwsgi-vidgenerator)")
    else:
        print("If uwsgi service is 'failed' and uwsgi.log shows 'Address already in use',")
        print("a stuck process may be holding port 5000. Fix:  python fix_502.py")
    if nginx_log and "robots.txt" in nginx_log and "No such file" in nginx_log:
        print("\nrobots.txt 404: Nginx is serving /robots.txt from disk. To proxy to app or fix, add a")
        print("location = /robots.txt { proxy_pass http://127.0.0.1:5000; } in the server block.")
    print("=" * 70)

if __name__ == "__main__":
    main()
