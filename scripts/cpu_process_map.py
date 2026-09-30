#!/usr/bin/env python3
"""
CPU Process Map — inventory every running process on the live server,
group them by known role (uwsgi web workers, profit daemons, nginx, ad-hoc
deploy/debug scripts, etc.), and flag which ones look like stale/duplicate
"old processes" that are safe to kill.

This is READ-ONLY by default. It never kills anything unless you pass
--kill AND --yes.

Usage:
  # Just show the map + recommendations (safe, no changes made)
  python scripts/cpu_process_map.py

  # Show more processes per group
  python scripts/cpu_process_map.py --top 40

  # Actually terminate the flagged "safe to kill" candidates (graceful SIGTERM)
  python scripts/cpu_process_map.py --kill --yes

Requires DEPLOY_HOST / DEPLOY_USER / DEPLOY_PASS (same convention used by the
other scripts/*.py deploy tools in this repo). Set these as Cursor Cloud Agent
secrets, or export them locally before running.

Context baked in from this repo (uwsgi_common.ini, systemd/*.service):
  - uwsgi is expected to run as 2 independent instances (port 5000 + 5001),
    each with "master = true" + "processes = 4" -> 1 master + 4 workers = 5
    processes per instance, 10 total. Anything beyond that is a leftover
    master/worker set from a previous restart that didn't fully die.
  - scripts/start_*_agents.sh, run_profit_daemon_server.sh, and similar
    helpers launch long-running python3 daemons with `&`/nohup and a .pid
    file, but nothing stops the *previous* copy first, so re-running a
    deploy script is a common way to accumulate duplicate daemons.
"""
import os
import re
import sys
import argparse
import socket
from collections import defaultdict

SERVER_HOST = os.environ.get("DEPLOY_HOST", "")
SERVER_USER = os.environ.get("DEPLOY_USER", "root")
SERVER_PASS = os.environ.get("DEPLOY_PASS", "")

# 1 master + processes(4) per uwsgi instance, x2 instances (port 5000 + 5001)
EXPECTED_UWSGI_PER_INSTANCE = 5
ADHOC_STALE_SECONDS = 3600  # 1h+ old, orphaned (ppid=1), not a known daemon -> suspect

# (group name, regex over the full `cmd` column, is a long-running daemon we expect exactly one of)
GROUPS = [
    ("nginx", r"\bnginx\b", None),
    ("mysql/mariadb", r"\b(mysqld|mariadbd)\b", None),
    ("uwsgi:5000", r"uwsgi.*uwsgi\.ini|uwsgi.*http-socket[= ]127\.0\.0\.1:5000", EXPECTED_UWSGI_PER_INSTANCE),
    ("uwsgi:5001", r"uwsgi.*uwsgi_5001\.ini|uwsgi.*:5001", EXPECTED_UWSGI_PER_INSTANCE),
    ("uwsgi:other", r"\buwsgi\b", None),
    ("profit-daemon", r"all_profit_daemons\.py|run_profit_daemon_server\.sh", 1),
    ("casino-agent-daemon", r"casino_agent_daemon\.py", 1),
    ("social-monitor", r"social[_-]monitor", 1),
    ("agent-runner", r"production_agent_runner\.py|agents_runner\.py", 1),  # pragma: allowlist secret
    ("python-proxy", r"python-proxy", 1),
    ("ssh", r"\bsshd\b", None),
    ("cron", r"\bcron\b", None),
]


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top", type=int, default=25, help="How many processes to show in the raw top-CPU table")
    ap.add_argument("--kill", action="store_true", help="Send SIGTERM to flagged 'safe to kill' PIDs")
    ap.add_argument("--yes", action="store_true", help="Required together with --kill to actually execute kills")
    return ap.parse_args()


def connect():
    if not SERVER_HOST or not SERVER_PASS:
        sys.exit(
            "Missing SSH credentials. Set DEPLOY_HOST and DEPLOY_PASS (and optionally DEPLOY_USER, "
            "default 'root') as environment variables or Cursor Cloud Agent secrets before running this script."
        )
    try:
        import paramiko
    except ImportError:
        sys.exit("Install paramiko first: pip install paramiko")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=20)
    return ssh


def run(ssh, cmd, timeout=20):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    try:
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
    except (TimeoutError, OSError, socket.timeout):
        out, err = "", ""
    return out, err


PS_FIELDS = ["pid", "ppid", "user", "pcpu", "pmem", "etimes", "stat", "cmd"]


def fetch_processes(ssh):
    fmt = ",".join(PS_FIELDS)
    out, _ = run(ssh, f"ps -eo {fmt} --no-headers ww")
    procs = []
    for line in out.splitlines():
        parts = line.strip().split(None, len(PS_FIELDS) - 1)
        if len(parts) < len(PS_FIELDS):
            continue
        pid, ppid, user, pcpu, pmem, etimes, stat, cmd = parts
        try:
            procs.append({
                "pid": int(pid),
                "ppid": int(ppid),
                "user": user,
                "pcpu": float(pcpu),
                "pmem": float(pmem),
                "etimes": int(etimes),
                "stat": stat,
                "cmd": cmd,
            })
        except ValueError:
            continue
    return procs


def fmt_age(seconds):
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    if d:
        return f"{d}d{h}h"
    if h:
        return f"{h}h{m}m"
    return f"{m}m"


def classify(procs):
    """Return (groups: {name: [proc,...]}, ungrouped: [proc,...])"""
    groups = defaultdict(list)
    ungrouped = []
    for p in procs:
        # ps aux/ww itself and our own ssh/grep pipeline noise
        if re.search(r"\bps -eo\b|/bin/sh -c ps", p["cmd"]):
            continue
        matched = False
        for name, pattern, _expected in GROUPS:
            if re.search(pattern, p["cmd"], re.IGNORECASE):
                groups[name].append(p)
                matched = True
                break
        if not matched:
            ungrouped.append(p)
    return groups, ungrouped


def is_adhoc_script(p):
    return bool(re.search(r"python3?\s+.*\.py", p["cmd"])) and not re.search(
        r"uwsgi|wsgi|gunicorn", p["cmd"], re.IGNORECASE
    )


def build_recommendations(groups, ungrouped):
    """Return list of dicts: {pid, cmd, cpu, age, reason}"""
    kill_candidates = []

    for name, pattern, expected in GROUPS:
        plist = groups.get(name)
        if not plist or not expected:
            continue
        if len(plist) <= expected:
            continue
        # More instances than expected -> keep the newest `expected` (lowest etimes),
        # flag the rest (oldest / leftover from a previous restart) as kill candidates.
        ordered = sorted(plist, key=lambda p: p["etimes"])  # newest first
        stale = ordered[expected:]
        for p in stale:
            kill_candidates.append({
                "pid": p["pid"],
                "cmd": p["cmd"][:90],
                "cpu": p["pcpu"],
                "age": fmt_age(p["etimes"]),
                "reason": f"duplicate '{name}' process (expected {expected}, found {len(plist)}) — likely a leftover "
                          f"master/worker from a previous restart that never fully stopped",
            })

    # Duplicate daemon scripts by identical cmdline (covers ungrouped ad-hoc python
    # daemons/deploy scripts too — restricted to python invocations so we don't flag
    # unrelated system processes that legitimately run more than once).
    by_cmd = defaultdict(list)
    for p in ungrouped:
        if is_adhoc_script(p):
            by_cmd[p["cmd"]].append(p)
    for cmd, plist in by_cmd.items():
        if len(plist) > 1:
            ordered = sorted(plist, key=lambda p: p["etimes"])
            for p in ordered[1:]:
                kill_candidates.append({
                    "pid": p["pid"],
                    "cmd": p["cmd"][:90],
                    "cpu": p["pcpu"],
                    "age": fmt_age(p["etimes"]),
                    "reason": "duplicate copy of the same command still running — earlier run was never stopped",
                })

    # Orphaned (ppid=1, i.e. parent shell/deploy session exited) ad-hoc scripts left running a long time
    for p in ungrouped:
        if p["ppid"] == 1 and p["etimes"] >= ADHOC_STALE_SECONDS and is_adhoc_script(p):
            if any(c["pid"] == p["pid"] for c in kill_candidates):
                continue
            kill_candidates.append({
                "pid": p["pid"],
                "cmd": p["cmd"][:90],
                "cpu": p["pcpu"],
                "age": fmt_age(p["etimes"]),
                "reason": "orphaned ad-hoc python script (no parent shell, running "
                          f"{fmt_age(p['etimes'])}) — looks like a one-off deploy/debug script left running",
            })

    # Zombies — flagged for visibility only, cannot be "kill -9"'d directly
    zombies = [p for p in (groups_flat(groups) + ungrouped) if "Z" in p["stat"]]

    return kill_candidates, zombies


def groups_flat(groups):
    flat = []
    for plist in groups.values():
        flat.extend(plist)
    return flat


def print_report(load, mem, procs, groups, ungrouped, kill_candidates, zombies, top_n):
    print("=" * 78)
    print("SERVER LOAD / MEMORY")
    print("=" * 78)
    print(load)
    print()
    print(mem)
    print()

    print("=" * 78)
    print(f"TOP {top_n} PROCESSES BY CPU")
    print("=" * 78)
    print(f"{'PID':>7} {'PPID':>7} {'USER':<10} {'%CPU':>6} {'%MEM':>6} {'AGE':>7} {'STAT':<6} CMD")
    for p in sorted(procs, key=lambda p: -p["pcpu"])[:top_n]:
        print(f"{p['pid']:>7} {p['ppid']:>7} {p['user']:<10} {p['pcpu']:>6.1f} {p['pmem']:>6.1f} "
              f"{fmt_age(p['etimes']):>7} {p['stat']:<6} {p['cmd'][:80]}")

    print()
    print("=" * 78)
    print("PROCESS MAP BY ROLE")
    print("=" * 78)
    print(f"{'GROUP':<22} {'COUNT':>6} {'TOTAL %CPU':>11} {'OLDEST':>8} {'EXPECTED':>9}")
    for name, _pattern, expected in GROUPS:
        plist = groups.get(name)
        if not plist:
            continue
        total_cpu = sum(p["pcpu"] for p in plist)
        oldest = max(p["etimes"] for p in plist)
        flag = "  <-- extra!" if expected and len(plist) > expected else ""
        print(f"{name:<22} {len(plist):>6} {total_cpu:>10.1f}% {fmt_age(oldest):>8} "
              f"{(str(expected) if expected else '-'):>9}{flag}")
    if ungrouped:
        total_cpu = sum(p["pcpu"] for p in ungrouped)
        oldest = max(p["etimes"] for p in ungrouped) if ungrouped else 0
        print(f"{'other/unrecognized':<22} {len(ungrouped):>6} {total_cpu:>10.1f}% {fmt_age(oldest):>8} {'-':>9}")

    print()
    print("=" * 78)
    print("RECOMMENDATIONS")
    print("=" * 78)
    if not kill_candidates:
        print("No obviously stale/duplicate processes found. High CPU is likely from")
        print("legitimately-running services (uwsgi workers, profit daemons) under real load.")
    else:
        total_freed = sum(c["cpu"] for c in kill_candidates)
        print(f"Found {len(kill_candidates)} candidate process(es) to kill (~{total_freed:.1f}% CPU):\n")
        for c in kill_candidates:
            print(f"  PID {c['pid']:>7}  {c['cpu']:>5.1f}%  age {c['age']:>6}  {c['cmd']}")
            print(f"           reason: {c['reason']}")
            print(f"           command: kill {c['pid']}   (or `kill -9 {c['pid']}` if it ignores SIGTERM)")
        print("\nReview the list above before killing anything on a live server.")
        print("Re-run with --kill --yes to send SIGTERM to exactly these PIDs.")

    if zombies:
        print(f"\n{len(zombies)} zombie/defunct process(es) found (informational only; these free themselves")
        print("once their parent reaps them — if the parent is PID 1 and they persist, the parent")
        print("process itself is likely the real problem):")
        for p in zombies:
            print(f"  PID {p['pid']:>7}  ppid {p['ppid']:>7}  age {fmt_age(p['etimes']):>6}  {p['cmd'][:70]}")


def do_kill(ssh, kill_candidates):
    print("\n=== Killing flagged candidates (SIGTERM) ===")
    for c in kill_candidates:
        out, err = run(ssh, f"kill {c['pid']} 2>&1 || true")
        print(f"  kill {c['pid']} -> {out or err or 'ok'}")


def main():
    args = parse_args()
    ssh = connect()
    try:
        load, _ = run(ssh, "uptime; echo ---; cat /proc/loadavg; echo ---; nproc")
        mem, _ = run(ssh, "free -h")
        procs = fetch_processes(ssh)
        if not procs:
            sys.exit("Got no process data back from the server — check SSH connectivity/credentials.")

        groups, ungrouped = classify(procs)
        kill_candidates, zombies = build_recommendations(groups, ungrouped)

        print_report(load, mem, procs, groups, ungrouped, kill_candidates, zombies, args.top)

        if args.kill:
            if not args.yes:
                sys.exit("\n--kill requires --yes as well (safety check). No processes were killed.")
            if not kill_candidates:
                print("\nNothing flagged to kill; skipping.")
            else:
                do_kill(ssh, kill_candidates)
    finally:
        ssh.close()


if __name__ == "__main__":
    main()
