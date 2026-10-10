#!/usr/bin/env python3
"""
Complete Ubuntu web server scan and optional cleanup for masternoder.dk.
Scans for disk usage and safe-to-delete candidates; with --clean performs cleanup.

Usage:
  python scripts/server_cleanup_scan.py                  # Scan only (report)
  python scripts/server_cleanup_scan.py --investigate    # Deep dive: what fills the disk (du, largest dirs/files)
  python scripts/server_cleanup_scan.py --clean         # Scan then run safe cleanup
  python scripts/server_cleanup_scan.py --clean --yes   # Skip confirmation
  python scripts/server_cleanup_scan.py --full --yes    # Aggressive: whole-drive cleanup (logs, journal, autoremove)
  python scripts/server_cleanup_scan.py --full --yes --clear-all-videos  # Also remove all videos (max space)
"""
from __future__ import print_function

import os
import sys
import argparse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
REMOTE_BASE = "/var/www/html"
# Videos at root after move; fallback to legacy path
VIDEOS_DIR_REMOTE = "/var/www/html/videos"
VIDEOS_DIR_LEGACY = "/var/www/html/vidgenerator/videos"
BASE_REMOTE = "/var/www/html"  # App root (cleans __pycache__ under whole tree)


def run_cmd(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    return out, err


def _get_avail_kb(ssh):
    """Get available space in 1K blocks for root fs (/) from server."""
    out, _ = run_cmd(ssh, "df --output=avail / 2>/dev/null | tail -1")
    try:
        return int(out.strip())
    except (ValueError, AttributeError):
        return None


def _run_investigate(ssh, report):
    """Deep dive: what is using disk. Append to report list."""
    report.append("\n[INVESTIGATE] What is filling the server disk\n")

    out, _ = run_cmd(ssh, "df -h / 2>/dev/null")
    report.append(out or "(no df)")
    report.append("")

    # Top-level dirs on / (often /var, /usr are biggest)
    report.append("--- Top-level usage (/) ---")
    out, _ = run_cmd(ssh, "du -sh /var /usr /home /tmp /root /opt 2>/dev/null | sort -hr")
    report.append(out or "(no output)")
    report.append("")

    # /var breakdown
    report.append("--- /var breakdown ---")
    out, _ = run_cmd(ssh, "du -sh /var/* 2>/dev/null | sort -hr")
    report.append(out or "(no output)")
    report.append("")

    # /var/www breakdown (our app)
    report.append("--- /var/www (app) – biggest dirs ---")
    out, _ = run_cmd(ssh, "du -sh /var/www/html/* 2>/dev/null; du -sh /var/www/html/.venv /var/www/html/.git 2>/dev/null | sort -hr | head -40")
    report.append(out or "(no output)")
    report.append("")

    # .venv and venv-like dirs (often 500MB–2GB each)
    report.append("--- Virtual envs and caches (.venv, venv, __pycache__) ---")
    out, _ = run_cmd(ssh, "du -sh /var/www/html/.venv /var/www/html/vidgenerator/.venv /var/www/html/*/.venv /var/www/html/*/venv 2>/dev/null; find /var/www/html -maxdepth 3 -type d -name '.venv' -o -name 'venv' 2>/dev/null | head -20 | xargs -I{} du -sh {} 2>/dev/null")
    report.append(out or "(none)")
    report.append("")

    # Largest single files under /var/www (candidates to delete or compress)
    report.append("--- Largest files under /var/www (>20MB) ---")
    out, _ = run_cmd(ssh, "find /var/www -type f -size +20M 2>/dev/null | xargs du -h 2>/dev/null | sort -hr | head -25")
    report.append(out or "(none)")
    report.append("")

    # /var/log (log files)
    report.append("--- /var/log (largest files) ---")
    out, _ = run_cmd(ssh, "du -ah /var/log 2>/dev/null | sort -hr | head -20")
    report.append(out or "(no output)")
    report.append("")

    # journal, apt cache
    report.append("--- Journal & APT cache ---")
    out, _ = run_cmd(ssh, "journalctl --disk-usage 2>/dev/null; du -sh /var/cache/apt/archives /var/cache/apt/pkgcache.bin 2>/dev/null")
    report.append(out or "(no output)")
    report.append("")

    # /root (often has .cache, pip, old files – 1.9G is a lot)
    report.append("--- /root (user root home – often cache) ---")
    out, _ = run_cmd(ssh, "du -sh /root/.[!.]* /root/* 2>/dev/null | sort -hr | head -25")
    report.append(out or "(no output)")

    # /var/lib (dpkg, docker, etc.)
    report.append("")
    report.append("--- /var/lib (biggest subdirs) ---")
    out, _ = run_cmd(ssh, "du -sh /var/lib/* 2>/dev/null | sort -hr | head -15")
    report.append(out or "(no output)")

    # Any remaining backup or old dirs
    report.append("")
    report.append("--- Possible deletables (backups, old, .bak) ---")
    out, _ = run_cmd(ssh, "find /var/www/html -maxdepth 2 -type d \\( -name '*.backup*' -o -name '*.bak' -o -name '*.old' -o -name 'backup' \\) 2>/dev/null | head -20")
    report.append(out or "(none)")
    out2, _ = run_cmd(ssh, "ls -la /var/www/html/ | grep -E 'backup|bak|old' 2>/dev/null")
    if out2:
        report.append("  (dirs in html: " + out2.strip()[:200] + ")")
    report.append("")
    report.append("--- Logs safe to truncate (btmp = failed logins, can free 80MB+) ---")
    out, _ = run_cmd(ssh, "ls -la /var/log/btmp /var/log/auth.log 2>/dev/null")
    report.append(out or "(no output)")
    report.append("")
    report.append("=" * 60)
    report.append("Suggestions:")
    report.append("  1. /root: clear /root/.cache, /root/.pip if large (--clean-root-cache)")
    report.append("  2. Truncate btmp: sudo truncate -s 0 /var/log/btmp (frees ~80MB)")
    report.append("  3. Remove old backups: vidgenerator.backup.* (--remove-old-backups)")
    report.append("  4. Optional: delete en_US-lessac-medium.onnx (61MB TTS model, re-downloadable)")
    report.append("  5. journalctl --vacuum-size=50M, apt-get clean")
    report.append("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Scan Ubuntu server for disk usage and safe-to-delete files")
    parser.add_argument("--clean", action="store_true", help="Run safe cleanup after scan")
    parser.add_argument("--full", action="store_true", help="Whole-drive cleanup: --clean + truncate logs, aggressive journal, apt autoremove")
    parser.add_argument("--clear-all-videos", action="store_true", help="With --full: remove all videos (not just keep top 10). Use for max space.")
    parser.add_argument("--remove-old-backups", action="store_true", help="Remove /var/www/html/vidgenerator.backup.* (old backup dirs with .venv – frees hundreds of MB)")
    parser.add_argument("--investigate", "-i", action="store_true", help="Deep dive: show what uses disk (top dirs, /var/www breakdown, largest files)")
    parser.add_argument("--clean-btmp", action="store_true", help="Truncate /var/log/btmp (failed logins – frees ~80MB)")
    parser.add_argument("--clean-root-cache", action="store_true", help="Remove /root/.cache and /root/.pip/cache to free space")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation when using --clean/--full")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password (ignores DEPLOY_PASS in .env)")
    args = parser.parse_args()
    if args.full:
        args.clean = True
        args.remove_old_backups = True  # Free hundreds of MB from old vidgenerator.backup.*

    try:
        import paramiko
    except ImportError:
        print("pip install paramiko")
        sys.exit(1)

    server_pass = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = None
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=server_pass, timeout=30)
    except Exception as e:
        print("SSH connection failed:", e)
        if not args.ask_pass:
            print("Hint: DEPLOY_PASS in .env may be stale — retry with --ask-pass")
        sys.exit(1)

    try:
        report = []
        report.append("=" * 60)
        report.append("UBUNTU SERVER DISK SCAN — masternoder.dk")
        report.append("=" * 60)

        if args.investigate:
            _run_investigate(ssh, report)
            text = "\n".join(report)
            print(text)
            return

        # --- 1. Overall disk usage ---
        out, _ = run_cmd(ssh, "df -h / /var 2>/dev/null | tail -5")
        report.append("\n[1] DISK USAGE (df -h)")
        report.append(out or "(no output)")

        # --- 2. Large directories under /var ---
        out, _ = run_cmd(ssh, "du -sh /var/cache /var/log /var/www 2>/dev/null")
        report.append("\n[2] KEY DIRS (/var)")
        report.append(out or "(no output)")

        # --- 3. Nginx cache ---
        out, _ = run_cmd(ssh, "du -sh /var/cache/nginx 2>/dev/null || echo '0'")
        nginx_sz = (out or "0").split()[0] if out else "0"
        report.append("\n[3] NGINX CACHE")
        report.append("  /var/cache/nginx: {} (safe to clear)".format(nginx_sz))

        # --- 4. APT cache ---
        out, _ = run_cmd(ssh, "du -sh /var/cache/apt/archives 2>/dev/null || echo '0'")
        apt_sz = (out or "0").split()[0] if out else "0"
        report.append("\n[4] APT CACHE")
        report.append("  /var/cache/apt/archives: {} (safe: apt-get clean)".format(apt_sz))

        # --- 5. __pycache__ and .pyc under app ---
        out, _ = run_cmd(ssh, "find {} -type d -name __pycache__ 2>/dev/null | head -50".format(REMOTE_BASE))
        n_dirs = len([x for x in (out or "").strip().splitlines() if x.strip()])
        out2, _ = run_cmd(ssh, "find {} -type f -name '*.pyc' 2>/dev/null | wc -l".format(REMOTE_BASE))
        n_pyc = (out2 or "0").strip()
        out3, _ = run_cmd(ssh, "du -sh $(find {} -type d -name __pycache__ 2>/dev/null | tr '\\n' ' ') 2>/dev/null || echo 0".format(REMOTE_BASE))
        pycache_sz = (out3 or "0").split()[0] if out3 else "0"
        report.append("\n[5] PYTHON CACHE (app)")
        report.append("  __pycache__ dirs: {}, .pyc files: {}, total ~{} (safe to delete)".format(n_dirs, n_pyc, pycache_sz))

        # --- 6. Journal logs ---
        out, _ = run_cmd(ssh, "journalctl --disk-usage 2>/dev/null || echo '0'")
        report.append("\n[6] SYSTEMD JOURNAL")
        report.append("  " + (out or "N/A").replace("\n", " ")[:80])
        report.append("  (safe: journalctl --vacuum-time=3d or --vacuum-size=100M)")

        # --- 7. App / nginx logs ---
        report.append("\n[7] APP/NGINX LOGS (sizes)")
        out, _ = run_cmd(ssh, "for f in {}/uwsgi.log {}/flask_app.log /var/log/nginx/access.log /var/log/nginx/error.log; do test -f \"$f\" && du -sh \"$f\" 2>/dev/null; done".format(REMOTE_BASE, REMOTE_BASE))
        report.append(out or "  (none found)")

        # --- 8. Videos directory (root or legacy vidgenerator/videos) ---
        out, _ = run_cmd(ssh, "du -sh {} {} 2>/dev/null | tail -1 || echo '0'".format(VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
        vid_sz = (out or "0").split()[0] if out else "0"
        out2, _ = run_cmd(ssh, "for d in {} {}; do test -d \"$d\" && find \"$d\" -maxdepth 1 -name '*.mp4' 2>/dev/null | wc -l; done | awk '{{s+=$1}}END{{print s+0}}'".format(VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
        n_mp4 = (out2 or "0").strip()
        out_orphan, _ = run_cmd(ssh, "for d in {} {}; do du -ch \"$d\"/*.job.json \"$d\"/*.pipeline.json \"$d\"/*_temp_audio.mp4 2>/dev/null; done | tail -1 || echo '0'".format(VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
        orphan_sz = (out_orphan or "0").split()[0] if out_orphan else "0"
        report.append("\n[8] VIDEOS DIR (videos/ or vidgenerator/videos)")
        report.append("  Total: {}, .mp4 count: {} (retention: keep top 10 by size, rest eligible for cleanup)".format(vid_sz, n_mp4))
        report.append("  Orphan metadata/temp (.job.json, .pipeline.json, *_temp_audio.mp4): ~{} (cleaned with --clean)".format(orphan_sz))

        # --- 9. Old backup dirs (vidgenerator.backup.*) ---
        out, _ = run_cmd(ssh, "du -sh {}/vidgenerator.backup.* 2>/dev/null || echo ''".format(REMOTE_BASE))
        backup_lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
        report.append("\n[9] OLD BACKUP DIRS (safe to remove for space)")
        report.append("  " + ("; ".join(backup_lines) if backup_lines else "(none)"))

        # --- 10. Large files in /var/www ---
        out, _ = run_cmd(ssh, "find {} -type f -size +5M 2>/dev/null | head -30".format(REMOTE_BASE))
        report.append("\n[10] LARGE FILES >5MB under /var/www")
        report.append(out or "  (none)")

        # --- 11. /tmp and /var/tmp ---
        out, _ = run_cmd(ssh, "du -sh /tmp /var/tmp 2>/dev/null")
        report.append("\n[11] TMP DIRS")
        report.append("  " + (out or "N/A").replace("\n", " "))

        report.append("\n" + "=" * 60)
        report.append("END SCAN — use --clean to run safe cleanup")
        report.append("=" * 60)

        text = "\n".join(report)
        print(text)

        # Run btmp/root-cache only (no full cleanup)
        if (args.clean_btmp or args.clean_root_cache) and not args.clean:
            if args.clean_btmp:
                run_cmd(ssh, "truncate -s 0 /var/log/btmp 2>/dev/null; echo done")
                print("  [OK] Truncated /var/log/btmp (~80MB freed)")
            if args.clean_root_cache:
                run_cmd(ssh, "rm -rf /root/.cache/* /root/.pip/cache 2>/dev/null; echo done")
                print("  [OK] Cleared /root/.cache and /root/.pip/cache")
            return

        if args.remove_old_backups:
            if not args.yes:
                try:
                    r = input("Remove vidgenerator.backup.* dirs (frees hundreds of MB)? [y/N]: ")
                    if r.strip().lower() != "y":
                        print("Skipped.")
                    else:
                        run_cmd(ssh, "rm -rf {}/vidgenerator.backup.* 2>/dev/null; echo done".format(REMOTE_BASE))
                        print("  [OK] Removed vidgenerator.backup.*")
                except Exception:
                    print("Use --yes to skip prompt.")
            else:
                run_cmd(ssh, "rm -rf {}/vidgenerator.backup.* 2>/dev/null; echo done".format(REMOTE_BASE))
                print("  [OK] Removed vidgenerator.backup.*")
            if not args.clean:
                return

        if not args.clean:
            return

        # --- CLEANUP ---
        print("\n--- CLEANUP ({}) ---".format("--full (whole drive)" if args.full else "--clean"))
        if not args.yes:
            try:
                r = input("Proceed with safe cleanup? [y/N]: ")
                if r.strip().lower() != "y":
                    print("Aborted.")
                    return
            except Exception:
                print("Aborted (no TTY). Use --yes to skip prompt.")
                return

        before_kb = _get_avail_kb(ssh)
        cleaned = []

        if args.clean_btmp:
            run_cmd(ssh, "truncate -s 0 /var/log/btmp 2>/dev/null; echo done")
            cleaned.append("Truncated /var/log/btmp")
        if args.clean_root_cache:
            run_cmd(ssh, "rm -rf /root/.cache/* /root/.pip/cache 2>/dev/null; echo done")
            cleaned.append("Cleared /root/.cache and /root/.pip/cache")

        # Old backup dirs (with --full or --remove-old-backups)
        if args.remove_old_backups:
            run_cmd(ssh, "rm -rf {}/vidgenerator.backup.* 2>/dev/null; echo done".format(REMOTE_BASE))
            cleaned.append("Removed vidgenerator.backup.*")

        # Nginx cache
        run_cmd(ssh, "rm -rf /var/cache/nginx/* 2>/dev/null || true")
        cleaned.append("Nginx cache cleared")

        # APT cache
        run_cmd(ssh, "apt-get clean -y 2>/dev/null || true")
        cleaned.append("APT cache (apt-get clean)")

        # __pycache__ and .pyc
        run_cmd(ssh, "find {} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true".format(REMOTE_BASE))
        run_cmd(ssh, "find {} -type f -name '*.pyc' -delete 2>/dev/null || true".format(REMOTE_BASE))
        cleaned.append("Python __pycache__ and .pyc under /var/www/html")

        # Video: clear all (--clear-all-videos) or keep top 10 (both root and legacy dirs)
        if getattr(args, "clear_all_videos", False):
            run_cmd(ssh, "for d in {} {}; do rm -f \"$d\"/*.mp4 \"$d\"/*.webm \"$d\"/*.mkv \"$d\"/*.status.json \"$d\"/*.pipeline.json \"$d\"/*.job.json \"$d\"/*_temp_audio.mp4 2>/dev/null; done; echo done".format(
                VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
            cleaned.append("All videos and metadata removed (--clear-all-videos)")
        else:
            out, _ = run_cmd(ssh, "cd {} && for d in {} {}; do test -d \"$d\" || continue; VIDEOS_DIR=\"$d\" python3 scripts/cleanup_videos_keep_top10.py 2>/dev/null || VIDEOS_DIR=\"$d\" .venv/bin/python scripts/cleanup_videos_keep_top10.py 2>/dev/null; done || true".format(
                REMOTE_BASE, VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
            if out:
                print("  ", out.strip()[:200])
            cleaned.append("Video retention cleanup (keep top 10)")

        # Journal vacuum: aggressive when --full, else 3 days
        if args.full:
            run_cmd(ssh, "journalctl --vacuum-size=50M 2>/dev/null || true")
            cleaned.append("Journal vacuum (keep 50M)")
        else:
            run_cmd(ssh, "journalctl --vacuum-time=3d 2>/dev/null || true")
            cleaned.append("Journal vacuum (keep 3 days)")

        # Orphan video metadata/temp (both video dirs)
        run_cmd(ssh, "for d in {} {}; do rm -f \"$d\"/*_temp_audio.mp4 2>/dev/null; "
                     "cd \"$d\" 2>/dev/null && for f in *.job.json *.pipeline.json; do "
                     "test -f \"$f\" || continue; b=\"${{f%.job.json}}\"; b=\"${{b%.pipeline.json}}\"; "
                     "test -f \"$b.mp4\" || rm -f \"$f\"; done; done".format(VIDEOS_DIR_REMOTE, VIDEOS_DIR_LEGACY))
        cleaned.append("Orphan video metadata/temp (.job.json, .pipeline.json, *_temp_audio.mp4 without .mp4)")

        # --full: truncate large logs, apt autoremove
        if args.full:
            run_cmd(ssh, "for f in {}/uwsgi.log {}/flask_app.log {}/vidgenerator/uwsgi.log; do test -f \"$f\" && :> \"$f\" 2>/dev/null; done".format(REMOTE_BASE, REMOTE_BASE, REMOTE_BASE))
            cleaned.append("App logs truncated (uwsgi.log, flask_app.log)")
            run_cmd(ssh, "for f in /var/log/nginx/access.log /var/log/nginx/error.log; do test -f \"$f\" && :> \"$f\" 2>/dev/null; done")
            cleaned.append("Nginx logs truncated")
            run_cmd(ssh, "apt-get autoremove -y 2>/dev/null || true")
            cleaned.append("apt-get autoremove")
            run_cmd(ssh, "find /tmp /var/tmp -type f -mtime +7 -delete 2>/dev/null; echo ok")
            cleaned.append("tmp dirs: removed files older than 7 days")

        for line in cleaned:
            print("  [OK]", line)

        after_kb = _get_avail_kb(ssh)
        if before_kb is not None and after_kb is not None and after_kb >= before_kb:
            freed_kb = after_kb - before_kb
            if freed_kb >= 1024 * 1024:
                print("\n  Space freed: {:.1f} GB ({:,} KB)".format(freed_kb / (1024 * 1024), freed_kb))
            elif freed_kb >= 1024:
                print("\n  Space freed: {:.1f} MB ({:,} KB)".format(freed_kb / 1024, freed_kb))
            else:
                print("\n  Space freed: {:,} KB".format(freed_kb))
        elif before_kb is not None and after_kb is not None:
            print("\n  (Available space decreased — other activity on server; check df -h)")
        print("\nCleanup done. Run this script again without --clean to see new disk usage.")
    finally:
        try:
            if ssh:
                ssh.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
