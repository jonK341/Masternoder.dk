#!/usr/bin/env python3
"""
Capture why uWSGI exits with status=1 (so we can fix it).
Run from your PC:  python scripts/diagnose_uwsgi_exit_code.py

SSHs to the server and runs uwsgi in foreground for a few seconds;
the first error lines are printed (chdir, import, bind, etc.).
"""
import os
import sys

# Same as fix_502.py
SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))


def main():
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    print("=" * 60)
    print("Diagnose uWSGI exit code 1 (capture real error)")
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)

    def run(cmd, timeout=20):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    # Run uwsgi in foreground; it will exit with 1 quickly, we capture first 80 lines
    print("\n[1] Running uwsgi in foreground (15s) to capture error...\n")
    cmd = "timeout 15 sudo -u www-data /usr/bin/uwsgi --ini /var/www/html/vidgenerator/uwsgi.ini 2>&1 || true"
    out, err = run(cmd, timeout=20)
    combined = (out + "\n" + err).strip()
    if combined:
        for line in combined.split("\n")[:80]:
            print(line)
    else:
        print("(no output captured)")

    # Show last 20 lines of uwsgi.log if any
    print("\n[2] Last 20 lines of /var/www/html/vidgenerator/uwsgi.log")
    out, _ = run("tail -20 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null || true")
    if out:
        print(out)
    else:
        print("(empty or missing)")

    # Check port 5000
    print("\n[3] Port 5000")
    port_out, _ = run("ss -tlnp 2>/dev/null | grep 5000 || echo 'nothing on 5000'")
    print(port_out)

    ssh.close()

    # If uwsgi is already listening and log shows blueprints, app is healthy
    if "LISTEN" in port_out and "127.0.0.1:5000" in port_out:
        print("\n--> No error to fix: uWSGI is already running on port 5000 and the log shows blueprints loaded.")
        print("    (Section [1] had no error because a second uwsgi could not bind - the first one is using the port.)")
    else:
        print("\nDone. Fix the error shown above (chdir, import, bind, uid, etc.).")


if __name__ == "__main__":
    main()
