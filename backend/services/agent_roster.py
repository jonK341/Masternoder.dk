"""Which catalog agents can actually run, and which sites fold into a shorter map.

The skillset lists many named agents. Only the bindings below have a service
already in the process. Everything else stays unused instead of being wrapped
in an empty shell. Off-nav pages are grouped the same way: linked, folded into
a page that already covers them, archived lore, or kept because nothing else
covers them.
"""
import importlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

_NAV_URL = re.compile(r"""APP_BASE\s*\+\s*['"]([^'"]+)['"]""")
_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)

# Directories that are code or assets, not public sites.
_SKIP_DIRS = {
    ".git",
    ".venv",
    "backend",
    "content",
    "data",
    "docs",
    "logs",
    "migrations",
    "mobile",
    "node_modules",
    "scripts",
    "src",
    "static",
    "tests",
}

# Catalog names with no service. Dropped from the skillset and the roster.
RETIRED_AGENT_IDS = frozenset({
    "ai_trainer_agent",
    "backup_agent",
    "collaboration_agent",
    "communication_agent",
    "compliance_agent",
    "data_processor_agent",
    "deployment_agent",
    "innovation_agent",
    "intelligence_aggregator_agent",
    "learning_agent",
    "master_dashboard_agent",
    "notification_agent",
    "quality_assurance_agent",
    "resource_manager_agent",
    "scanner_agent",
    "tester_agent",
    "tts_narration_agent",
    "workflow_agent",
})


def without_retired(catalog, retired=None):
    """Return catalog entries that still have a reason to exist."""
    blocked = RETIRED_AGENT_IDS if retired is None else retired
    return {
        agent_id: meta
        for agent_id, meta in (catalog or {}).items()
        if agent_id not in blocked
    }


# skillset id -> the agent that already does this job
AGENT_ALIASES = {
    "content_ai_agent": "content_generator_agent",
    "video_ai_agent": "content_generator_agent",
    "security_audit_agent": "security_agent",
    "performance_agent": "performance_optimizer_agent",
    "agent_research_tracker_agent": "research_agent",
    "support_ticket_agent": "support",
}

# Real services. startable loops are not started until asked.
RUNTIME_BINDINGS = (
    {"agent_id": "master_fix_agent", "controller_key": "master_fix", "module": "backend.services.master_fix_agent_skills", "attr": "master_fix_agent_skills", "startable": False, "name": "Master Fix Agent"},
    {"agent_id": "monitoring_agent", "controller_key": "api_monitoring", "module": "backend.services.api_monitoring_agent", "attr": "api_monitoring_agent", "startable": False, "name": "Monitoring Agent"},
    {"agent_id": "content_generator_agent", "controller_key": "content_generator", "module": "backend.services.agent_content_generator", "attr": "agent_content_generator", "startable": False, "name": "Content Generator Agent"},
    {"agent_id": "battle_strategy_agent", "controller_key": "battle_strategy", "module": "backend.services.agent_battle_strategy", "attr": "agent_battle_strategy", "startable": False, "name": "Battle Strategy Agent"},
    {"agent_id": "social_engagement_agent", "controller_key": "social_engagement", "module": "backend.services.agent_social_engagement", "attr": "agent_social_engagement", "startable": False, "name": "Social Engagement Agent"},
    {"agent_id": "analytics_agent", "controller_key": "analytics", "module": "backend.services.agent_analytics", "attr": "agent_analytics", "startable": False, "name": "Analytics Agent"},
    {"agent_id": "security_agent", "controller_key": "security", "module": "backend.services.agent_security", "attr": "agent_security", "startable": False, "name": "Security Agent"},
    {"agent_id": "performance_optimizer_agent", "controller_key": "performance_optimizer", "module": "backend.services.agent_performance_optimizer", "attr": "agent_performance_optimizer", "startable": False, "name": "Performance Optimizer Agent"},
    {"agent_id": "user_experience_agent", "controller_key": "user_experience", "module": "backend.services.agent_user_experience", "attr": "agent_user_experience", "startable": False, "name": "User Experience Agent"},
    {"agent_id": "integration_agent", "controller_key": "integration", "module": "backend.services.agent_integration", "attr": "agent_integration", "startable": False, "name": "Integration Agent"},
    {"agent_id": "research_agent", "controller_key": "research", "module": "backend.services.agent_research_tracker", "attr": "agent_research_tracker", "startable": False, "name": "Research Agent"},
    {"agent_id": "agent_judge", "controller_key": "judge", "module": "backend.services.agent_judge", "attr": "agent_judge", "startable": False, "name": "Agent Judge"},
    {"agent_id": "ai_intelligence_agent", "controller_key": "ai_intelligence", "module": "backend.services.agent_ai_intelligence", "attr": "agent_ai_intelligence", "startable": False, "name": "AI Intelligence Agent"},
    {"agent_id": "llm_orchestrator_agent", "controller_key": "llm_orchestrator", "module": "backend.services.agent_ai_orchestrator", "attr": "agent_ai_orchestrator", "startable": False, "name": "LLM Orchestrator Agent"},
    {"agent_id": "error_migration_agent", "controller_key": "error_handler", "module": "backend.services.agent_error_handler", "attr": "agent_error_handler", "startable": False, "name": "Error Migration Agent"},
    {"agent_id": "support", "controller_key": "support", "module": "backend.services.agent_support_service", "attr": "agent_support_service", "startable": False, "name": "Support"},
    {"agent_id": "trigger", "controller_key": "trigger", "module": "backend.services.agent_trigger_system", "attr": "agent_trigger_system", "startable": False, "name": "Trigger System"},
    {"agent_id": "python_executor", "controller_key": "python_executor", "module": "backend.services.agent_python_executor", "attr": "agent_python_executor", "startable": False, "name": "Python Executor"},
    {"agent_id": "manager", "controller_key": "manager", "module": "backend.services.agent_manager", "attr": "agent_manager", "startable": False, "name": "Agent Manager"},
    {"agent_id": "secretary", "controller_key": "secretary", "module": "backend.services.agent_secretary", "attr": "agent_secretary", "startable": False, "name": "Agent Secretary"},
    {"agent_id": "automation", "controller_key": "automation", "module": "backend.services.agent_automation", "attr": "agent_automation", "startable": True, "name": "Automation"},
    {"agent_id": "activation", "controller_key": "activation", "module": "backend.services.agent_activation_system", "attr": "agent_activation_system", "startable": True, "name": "Activation"},
)

# Off-nav page -> (canonical path, why it is not its own destination)
SITE_FOLDS = {
    "points": ("profile", "Points already live on Profile."),
    "stats": ("profile", "Stats already live on Profile."),
    "leaderboards": ("profile", "Leaderboards already live on Profile."),
    "user": ("profile", "The account page is Profile."),
    "dashboard": ("profile", "The all-points dashboard duplicates Profile."),
    "unified_dashboard": ("dashboard/agents_control", "Ops dashboards share Agents Control."),
    "dashboard/master_control": ("dashboard/agents_control", "Ops dashboards share Agents Control."),
    "analytics": ("aggregator", "Monitoring already lives on the Aggregator."),
    "command-center": ("dashboard/agents_control", "Ops dashboards share Agents Control."),
    "business-control": ("dashboard/agents_control", "Ops dashboards share Agents Control."),
    "theme_premium": ("generator", "Themes are chosen in the generator."),
    "theme-points": ("generator", "Theme points are part of generation."),
    "editor": ("generator", "Clip editing continues in the generator."),
    "creator": ("create-app", "The encoder flow is Create App."),
    "monetization": ("shop", "Income and checkout live in the shop."),
    "chat": ("social", "Chat is part of Social."),
    "forum": ("social", "The forum is part of Social."),
    "social-monitor": ("social", "Social monitoring is part of Social."),
    "staking-monitor": ("staking-leaderboard", "Staking status is the leaderboard."),
    "proof-of-reserves": ("explorer", "Reserves are part of the MN2 explorer."),
    "beta_testing": ("lab", "Beta tools live in the Lab."),
    "advanced_calculator": ("lab", "The calculator lives in the Lab."),
    "champions-league": ("battle", "League standings are part of Battle."),
    "fleet-progress-monitor": ("starmap25", "The fleet monitor is the star map."),
    "streamer": ("podcast", "The stream surface is the podcast."),
    "terms": ("legal/terms", "Terms already have a legal page."),
    "discord-play": ("casino", "Discord play is the casino."),
}

SITE_ARCHIVE = (
    "academic-perspective",
    "danish-divine-tech-tree",
    "metal",
    "milkyway",
    "rights-law",
    "time-achievement-guides",
    "victory-tech-tree",
)

_PROBE_CACHE = None


class BoundAgent:
    """Controller entry that always has get_status, even when the service does not."""

    def __init__(self, agent_id, name, instance):
        self.agent_id = agent_id
        self.name = name
        self.instance = instance

    def get_status(self):
        detail = {}
        if hasattr(self.instance, "get_status"):
            try:
                detail = self.instance.get_status() or {}
            except Exception as exc:
                detail = {"error": str(exc)}
        if not isinstance(detail, dict):
            detail = {"value": detail}
        running = getattr(self.instance, "running", None)
        if running is None:
            running = detail.get("running", True)
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "running": bool(running),
            "detail": detail,
        }

    def __getattr__(self, item):
        return getattr(self.instance, item)


def nav_paths_from_source(source):
    """Return sorted site paths declared as APP_BASE + '/path' in the nav toolbar."""
    found = set()
    for match in _NAV_URL.finditer(source or ""):
        raw = match.group(1).split("?", 1)[0].strip("/")
        if raw:
            found.add(raw)
    return sorted(found)


def _norm(path):
    return str(path or "").split("?", 1)[0].strip().strip("/")


def _listed_running(probe):
    if probe.get("running") is None:
        return not probe.get("startable")
    return bool(probe.get("running"))


def _instance_running(probe):
    instance = probe.get("instance")
    if instance is not None and hasattr(instance, "running"):
        return bool(instance.running)
    return _listed_running(probe)


def classify_agents(catalog, probes, aliases=None):
    """Label each catalog agent active, idle, unused, alias, or blocked."""
    aliases = AGENT_ALIASES if aliases is None else aliases
    probes = probes or {}
    rows = []
    for agent_id in sorted(catalog or {}):
        meta = catalog.get(agent_id) or {}
        name = meta.get("name") or agent_id
        if agent_id in aliases:
            rows.append({
                "agent_id": agent_id,
                "name": name,
                "state": "alias",
                "alias_of": aliases[agent_id],
            })
            continue
        probe = probes.get(agent_id)
        if not probe:
            rows.append({
                "agent_id": agent_id,
                "name": name,
                "state": "unused",
                "note": "Named in the skillset, with no service to run.",
            })
            continue
        label = probe.get("name") or name
        if not probe.get("loadable"):
            rows.append({
                "agent_id": agent_id,
                "name": label,
                "state": "blocked",
                "error": probe.get("error") or "unavailable",
            })
            continue
        state = "idle" if probe.get("startable") and not _listed_running(probe) else "active"
        row = {"agent_id": agent_id, "name": label, "state": state}
        if state == "idle":
            row["note"] = "Service is loaded. Its background loop is stopped."
        rows.append(row)
    return rows


def classify_sites(pages, nav_paths, folds=None, archived=None):
    """Split pages into linked, folded, archived, kept, and vidgenerator mirrors."""
    fold_map = SITE_FOLDS if folds is None else folds
    archive = set(SITE_ARCHIVE if archived is None else archived)
    nav = {_norm(path) for path in nav_paths or []}
    page_set = {_norm(path) for path in pages or []}
    known = page_set | nav | set(fold_map) | archive

    linked = []
    folded = []
    archived_rows = []
    keep = []
    mirrors = []
    for path in sorted(page_set):
        if path.startswith("vidgenerator/"):
            original = path.split("/", 1)[1]
            if original in known:
                mirrors.append({"path": path, "of": original})
                continue
        if path in nav:
            linked.append(path)
            continue
        if path in fold_map:
            into, reason = fold_map[path]
            folded.append({"path": path, "into": into, "reason": reason})
            continue
        if path in archive:
            archived_rows.append(path)
            continue
        keep.append(path)
    return {
        "linked": linked,
        "folded": folded,
        "archived": archived_rows,
        "keep": keep,
        "mirrors": mirrors,
    }


def build_recap(catalog, probes, aliases, pages, nav_paths):
    agents = classify_agents(catalog, probes, aliases)
    counts = {"active": 0, "idle": 0, "unused": 0, "alias": 0, "blocked": 0}
    for row in agents:
        counts[row["state"]] = counts.get(row["state"], 0) + 1
    sites = classify_sites(pages, nav_paths)
    sites["counts"] = {
        "linked": len(sites["linked"]),
        "folded": len(sites["folded"]),
        "archived": len(sites["archived"]),
        "keep": len(sites["keep"]),
        "mirrors": len(sites["mirrors"]),
    }
    return {"counts": counts, "agents": agents, "sites": sites}


def _prime_loop(instance):
    """Stamp empty schedules so the first loop tick waits for its interval."""
    if hasattr(instance, "prime_schedules"):
        instance.prime_schedules()
        return
    activations = getattr(instance, "activations", None)
    if not isinstance(activations, dict):
        return
    last = activations.setdefault("last_activations", {})
    now = datetime.now().isoformat()
    for act in activations.get("auto_activations") or []:
        activation_id = act.get("id")
        if activation_id and not last.get(activation_id):
            last[activation_id] = now
    save = getattr(instance, "save_activations", None)
    if callable(save):
        save()


def _bind(controller, agent_id, controller_key, instance, name):
    bound = BoundAgent(agent_id, name, instance)
    controller.agents[agent_id] = bound
    if controller_key and controller_key != agent_id:
        controller.agents[controller_key] = bound
    data = getattr(controller, "data", None)
    if isinstance(data, dict):
        registered = list(data.get("agents_registered") or [])
        for key in (agent_id, controller_key):
            if key and key not in registered:
                registered.append(key)
        data["agents_registered"] = registered
        data["total_agents"] = len(controller.agents)


def activate_existing(probes, controller=None, start_loops=False):
    """Register loadable services. Start background loops only when asked."""
    started = []
    registered = []
    skipped = []
    errors = []
    already = []
    for agent_id in sorted(probes or {}):
        probe = probes[agent_id] or {}
        name = probe.get("name") or agent_id
        instance = probe.get("instance")
        if not probe.get("loadable") or instance is None:
            skipped.append(agent_id)
            if probe.get("error"):
                errors.append({"agent": agent_id, "error": probe["error"]})
            continue
        startable = bool(probe.get("startable"))
        running = _instance_running(probe)
        if startable and not running:
            if not start_loops:
                skipped.append(agent_id)
                continue
            try:
                _prime_loop(instance)
                if hasattr(instance, "start"):
                    instance.start()
                probe["running"] = True
                started.append(agent_id)
            except Exception as exc:
                errors.append({"agent": agent_id, "error": str(exc)})
                skipped.append(agent_id)
                continue
        elif startable:
            already.append(agent_id)
        if controller is not None:
            _bind(
                controller,
                agent_id,
                probe.get("controller_key") or agent_id,
                instance,
                name,
            )
        registered.append(agent_id)
    if controller is not None and hasattr(controller, "save_data"):
        controller.save_data()
    return {
        "success": True,
        "started": started,
        "registered": registered,
        "skipped": skipped,
        "already_running": already,
        "errors": errors,
    }


def discover_site_pages(root):
    """Public pages: directories that contain index.html, with their titles."""
    root = Path(root)
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        parts = [] if rel == "." else rel.split(os.sep)
        dirnames[:] = [
            name for name in dirnames
            if name not in _SKIP_DIRS and not name.startswith(".") and name != "vidgenerator"
        ]
        if any(part in _SKIP_DIRS or part.startswith(".") for part in parts):
            dirnames[:] = []
            continue
        if len(parts) > 2:
            dirnames[:] = []
            continue
        if "index.html" not in filenames or not parts:
            continue
        title = ""
        try:
            text = (Path(dirpath) / "index.html").read_text(encoding="utf-8", errors="ignore")[:4000]
            match = _TITLE.search(text)
            if match:
                title = re.sub(r"\s+", " ", match.group(1)).strip()
        except OSError:
            title = ""
        found.append({"path": "/".join(parts), "title": title})
    found.sort(key=lambda row: row["path"])
    return found


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _import_probe(binding):
    meta = {
        "name": binding.get("name") or binding["agent_id"],
        "startable": bool(binding.get("startable")),
        "controller_key": binding.get("controller_key") or binding["agent_id"],
    }
    try:
        module = importlib.import_module(binding["module"])
        instance = getattr(module, binding["attr"])
    except Exception as exc:
        return {**meta, "loadable": False, "running": None, "error": str(exc)}
    running = bool(getattr(instance, "running", False)) if meta["startable"] else None
    return {**meta, "loadable": True, "running": running, "instance": instance, "error": None}


def probe_bindings(bindings=None, refresh=False):
    """Import each runtime binding once, then refresh loop running flags."""
    global _PROBE_CACHE
    source = RUNTIME_BINDINGS if bindings is None else bindings
    if bindings is None and _PROBE_CACHE is not None and not refresh:
        for probe in _PROBE_CACHE.values():
            instance = probe.get("instance")
            if probe.get("startable") and instance is not None:
                probe["running"] = bool(getattr(instance, "running", False))
        return _PROBE_CACHE
    probed = {binding["agent_id"]: _import_probe(binding) for binding in source}
    if bindings is None:
        _PROBE_CACHE = probed
    return probed


def _names_only(agents):
    named = {}
    for agent_id, meta in (agents or {}).items():
        if not isinstance(meta, dict):
            continue
        named[agent_id] = {"name": meta.get("name") or agent_id}
    return named


def _live_catalog(probes):
    """Names only. Do not construct AgentSkillset(); its init rewrites the skill file."""
    catalog = {}
    path = _repo_root() / "logs" / "agent_skillsets" / "skillsets.json"
    try:
        if path.is_file():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            catalog = _names_only(loaded.get("agents"))
    except (OSError, ValueError, TypeError):
        catalog = {}
    if not catalog:
        from backend.services.agent_skillset import AgentSkillset
        catalog = _names_only(AgentSkillset._default_skillsets(None).get("agents"))
    for agent_id, probe in probes.items():
        catalog.setdefault(agent_id, {"name": probe.get("name") or agent_id})
    return without_retired(catalog)


def _live_pages_and_nav():
    root = _repo_root()
    discovered = discover_site_pages(root)
    pages = [row["path"] for row in discovered]
    titles = {row["path"]: row["title"] for row in discovered}
    nav_file = root / "static" / "js" / "navigation-toolbar.js"
    try:
        nav = nav_paths_from_source(nav_file.read_text(encoding="utf-8", errors="ignore"))
    except OSError:
        nav = []
    return pages, titles, nav


def live_recap():
    """Read-only recap. Does not start loops."""
    probes = probe_bindings()
    pages, titles, nav = _live_pages_and_nav()
    recap = build_recap(_live_catalog(probes), probes, AGENT_ALIASES, pages, nav)
    recap["sites"]["keep_detail"] = [
        {"path": path, "title": titles.get(path, "")}
        for path in recap["sites"]["keep"]
    ]
    for row in recap["sites"]["folded"]:
        row["title"] = titles.get(row["path"], "")
    recap["success"] = True
    return recap


def live_activate(start_loops=False):
    """Attach existing services to the controller. Optionally start their loops."""
    probes = probe_bindings(refresh=True)
    try:
        # Lazy: the controller imports the same services and must not import this module at load.
        from backend.services.agent_controller import agent_controller
        controller = agent_controller
    except Exception as exc:
        controller = None
        controller_error = str(exc)
    else:
        controller_error = None
    result = activate_existing(probes, controller=controller, start_loops=start_loops)
    if controller_error:
        result["errors"].append({"agent": "controller", "error": controller_error})
        result["success"] = False
    result["recap"] = live_recap()
    return result
