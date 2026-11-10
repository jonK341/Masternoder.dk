"""Product layer for **The Profit Daemon Jon** — top-25 tech install + release metadata."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_PRODUCT_DIR = os.path.join(ex._BASE, "profit_daemon_jon")
_CATALOG = os.path.join(_PRODUCT_DIR, "top25_technologies.json")
_STATE = os.path.join(ex._DATA_DIR, "profit_daemon_jon_tech.json")
_PRODUCT = os.path.join(_PRODUCT_DIR, "PRODUCT.json")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def product_meta() -> Dict[str, Any]:
    meta = _read_json(_PRODUCT, {})
    version_path = os.path.join(_PRODUCT_DIR, "VERSION")
    if os.path.isfile(version_path):
        meta["version"] = open(version_path, encoding="utf-8").read().strip() or meta.get("version")
    meta["product_dir"] = _PRODUCT_DIR
    return meta


def load_catalog() -> Dict[str, Any]:
    return _read_json(_CATALOG, {"technologies": []})


def install_state() -> Dict[str, Any]:
    state = _read_json(_STATE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("installed", {})
    state.setdefault("product", "The Profit Daemon Jon")
    return state


def _pip_install(pkgs: List[str], *, python_bin: Optional[str] = None) -> Dict[str, Any]:
    if not pkgs:
        return {"ok": True, "skipped": True}
    py = python_bin or sys.executable
    cmd = [py, "-m", "pip", "install", "--quiet", *pkgs]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        return {
            "ok": proc.returncode == 0,
            "cmd": cmd,
            "stdout": (proc.stdout or "")[-500:],
            "stderr": (proc.stderr or "")[-500:],
            "code": proc.returncode,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def _module_ok(module: str) -> bool:
    if not module:
        return True
    try:
        __import__(module)
        return True
    except Exception:
        return False


def install_top25(
    *,
    keys: Optional[List[str]] = None,
    pip: bool = True,
    python_bin: Optional[str] = None,
) -> Dict[str, Any]:
    """Install/mark the top-25 technologies into local product state."""
    catalog = load_catalog()
    techs = list(catalog.get("technologies") or [])
    if keys:
        want = {str(k) for k in keys}
        techs = [t for t in techs if str(t.get("key")) in want]
    state = install_state()
    installed = dict(state.get("installed") or {})
    results: List[Dict[str, Any]] = []
    for tech in techs:
        key = str(tech.get("key") or tech.get("id"))
        row: Dict[str, Any] = {"key": key, "title": tech.get("title"), "id": tech.get("id")}
        pip_pkgs = [str(p) for p in (tech.get("pip") or []) if str(p).strip()]
        if pip and pip_pkgs:
            row["pip"] = _pip_install(pip_pkgs, python_bin=python_bin)
        else:
            row["pip"] = {"ok": True, "skipped": True}
        module = str(tech.get("module") or "")
        path = tech.get("path") or tech.get("script")
        path_ok = True
        if path:
            path_ok = os.path.exists(os.path.join(ex._BASE, str(path)))
        mod_ok = _module_ok(module) if module else True
        row["module_ok"] = mod_ok
        row["path_ok"] = path_ok
        row["ok"] = bool(row["pip"].get("ok")) and mod_ok and path_ok
        installed[key] = {
            "title": tech.get("title"),
            "id": tech.get("id"),
            "installed_at": time.time(),
            "ok": row["ok"],
            "pip_pkgs": pip_pkgs,
        }
        results.append(row)
    state["installed"] = installed
    state["updated_at"] = time.time()
    state["version"] = product_meta().get("version")
    state["count"] = len(installed)
    state["ok_count"] = sum(1 for v in installed.values() if v.get("ok"))
    _write_json(_STATE, state)
    return {
        "success": True,
        "product": product_meta(),
        "installed": len(results),
        "ok": sum(1 for r in results if r.get("ok")),
        "results": results,
        "state_path": _STATE,
    }


def status_report() -> Dict[str, Any]:
    catalog = load_catalog()
    state = install_state()
    installed = state.get("installed") or {}
    rows = []
    for tech in catalog.get("technologies") or []:
        key = str(tech.get("key") or tech.get("id"))
        info = installed.get(key) or {}
        rows.append({
            "id": tech.get("id"),
            "key": key,
            "title": tech.get("title"),
            "installed": bool(info),
            "ok": bool(info.get("ok")),
            "why": tech.get("why"),
        })
    return {
        "product": product_meta(),
        "total": len(rows),
        "installed": sum(1 for r in rows if r["installed"]),
        "ok": sum(1 for r in rows if r["ok"]),
        "technologies": rows,
        "state_path": _STATE,
    }


def product_improvement_backlog() -> Dict[str, Any]:
    """Finished-product improvement checklist (strategy + packaging)."""
    items = [
        {"id": "pkg-readme", "area": "packaging", "title": "Branded README + one-command install", "status": "done"},
        {"id": "pkg-top25", "area": "packaging", "title": "Top-25 technology catalog + installer", "status": "done"},
        {"id": "pkg-runner", "area": "packaging", "title": "profit_daemon_jon/run.py entrypoint", "status": "done"},
        {"id": "pkg-build", "area": "packaging", "title": "PyInstaller Linux/macOS/Windows build scripts", "status": "done"},
        {"id": "pkg-release-ci", "area": "packaging", "title": "GitHub Actions release artifacts", "status": "done"},
        {"id": "pkg-env", "area": "packaging", "title": "Slim .env.example for paper/live", "status": "done"},
        {"id": "str-exit-fund", "area": "strategy", "title": "Exit funding not starved by quote_reserve", "status": "done"},
        {"id": "str-fill-model", "area": "strategy", "title": "Calibrated fill-prob (no saturated 1.0 widen)", "status": "done"},
        {"id": "str-metrics", "area": "strategy", "title": "Grafana metrics for skew/fills/balances", "status": "done"},
        {"id": "str-sales", "area": "strategy", "title": "Sales report CLI (N-hour)", "status": "done"},
        {"id": "str-nonkyc-quote", "area": "strategy", "title": "NonKYC quote top-up / sell dust → USDT", "status": "done"},
        {"id": "str-level-cap", "area": "strategy", "title": "Dynamic max levels from free quote", "status": "done"},
        {"id": "str-pair-edge", "area": "strategy", "title": "PPP edge filter before ladder symbols", "status": "done"},
        {"id": "str-fee-aware", "area": "strategy", "title": "Per-venue maker/taker fee table auto-refresh", "status": "done"},
        {"id": "ops-win-exe", "area": "ops", "title": "Publish signed Windows .exe on Releases", "status": "done"},
        {"id": "ops-mac-app", "area": "ops", "title": "Publish macOS arm64/x64 builds", "status": "done"},
        {"id": "ops-docker", "area": "ops", "title": "Official Docker Compose one-liner", "status": "done"},
        {"id": "ops-wizard", "area": "ops", "title": "First-run setup wizard (keys + paper/live)", "status": "done"},
        {"id": "ops-gui", "area": "ops", "title": "Desktop tray status for The Profit Daemon Jon", "status": "done"},
        {"id": "ops-control", "area": "ops", "title": "127.0.0.1 browser control on daemon start", "status": "done"},
        {"id": "ops-exchange-registry", "area": "ops", "title": "Exchange registry — easy add/enable venues", "status": "done"},
        {"id": "sec-vault", "area": "security", "title": "Forced vault for live keys in downloadable build", "status": "done"},
        {"id": "sec-paper-default", "area": "security", "title": "Hard paper default until explicit live unlock", "status": "done"},
        {"id": "obs-public-dash", "area": "observability", "title": "Bundled Grafana/Prometheus compose profile", "status": "done"},
        {"id": "obs-sales-api", "area": "observability", "title": "HTTP /sales report endpoint", "status": "done"},
        {"id": "docs-video", "area": "docs", "title": "5-minute install video + screenshots", "status": "done"},
        {"id": "qa-smoke", "area": "qa", "title": "Release smoke: --once paper on CI", "status": "done"},
    ]
    done = sum(1 for i in items if i["status"] == "done")
    return {
        "product": "The Profit Daemon Jon",
        "total": len(items),
        "done": done,
        "open": len(items) - done,
        "completion_pct": round(100.0 * done / max(1, len(items)), 1),
        "items": items,
    }
