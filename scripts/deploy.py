#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic deploy: upload files by manifest name, clear cache, restart services.
Usage:
  python scripts/deploy.py profile     # profile + auth
  python scripts/deploy.py sync        # sync + agent DB
  python scripts/deploy.py loading     # loading optimizations
  python scripts/deploy.py static_pages  # root index.html pages + entire static/ folder
  python scripts/deploy.py static_pages --upload-only   # upload only (no restart)
  python scripts/deploy.py battle_hunter_quick   # battle RPS/queue + Hunter XP + battle/profile UI + tournaments JS
  python scripts/deploy.py service_check_backend --upload-only   # leaderboard/agents/service_check files; no uwsgi restart
  python scripts/deploy.py --files path1 path2 ...
  python scripts/deploy.py --files debugger/index.html --upload-only   # upload only, no restart

SSH password: set DEPLOY_PASS, or run from an interactive terminal to be prompted
twice (enter + confirm); see deploy_ssh_env.require_deploy_pass.
"""
import os
import sys
import time
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

SERVER_HOST = deploy_host()
SERVER_USER = deploy_user()
SERVER_PASS = require_deploy_pass()
REMOTE_BASE = "/var/www/html"


def _static_pages_manifest():
    """Root site HTML (index.html + */index.html) and all files under static/ (excludes backup trees)."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    skip_dirs = {
        "backend", "vidgenerator", "vidgenerator.backup", "server_backup",
        ".git", "__pycache__", "node_modules", "mcps", ".cursor", "src",
    }
    idx_root = os.path.join(root, "index.html")
    if os.path.isfile(idx_root):
        out.append("index.html")
    try:
        for name in os.listdir(root):
            if name in skip_dirs or name.startswith("."):
                continue
            p = os.path.join(root, name)
            if not os.path.isdir(p):
                continue
            idx = os.path.join(p, "index.html")
            if os.path.isfile(idx):
                out.append(f"{name}/index.html")
    except OSError:
        pass
    mc = os.path.join(root, "dashboard", "master_control", "index.html")
    if os.path.isfile(mc):
        out.append("dashboard/master_control/index.html")
    static_dir = os.path.join(root, "static")
    if os.path.isdir(static_dir):
        for dirpath, dirnames, filenames in os.walk(static_dir):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if fn.startswith(".") or fn.endswith(".backup"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                out.append(rel)
    return sorted(set(out))


MANIFESTS = {
    "profile": [
        "vidgenerator/profile/index.html",
        "vidgenerator/static/js/backend-connector.js",
        "vidgenerator/static/js/image-support.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "backend/routes/social_auth_routes.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/missing_endpoints_routes.py",
    ],
    "sync": [
        "backend/services/unified_points_sync.py",
        "scripts/sync_database_migration.py",
        "backend/services/communication_psychology_service.py",
        "backend/services/dna_manipulation_system.py",
        "backend/services/user_engagement.py",
        "backend/services/agent_db_service.py",
        "backend/routes/missing_endpoints_routes.py",
        "docs/SYNC_AND_AGENT_KNOWLEDGE.md",
        "docs/TSS_AI_IMPLEMENTATION_GUIDE.md",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
        "data/rulebook_v16_sync.json",
    ],
    "loading": [
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "vidgenerator/unified_dashboard/index.html",
        "vidgenerator/profile/index.html",
        "vidgenerator/stats/index.html",
        "vidgenerator/generator/index.html",
        "vidgenerator/battle/index.html",
        "vidgenerator/shop/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
    ],
    # TTS (Piper/ElevenLabs/gTTS) + Audio Enhancement (DeepFilterNet/loudnorm) — pipeline + system overview
    "tts": [
        "backend/services/tts_service.py",
        "backend/services/audio_enhancement_service.py",
        "backend/services/video_generator_service.py",
        "backend/routes/system_overview_routes.py",
        "backend/routes/ai_providers_routes.py",
        "backend/routes/missing_endpoints_routes.py",
        "vidgenerator/debugger/index.html",
        "backend/templates/debugger/index.html",
        "docs/ENCODER_FREE_TIER.md",
    ],
    "generator": [
        "vidgenerator/generator/index.html",
        "vidgenerator/static/js/theme-timeline.js",
        "vidgenerator/static/css/theme-timeline.css",
        "vidgenerator/static/js/unified-generator-battle.js",
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/static/js/error-manager.js",
        "vidgenerator/static/js/service-worker-gatherer.js",
        "vidgenerator/static/css/navigation-toolbar.css",
        "vidgenerator/static/js/navigation-toolbar.js",
        "backend/routes/missing_endpoints_routes.py",
    ],
    # Minimal set for generator UI + routes + blueprint; only restarts uwsgi-vidgenerator
    "generator_recent": [
        "generator/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/generator_routes.py",
        "backend/routes/generator_shared.py",
        "backend/register_blueprints.py",
        "backend/services/video_generator_service.py",
        "backend/services/video_ai_bridge.py",
        "backend/services/agent_support_service.py",
        "backend/services/user_identification.py",
        "backend/run_generator_job.py",
    ],
    # Gallery + compact nav (no restart override; use full restart)
    "gallery_nav": [
        "gallery/index.html",
        "static/css/navigation-toolbar.css",
        "static/css/page-layout-metrics.css",
        "static/css/page-layout-metrics-debugger.css",
    ],
    # Star Map 25 upgrade: monitor, 50 projects, agent assignment, generator UI
    "starmap25": [
        "starmap25/index.html",
        "game/index.html",
        "generator/index.html",
        "backend/routes/star_map_routes.py",
        "backend/routes/debugger_agent_tasks_routes.py",
        "data/star_map_25.json",
        "data/starmap25_agent_projects.json",
        "data/starmap25_ai_proof_docs.json",
        "data/starmap25_walkthrough.json",
        "docs/STARMAP_25_50_PROJECTS.md",
        "docs/STARMAP25_UPGRADE_FINISH.md",
        "uwsgi.ini",
        ".uwsgi_touch_reload",
    ],
    # Rewind cleanup + deploy all commonly missing files (profile, sync, loading, tts, endpoints, blueprints, agent services)
    "rewind_missing": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/register_blueprints.py",
        "vidgenerator/profile/index.html",
        "vidgenerator/static/js/backend-connector.js",
        "vidgenerator/static/css/sync-status-widget.css",
        "vidgenerator/static/js/sync-status-widget.js",
        "vidgenerator/static/js/image-support.js",
        "backend/routes/social_auth_routes.py",
        "backend/routes/user_profile_routes.py",
        "backend/services/unified_points_sync.py",
        "scripts/sync_database_migration.py",
        "backend/services/communication_psychology_service.py",
        "backend/services/dna_manipulation_system.py",
        "backend/services/user_engagement.py",
        "backend/services/agent_db_service.py",
        "backend/services/agent_controller.py",
        "backend/services/agent_automation.py",
        "backend/services/agent_skillset.py",
        "backend/services/agent_groups.py",
        "backend/services/agent_ability_tracker.py",
        "vidgenerator/static/js/load-time-measurement.js",
        "vidgenerator/unified_dashboard/index.html",
        "vidgenerator/stats/index.html",
        "vidgenerator/generator/index.html",
        "vidgenerator/battle/index.html",
        "vidgenerator/shop/index.html",
        "backend/services/tts_service.py",
        "backend/services/audio_enhancement_service.py",
        "backend/services/video_generator_service.py",
        "backend/routes/system_overview_routes.py",
        "backend/routes/ai_providers_routes.py",
        "vidgenerator/debugger/index.html",
        "docs/SYNC_AND_AGENT_KNOWLEDGE.md",
        "docs/TSS_AI_IMPLEMENTATION_GUIDE.md",
        "docs/LOADING_AND_VIDGENERATOR_STATE.md",
        "docs/ENCODER_FREE_TIER.md",
        "data/rulebook_v16_sync.json",
    ],
    # Fix production 404s: routes + fallbacks + blueprint registration (see logs/production_404_deploy_checklist.txt)
    "fix_404": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/register_blueprints.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/user_account_routes.py",
        "backend/routes/battle_routes.py",
        "backend/routes/agent_automation_routes.py",
        "backend/routes/gallery_routes.py",
        "backend/routes/trophies_routes.py",
    ],
    # Quick battle (RPS / queue / Hunter XP), Hunters award_xp metadata, battle + profile UI, fantasy tournaments JS
    "battle_hunter_quick": [
        "backend/routes/battle_routes.py",
        "backend/routes/hunters_game.py",
        "battle/index.html",
        "profile/index.html",
        "static/js/enhanced-game-mechanics.js",
    ],
    # Important-only: 502/recursion fix (agent_ai_intelligence RecursionError, restart script log path, docs)
    "important": [
        "backend/services/agent_ai_intelligence.py",
        "backend/services/path_corrector.py",
        "backend/middleware/signal_processor_middleware.py",
        "scripts/restart_uwsgi_fix_502.py",
        "docs/SERVER_QUICK_REFERENCE.md",
        "src/app/__init__.py",
    ],
    # Full solution: generator safeJson, profile/game time & boosters, shop apply, fallbacks, docs
    "solution": [
        "vidgenerator/generator/index.html",
        "vidgenerator/profile/index.html",
        "vidgenerator/game/index.html",
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/shop_routes.py",
        "backend/services/unified_points_database.py",
        "backend/services/user_profile.py",
        "docs/PAGES_AND_FUNCTIONS_AUDIT.md",
        "docs/STARMAP_25_TOP10_IDEAS.md",
        "docs/AGENTS_SKILLS_SYNC.md",
    ],
    # API monitor dashboard (GET /api/) + disabled /vidgenerator/api
    "monitor": [
        "backend/routes/api_monitor_routes.py",
        "backend/routes/vidgenerator_disabled_routes.py",
        "backend/register_blueprints.py",
    ],
    # User location (GPS), themes, criticism skill, profile/generator/agents/gallery/aggregator UI
    "location_themes_recent": [
        "backend/services/user_location_service.py",
        "backend/routes/user_profile_routes.py",
        "backend/routes/hunters_game.py",
        "backend/services/agent_skillset.py",
        "backend/routes/missing_endpoints_routes.py",
        "profile/index.html",
        "generator/index.html",
        "theme_premium/index.html",
        "agents/index.html",
        "gallery/index.html",
        "aggregator/index.html",
        "static/js/theme-timeline.js",
        "docs/USER_LOCATION_GPS_SYSTEM.md",
        "docs/AGENT_SKILLS_AND_CONCLUSIONS.md",
        "docs/AGENTS_SKILLS_SYNC.md",
        "docs/MASTERNODER2_CRYPTO_INTEGRATION_PLAN.md",
    ],
    # MN2 401 fix: upload only .env + systemd units, install units, restart uwsgi-vidgenerator
    "mn2_env": [
        ".env",
        "systemd/uwsgi-vidgenerator.service",
        "systemd/uwsgi-vidgenerator-5001.service",
        "systemd/masternoder2d.service.example",
        "scripts/run_masternoder2d.sh",
        "scripts/run_masternoder2d.ps1",
        "cron/mn2_scan_deposits.sh",
        "cron/masternoder-mn2-scan.cron.d",
        "cron/mn2_accrue_rewards.sh",
        "cron/masternoder-mn2-accrue.cron.d",
    ],
    # MN2 staking system backend: services + routes + blueprint registration + config + ops script.
    # Frontend (profile/staking-monitor pages + static/js/mn2-*.js) ships via the "static_pages" manifest;
    # cron + .env ship via "mn2_env". Restarts uwsgi-vidgenerator to load the new Python.
    # NOTE: data/*.json here are CONFIG (safe to overwrite). Runtime state files (mn2_stakes.json,
    # mn2_ledger.json, reserve/rewards, onramp/p2p orders, agent_staking_agents.json) are intentionally
    # NOT deployed so the server's live state is never clobbered.
    "mn2_staking": [
        "backend/services/mn2_rpc_client.py",
        "backend/services/mn2_ledger.py",
        "backend/services/mn2_chainz.py",
        "backend/services/mn2_staking_service.py",
        "backend/services/mn2_staking_reconcile_service.py",
        "backend/services/mn2_staking_agents_service.py",
        "backend/services/mn2_onramp_service.py",
        "backend/services/mn2_p2p_service.py",
        "backend/services/unified_points_database.py",
        "backend/routes/mn2_routes.py",
        "backend/routes/mn2_staking_routes.py",
        "backend/routes/mn2_onramp_routes.py",
        "backend/routes/mn2_p2p_routes.py",
        "backend/routes/agent_staking_routes.py",
        "backend/register_blueprints.py",
        "data/mn2_staking_config.json",
        "data/mn2_staking_terms.json",
        "scripts/mn2_reconcile.py",
    ],
    # Reporter agent: knowledge-sharing ingredients cron (daily); set KNOWLEDGE_REPORT_SECRET in .env
    "knowledge_cron_env": [
        "cron/knowledge_sharing_report.sh",
        "cron/masternoder-knowledge-report.cron.d",
    ],
    # Agent platform crons (daily/weekly/monthly); set AGENT_CRON_SECRET — see docs/RESEARCH_AI_SYSTEMS.md
    "agents_cron_env": [
        "cron/agents_cron_daily.sh",
        "cron/agents_cron_weekly.sh",
        "cron/agents_cron_monthly.sh",
        "cron/agents_blueprint_route_fixer.sh",
        "cron/agents_api_service_skill.sh",
        "cron/masternoder-agents-daily.cron.d",
        "cron/masternoder-agents-weekly.cron.d",
        "cron/masternoder-agents-monthly.cron.d",
        "cron/masternoder-agents-blueprint-route.cron.d",
        "cron/masternoder-agents-api-service.cron.d",
    ],
    # MN2 daemon config (masternoder2.conf); deploy config folder to server
    "config": [
        "config/masternoder2.conf.example",
        "config/masternoder2.conf",
    ],
    # Optional: agent daemon (scripts/agent_daemon.py) + systemd unit example — install unit manually on server
    "agent_daemon_env": [
        "scripts/agent_daemon.py",
        "systemd/masternoder-agent-daemon.service.example",
    ],
    # Leaderboard + /agents routing fix + service check script (upload-only, then run service_check with --restart-uwsgi)
    "service_check_backend": [
        "backend/routes/missing_endpoints_routes.py",
        "backend/routes/leaderboard_routes.py",
        "backend/services/unified_points_database.py",
        "scripts/service_check_all_components.py",
        "docs/SERVICE_CHECK_LEADERBOARD_AGENTS_FIX.md",
    ],
}

# Built at import: every root */index.html + static/** (see _static_pages_manifest docstring)
MANIFESTS["static_pages"] = _static_pages_manifest()


# When using this manifest, only restart uwsgi-vidgenerator (not uwsgi emperor or python-proxy)
RESTART_VIDGENERATOR_ONLY_FOR = frozenset({
    "generator_recent",
    "monitor",
    "mn2_env",
    "mn2_staking",
    "config",
    "agent_daemon_env",
    "service_check_backend",
})
# HTML/CSS/JS under /var/www/html — clear nginx cache + reload nginx only (no uwsgi/python-proxy)
RESTART_NGINX_ONLY_FOR = frozenset({"static_pages"})


def run(files, upload_only=False, restart_services=None, manifest_name=None):
    ssh = None
    sftp = None
    try:
        print("=" * 60)
        print("DEPLOY:", " ".join(files[:3]) + (" ..." if len(files) > 3 else ""))
        if upload_only:
            print("(upload only — no cache clear, no restart)")
        print("=" * 60)
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()

        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(base)

        step = "[1/2]" if upload_only else "[1/4]"
        print(f"{step} Connecting...")
        ssh = __import__("paramiko").SSHClient()
        ssh.set_missing_host_key_policy(__import__("paramiko").AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()

        step = "[2/2]" if upload_only else "[2/4]"
        print(f"{step} Uploading files...")
        deployed = 0
        for local in files:
            if not os.path.exists(local):
                print(f"  [SKIP] {local} (missing)")
                continue
            remote = f"{REMOTE_BASE}/{local.replace(os.sep, '/')}"
            remote_dir = os.path.dirname(remote)
            try:
                ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=5)
                time.sleep(0.2)
            except Exception:
                pass
            try:
                with open(local, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                with sftp.file(remote, "w") as rf:
                    rf.write(content)
                print(f"  [OK] {local}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local}: {e}")
        sftp.close()
        print(f"  [SUMMARY] {deployed} files uploaded")
        print()

        # If we uploaded systemd units, install them so EnvironmentFile=.env is used
        systemd_units = [f for f in files if f.replace("\\", "/").startswith("systemd/") and f.endswith(".service")]
        if systemd_units and not upload_only:
            print("[2b] Installing systemd units...")
            for unit in ("uwsgi-vidgenerator.service", "uwsgi-vidgenerator-5001.service"):
                ssh.exec_command(f"cp {REMOTE_BASE}/systemd/{unit} /etc/systemd/system/ 2>/dev/null && echo OK", timeout=5)
                time.sleep(0.5)
            ssh.exec_command("systemctl daemon-reload", timeout=10)
            print("  [OK] systemd units installed and daemon-reloaded")
            print()

        # MN2 deposit scanner: executable + /etc/cron.d/ (manifest mn2_env)
        if manifest_name == "mn2_env" and not upload_only:
            print("[2c] MN2 scanner cron...")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/mn2_scan_deposits.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-mn2-scan.cron.d /etc/cron.d/masternoder-mn2-scan && chmod 644 /etc/cron.d/masternoder-mn2-scan",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command("test -f /etc/cron.d/masternoder-mn2-scan && echo OK", timeout=5)
            out = (stdout.read() or b"").decode().strip()
            if out == "OK":
                print("  [OK] /etc/cron.d/masternoder-mn2-scan (every 5 min)")
            else:
                print("  [WARN] cron.d install may have failed — check root and /etc/cron.d/")

            # MN2 staking reward accrual cron (hourly)
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/mn2_accrue_rewards.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-mn2-accrue.cron.d /etc/cron.d/masternoder-mn2-accrue && chmod 644 /etc/cron.d/masternoder-mn2-accrue",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command("test -f /etc/cron.d/masternoder-mn2-accrue && echo OK", timeout=5)
            out2 = (stdout.read() or b"").decode().strip()
            print("  [OK] /etc/cron.d/masternoder-mn2-accrue (hourly)" if out2 == "OK"
                  else "  [WARN] staking accrual cron.d install may have failed")
            print()

        if manifest_name == "knowledge_cron_env" and not upload_only:
            print("[2d] Knowledge-sharing report cron (reporter_agent)...")
            ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/knowledge_sharing_report.sh 2>/dev/null || true", timeout=5)
            ssh.exec_command(
                f"cp {REMOTE_BASE}/cron/masternoder-knowledge-report.cron.d /etc/cron.d/masternoder-knowledge-report && chmod 644 /etc/cron.d/masternoder-knowledge-report",
                timeout=10,
            )
            time.sleep(0.3)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /etc/cron.d/masternoder-knowledge-report && echo OK", timeout=5
            )
            out = (stdout.read() or b"").decode().strip()
            if out == "OK":
                print("  [OK] /etc/cron.d/masternoder-knowledge-report (daily)")
            else:
                print("  [WARN] knowledge cron.d install may have failed")
            print()

        if manifest_name == "agents_cron_env" and not upload_only:
            print("[2e] Agent platform crons (daily / weekly / monthly + blueprint/API)...")
            for sh in (
                "agents_cron_daily.sh",
                "agents_cron_weekly.sh",
                "agents_cron_monthly.sh",
                "agents_blueprint_route_fixer.sh",
                "agents_api_service_skill.sh",
            ):
                ssh.exec_command(f"chmod +x {REMOTE_BASE}/cron/{sh} 2>/dev/null || true", timeout=5)
            for cd, remote_name in (
                ("masternoder-agents-daily.cron.d", "masternoder-agents-daily"),
                ("masternoder-agents-weekly.cron.d", "masternoder-agents-weekly"),
                ("masternoder-agents-monthly.cron.d", "masternoder-agents-monthly"),
                ("masternoder-agents-blueprint-route.cron.d", "masternoder-agents-blueprint-route"),
                ("masternoder-agents-api-service.cron.d", "masternoder-agents-api-service"),
            ):
                ssh.exec_command(
                    f"cp {REMOTE_BASE}/cron/{cd} /etc/cron.d/{remote_name} && chmod 644 /etc/cron.d/{remote_name}",
                    timeout=10,
                )
                time.sleep(0.15)
            print("  [OK] /etc/cron.d/masternoder-agents-* (daily, weekly, monthly, blueprint-route, api-service)")
            print()

        if upload_only:
            print("=" * 60)
            print("UPLOAD COMPLETE (no restart)")
            print("=" * 60)
            ssh.close()
            return True

        print("[3/4] Clearing cache...")
        ssh.exec_command(
            f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command(
            f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
            timeout=30,
        )
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>/dev/null || true", timeout=10)
        print("  [OK] Cache cleared")
        print()

        print("[4/4] Restarting services...")
        wait_s = 8
        if restart_services is not None and restart_services == ["__nginx_static__"]:
            ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
            ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
            print("  [OK] Nginx reloaded (static_pages deploy; uwsgi not restarted)")
        elif restart_services is not None:
            for svc in restart_services:
                ssh.exec_command(f"systemctl restart {svc} 2>&1 || true", timeout=20)
                time.sleep(wait_s)
        else:
            ssh.exec_command("systemctl restart python-proxy 2>&1 || true", timeout=20)
            time.sleep(wait_s)
            for uwsgi_unit in (
                "uwsgi-vidgenerator",
                "uwsgi-vidgenerator-5001",
                "uwsgi",
            ):
                ssh.exec_command(f"systemctl restart {uwsgi_unit} 2>&1 || true", timeout=20)
                time.sleep(wait_s)
        for port in (5000, 5001):
            for _ in range(6):
                try:
                    stdin, stdout, stderr = ssh.exec_command(
                        f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/casino/ 2>/dev/null || echo 000",
                        timeout=10,
                    )
                    out = (stdout.read() or b"").decode().strip()
                    if out and out != "000":
                        try:
                            c = int(out)
                            if 200 <= c < 600 or c in (301, 302):
                                print(f"  [OK] Upstream :{port}/casino/ -> {c}")
                                break
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(3)
            else:
                print(f"  [WARN] Upstream :{port} not ready (or /casino/ check timed out)")
        ssh.exec_command("nginx -t 2>&1 || true", timeout=10)
        ssh.exec_command("systemctl reload nginx 2>&1 || systemctl restart nginx 2>&1 || true", timeout=15)
        print("  [OK] Services restarted")
        print()
        print("=" * 60)
        print("DEPLOY COMPLETE")
        print("=" * 60)
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if ssh:
            try:
                ssh.close()
            except Exception:
                pass
        return False


def main():
    args = sys.argv[1:]
    upload_only = "--upload-only" in args
    if upload_only:
        args = [a for a in args if a != "--upload-only"]
    if not args:
        print("Usage: python scripts/deploy.py <manifest> [--upload-only] | --files path1 path2 [--upload-only]")
        print("  --upload-only  SFTP files to the server only (no cache clear, no systemd/cron hooks, no service restart).")
        print("Manifests:", ", ".join(MANIFESTS))
        sys.exit(1)
    manifest_name = None
    if args[0] == "--files":
        files = args[1:]
        if not files:
            print("--files requires at least one path")
            sys.exit(1)
    else:
        name = args[0].lower()
        if name not in MANIFESTS:
            print("Unknown manifest:", name, "| known:", ", ".join(MANIFESTS))
            sys.exit(1)
        manifest_name = name
        files = MANIFESTS[name]
    restart_services = None
    if manifest_name and manifest_name in RESTART_VIDGENERATOR_ONLY_FOR:
        restart_services = ["uwsgi-vidgenerator"]
        print("(Restart: uwsgi-vidgenerator only)")
    elif manifest_name and manifest_name in RESTART_NGINX_ONLY_FOR and not upload_only:
        restart_services = ["__nginx_static__"]
        print("(Restart: nginx reload only — static HTML/CSS/JS)")
    ok = run(files, upload_only=upload_only, restart_services=restart_services, manifest_name=manifest_name)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
