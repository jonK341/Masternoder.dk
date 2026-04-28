#!/usr/bin/env python3
"""
Fix 504 Gateway Timeout by increasing nginx proxy timeouts.
Backend (uWSGI) may be slow; nginx often defaults to 60s and gives up first.

Usage:
  python scripts/fix_504_timeouts.py           # add 120s if missing
  python scripts/fix_504_timeouts.py --increase 300  # set all to 300s (e.g. when 120s still 504s)
  python scripts/fix_504_timeouts.py [--dry-run]

Reads /etc/nginx/sites-enabled/masternoder.dk. For each proxy_pass to 127.0.0.1:5000:
  - If block has no timeouts: add proxy_*_timeout (default 120s).
  - With --increase N: replace any proxy_*_timeout in those blocks with N seconds.
Then nginx -t && systemctl reload nginx.
"""
import os
import re
import sys
import argparse

SERVER_HOST = os.environ.get("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = (os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
NGINX_CONFIG = "/etc/nginx/sites-enabled/masternoder.dk"
DEFAULT_TIMEOUT = 120
# Scan this many lines after proxy_pass to find existing timeouts or block end
LOOKAHEAD = 80
# Match any proxy_*_timeout in block (for "already has timeout" check)
TIMEOUT_PATTERN = re.compile(
    r"proxy_(?:connect|send|read)_timeout\s",
    re.IGNORECASE
)
# Match a single timeout line for replacement (capture indent and kind)
TIMEOUT_LINE_PATTERN = re.compile(
    r"^(\s*)proxy_(connect|send|read)_timeout\s+\d+[sS]?\s*;",
    re.IGNORECASE
)


def timeout_lines(seconds: int, indent: str = "        ") -> str:
    return f"{indent}proxy_connect_timeout {seconds}s;\n{indent}proxy_send_timeout {seconds}s;\n{indent}proxy_read_timeout {seconds}s;"


def _block_end(lines: list, start: int) -> int:
    """Return index of the line that closes this location block (exclusive)."""
    for j in range(start, min(start + LOOKAHEAD, len(lines))):
        stripped = lines[j].strip()
        # First closing brace ends this block (nginx location blocks don't nest)
        if stripped == "}":
            return j
        if stripped.startswith("location ") or stripped.startswith("server "):
            return j
    return min(start + LOOKAHEAD, len(lines))


def _current_location(lines: list, proxy_line_index: int) -> str:
    """Find the location line that contains this proxy_pass (scan backward)."""
    for j in range(proxy_line_index, -1, -1):
        line = lines[j]
        m = re.match(r"\s*location\s+([^{]+)\s*\{?", line)
        if m:
            return m.group(1).strip()
    return "?"


def _block_has_timeout(lines: list, after_proxy: int, block_end: int) -> bool:
    """True if any proxy_*_timeout appears between after_proxy and block_end."""
    for j in range(after_proxy, block_end):
        if j < len(lines) and TIMEOUT_PATTERN.search(lines[j]):
            return True
    return False


def ensure_timeouts(content: str, timeout_sec: int = DEFAULT_TIMEOUT, dry_run: bool = False):
    """
    Insert timeout directives after each proxy_pass to 127.0.0.1:5000 if not already present.
    If dry_run, return (original_content, list of (location, action)) so no change.
    Otherwise return (new_content, list of (location, action)).
    """
    lines = content.split("\n")
    result = []
    actions = []  # (location_name, "add" | "skip")
    i = 0
    while i < len(lines):
        line = lines[i]
        result.append(line)
        if re.search(r"proxy_pass\s+http://127\.0\.0\.1:5000", line):
            block_end_idx = _block_end(lines, i + 1)
            has_timeout = _block_has_timeout(lines, i + 1, block_end_idx)
            location_name = _current_location(lines, i)
            if has_timeout:
                actions.append((location_name, "skip"))
            else:
                result.append(timeout_lines(timeout_sec).rstrip())
                actions.append((location_name, "add"))
        i += 1
    new_content = "\n".join(result)
    return (content if dry_run else new_content, actions)


def increase_existing_timeouts(content: str, new_sec: int) -> str:
    """
    Replace any proxy_*_timeout value in blocks that proxy to 127.0.0.1:5000 with new_sec.
    """
    lines = content.split("\n")
    block_start, block_end = -1, -1  # current 5000 block [block_start, block_end)
    result = []
    for i, line in enumerate(lines):
        if re.search(r"proxy_pass\s+http://127\.0\.0\.1:5000", line):
            block_start = i
            block_end = _block_end(lines, i + 1)
        if block_start <= i < block_end:
            m = TIMEOUT_LINE_PATTERN.match(line)
            if m:
                indent = m.group(1)
                kind = m.group(2).lower()
                line = f"{indent}proxy_{kind}_timeout {new_sec}s;"
        result.append(line)
    return "\n".join(result)


def main():
    ap = argparse.ArgumentParser(description="Increase nginx proxy timeouts to fix 504")
    ap.add_argument("--dry-run", action="store_true", help="Only show what would be changed")
    ap.add_argument("--increase", type=int, metavar="SEC", default=None,
                    help="Set all proxy timeouts to SEC seconds in blocks proxying to 5000 (e.g. 300)")
    args = ap.parse_args()

    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko")
        sys.exit(1)

    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    except Exception as e:
        print(f"[ERROR] Connect failed: {e}")
        sys.exit(1)

    def run(cmd, timeout=15):
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        return out, err

    out, err = run(f"cat {NGINX_CONFIG}")
    if not out and err:
        print(f"[ERROR] Could not read {NGINX_CONFIG}: {err}")
        ssh.close()
        sys.exit(1)
    original = out

    if args.increase is not None:
        # Replace existing timeouts with higher value
        new_content = increase_existing_timeouts(original, args.increase)
        if new_content == original:
            # No existing timeouts to replace — add args.increase in every proxy-to-5000 block
            print("No proxy_*_timeout lines found in proxy-to-5000 blocks. Adding {}s timeouts.".format(args.increase))
            new_content, _ = ensure_timeouts(original, timeout_sec=args.increase, dry_run=False)
        if new_content != original:
            run(f"cp {NGINX_CONFIG} {NGINX_CONFIG}.bak.504 2>/dev/null || true")
            sftp = ssh.open_sftp()
            with sftp.file(NGINX_CONFIG, "w") as f:
                f.write(new_content)
            sftp.close()
            out, err = run("nginx -t 2>&1")
            combined = (out + " " + err).lower()
            if "syntax is ok" not in combined and "successful" not in combined:
                print("[ERROR] nginx -t failed. Restoring backup.")
                run(f"cp {NGINX_CONFIG}.bak.504 {NGINX_CONFIG} 2>/dev/null || true")
                ssh.close()
                sys.exit(1)
            run("systemctl reload nginx 2>&1")
            print(f"Updated nginx proxy timeouts to {args.increase}s and reloaded nginx.")
        ssh.close()
        sys.exit(0)

    new_content, actions = ensure_timeouts(original, timeout_sec=DEFAULT_TIMEOUT, dry_run=False)
    adds = [loc for loc, act in actions if act == "add"]
    skips = [loc for loc, act in actions if act == "skip"]

    if new_content == original:
        print("Config already has proxy timeouts for all proxy_pass to 127.0.0.1:5000. Nothing to change.")
        print("To raise existing timeouts (e.g. 120s -> 300s):  python scripts/fix_504_timeouts.py --increase 300")
        ssh.close()
        sys.exit(0)

    if args.dry_run:
        print("Would add these lines after proxy_pass http://127.0.0.1:5000 (only in blocks that lack them):")
        print(timeout_lines(DEFAULT_TIMEOUT))
        if adds:
            print(f"\nWill ADD timeouts ({DEFAULT_TIMEOUT}s) in these blocks:")
            for loc in adds:
                print(f"  location {loc}")
        if skips:
            print("\nWill SKIP (already have timeouts):")
            for loc in skips:
                print(f"  location {loc}")
        print("\nRun without --dry-run to apply.")
        ssh.close()
        sys.exit(0)

    run(f"cp {NGINX_CONFIG} {NGINX_CONFIG}.bak.504 2>/dev/null || true")
    sftp = ssh.open_sftp()
    with sftp.file(NGINX_CONFIG, "w") as f:
        f.write(new_content)
    sftp.close()

    out, err = run("nginx -t 2>&1")
    combined = (out + " " + err).lower()
    if "syntax is ok" not in combined and "successful" not in combined:
        print("[ERROR] nginx -t failed. Restoring backup.")
        run(f"cp {NGINX_CONFIG}.bak.504 {NGINX_CONFIG} 2>/dev/null || true")
        print("stdout:", out)
        print("stderr:", err)
        ssh.close()
        sys.exit(1)

    run("systemctl reload nginx 2>&1")
    print(f"Updated nginx proxy timeouts to {DEFAULT_TIMEOUT}s and reloaded nginx.")
    if adds:
        print("Added in:", ", ".join(adds))
    ssh.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
