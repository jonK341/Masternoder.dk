#!/usr/bin/env python3
"""Generate self-hosted profile pictures (avatars) for platform agents.

Each agent gets a unique, deterministic robot avatar from DiceBear's "bottts"
style, seeded by the agent_id and tinted with the agent's theme color. The SVGs
are saved under static/img/agents/<agent_id>.svg and served at
/static/img/agents/<agent_id>.svg.

Why a script (and not a runtime call): avatars are self-hosted so the live site
has no external dependency, loads fast, and works offline. Re-run this script
whenever you add a new agent to AGENT_COLORS below.

Usage:
    python scripts/generate_agent_avatars.py          # only fetch missing files
    python scripts/generate_agent_avatars.py --force  # re-fetch everything
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(BASE_DIR, "static", "img", "agents")

DICEBEAR_STYLE = "bottts"  # friendly robot characters, fitting for AI agents
DICEBEAR_BASE = f"https://api.dicebear.com/9.x/{DICEBEAR_STYLE}/svg"

# Single source of truth: agent_id -> theme color (hex, no leading '#').
# Mirrors the icons/colors in backend/services/agent_db_service.py (_AGENT_DISPLAY)
# and the SYSTEM_AGENTS array in agents/index.html. Add new agents here.
AGENT_COLORS = {
    "content_generator_agent": "00ff88",
    "analytics_agent": "00d4ff",
    "battle_strategy_agent": "ff6b35",
    "social_engagement_agent": "a855f7",
    "master_fix_agent": "fbbf24",
    "monitoring_agent": "60a5fa",
    "scanner_agent": "34d399",
    "security_agent": "f87171",
    "performance_optimizer_agent": "fb923c",
    "user_experience_agent": "c084fc",
    "learning_agent": "38bdf8",
    "reporter_agent": "f472b6",
    "ai_intelligence_agent": "818cf8",
    "tester_agent": "4ade80",
    "error_migration_agent": "facc15",
    "master_dashboard_agent": "22d3ee",
    "integration_agent": "2dd4bf",
    "workflow_agent": "fb7185",
    "ai_trainer_agent": "a3e635",
    "quality_assurance_agent": "84cc16",
    "deployment_agent": "f59e0b",
    "backup_agent": "94a3b8",
    "resource_manager_agent": "eab308",
    "compliance_agent": "e879f9",
    "communication_agent": "0ea5e9",
    "research_agent": "14b8a6",
    "innovation_agent": "fde047",
    "collaboration_agent": "fb923c",
    "data_processor_agent": "64748b",
    "notification_agent": "f43f5e",
    "agent_judge": "d946ef",
}


def avatar_url(agent_id: str, color: str) -> str:
    params = {
        "seed": agent_id,
        "backgroundColor": color,
        "backgroundType": "gradientLinear,solid",
        "radius": "50",
    }
    return f"{DICEBEAR_BASE}?{urllib.parse.urlencode(params)}"


def fetch(url: str, retries: int = 3, timeout: int = 25) -> bytes:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "masternoder-avatar-gen/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001 - network errors vary
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * attempt)
    raise RuntimeError(f"failed after {retries} attempts: {last_err}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate agent avatar SVGs.")
    parser.add_argument("--force", action="store_true", help="re-fetch even if file exists")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Writing avatars to: {OUT_DIR}")

    created = skipped = failed = 0
    for agent_id, color in AGENT_COLORS.items():
        out_path = os.path.join(OUT_DIR, f"{agent_id}.svg")
        if os.path.exists(out_path) and not args.force:
            skipped += 1
            continue
        try:
            data = fetch(avatar_url(agent_id, color))
            if not data.lstrip().startswith(b"<svg"):
                raise ValueError("response was not an SVG")
            with open(out_path, "wb") as fh:
                fh.write(data)
            created += 1
            print(f"  + {agent_id}.svg ({len(data)} bytes)")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ! {agent_id}: {e}", file=sys.stderr)

    print(f"\nDone. created={created} skipped={skipped} failed={failed} total={len(AGENT_COLORS)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
