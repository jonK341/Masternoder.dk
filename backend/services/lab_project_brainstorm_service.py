"""
Multi-agent brainstorm for Lab seed projects (Google Play TWA, social hub, etc.).
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

BRAINSTORM_COOLDOWN_SEC = 3600

_AGENT_LINES: Dict[str, str] = {
    "google_play_agent": "Map TWA scope: asset links, Play Console listing, and deep links to /lab and /casino.",
    "lab_create_agent": "Scaffold v1 with Bubblewrap — single activity, no duplicate auth; ship internal test track first.",
    "lab_research_agent": "Research Play policy for virtual rewards, MN2 tips, and 18+ surfaces before store copy.",
    "lab_update_agent": "Plan weekly release notes tied to lab_projects_seed progress and Chapter V unlocks.",
    "lab_ip_agent": "Verify MasterNoder trademark, icon assets, and screenshot rights before public listing.",
    "co_tech_agent": "Draft co-tech row for mobile shell + PWA sync; link to rulebook_v16_sync.",
    "lab_project_agent": "Break v1 into: manifest, signing, internal test, production rollout checklist.",
    "social_roundtable_agent": "Social launch: Discord spotlight + lab roundtable thread for beta testers.",
    "roundtable_agent": "Schedule roundtable review after first internal Play build.",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _agent_line(agent_id: str, project: Dict[str, Any]) -> str:
    aid = (agent_id or "lab_project_agent").strip()
    custom = _AGENT_LINES.get(aid)
    if custom:
        return custom
    title = project.get("title") or "project"
    return f"{aid}: contribute one concrete deliverable for «{title}» this sprint."


def run_brainstorm(
    *,
    user_id: str,
    seed: Dict[str, Any],
    profile: Dict[str, Any],
    use_llm: bool = False,
) -> Dict[str, Any]:
    seed_id = str(seed.get("id") or "")
    agents = [a for a in (seed.get("assigned_agents") or []) if a]
    if not agents:
        agents = ["lab_project_agent", "lab_research_agent"]

    cooldowns = profile.get("lab_brainstorm_cooldowns")
    if not isinstance(cooldowns, dict):
        cooldowns = {}
    until_raw = cooldowns.get(seed_id)
    if until_raw:
        try:
            until = datetime.fromisoformat(str(until_raw).replace("Z", "+00:00"))
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
            if _now() < until:
                remain = int((until - _now()).total_seconds())
                return {"success": False, "error": "brainstorm_cooldown", "cooldown_sec": remain}
        except Exception:
            pass

    ideas: List[Dict[str, Any]] = []
    for aid in agents[:8]:
        ideas.append({
            "agent_id": aid,
            "line": _agent_line(aid, seed),
            "source": "heuristic",
        })

    synthesis = (
        f"Brainstorm for «{seed.get('title')}»: {len(ideas)} agent lines. "
        f"Next: pick one reference link, one acceptance test, one ship date."
    )

    if use_llm:
        try:
            from backend.services.agent_ai_router import routed_chat
            prompt = (
                "Return 3 short bullet lines (plain text, one per line) for a lab mobile app brainstorm. "
                f"Project: {seed.get('question') or seed.get('title')}. Agents: {', '.join(agents)}."
            )
            resp, _meta = routed_chat([{"role": "user", "content": prompt}], "chat_general", user_id)
            if resp and getattr(resp, "success", False) and getattr(resp, "content", ""):
                for i, line in enumerate(str(resp.content).strip().splitlines()[:3]):
                    line = line.lstrip("-• ").strip()
                    if line:
                        ideas.append({"agent_id": "llm_copilot", "line": line, "source": "llm"})
                synthesis = "LLM-augmented brainstorm merged with agent heuristics."
        except Exception:
            pass

    store = profile.get("lab_project_brainstorms")
    if not isinstance(store, dict):
        store = {}
    entry = {
        "seed_id": seed_id,
        "at": _now().isoformat(),
        "ideas": ideas,
        "synthesis": synthesis,
    }
    store[seed_id] = entry
    profile["lab_project_brainstorms"] = store
    cooldowns[seed_id] = (_now() + timedelta(seconds=BRAINSTORM_COOLDOWN_SEC)).isoformat()
    profile["lab_brainstorm_cooldowns"] = cooldowns

    return {
        "success": True,
        "seed_id": seed_id,
        "brainstorm": entry,
        "cooldown_sec": BRAINSTORM_COOLDOWN_SEC,
    }
