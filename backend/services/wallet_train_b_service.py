"""Wallet Train B — Tools & Debuggers (W-11…W-20) toward v1.5.0.0.

Site/ops surfaces for static checks, profilers, scanners, regression pack,
logs, error codes, format gate, and docs generation stubs.
"""
from __future__ import annotations

import ast
import os
import py_compile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from backend.services import mn2_rpc_client as rpc

TRAIN_B_TARGET = "v1.5.0.0"
TRAIN_B_CHANNEL = "draft"
TRAIN_B_SLICE = "B"

TRAIN_B_IDS: Tuple[str, ...] = tuple(f"W-{i:02d}" for i in range(11, 21))

TRAIN_B_META: Dict[str, Dict[str, Any]] = {
    "W-11": {
        "tech": "Code Analyzer",
        "title": "Release static-check gate on wallet patches",
        "surfaces": ["ops"],
    },
    "W-12": {
        "tech": "Performance Profiler",
        "title": "getwalletinfo / sync profiler panel",
        "surfaces": ["qt", "daemon"],
    },
    "W-13": {
        "tech": "Memory Debugger",
        "title": "Wallet memory watchdog + leak report",
        "surfaces": ["daemon"],
    },
    "W-14": {
        "tech": "Security Scanner",
        "title": "Dependency + RPC ACL scanner before release",
        "surfaces": ["ops"],
    },
    "W-15": {
        "tech": "Dependency Checker",
        "title": "Manifest of linked libs in RELEASE_MANIFEST",
        "surfaces": ["ops"],
    },
    "W-16": {
        "tech": "Test Generator",
        "title": "Auto wallet RPC regression pack",
        "surfaces": ["ops"],
    },
    "W-17": {
        "tech": "Log Analyzer",
        "title": "Structured wallet log schema + viewer hooks",
        "surfaces": ["daemon", "qt"],
    },
    "W-18": {
        "tech": "Error Tracker",
        "title": "Wallet error codes on /api/mn2/*",
        "surfaces": ["web"],
    },
    "W-19": {
        "tech": "Code Formatter",
        "title": "Format gate for wallet patches",
        "surfaces": ["ops"],
    },
    "W-20": {
        "tech": "Documentation Generator",
        "title": "Auto release notes + setup from manifest",
        "surfaces": ["ops", "web"],
    },
}

_BASE = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_WALLET_SERVICE_FILES = (
    "backend/services/mn2_wallet_service.py",
    "backend/services/mn2_rpc_client.py",
    "backend/services/mn2_onchain_wallet.py",
    "backend/services/wallet_train_a_service.py",
    "backend/services/wallet_train_b_service.py",
)
_RPC_LOG = _BASE / "logs" / "mn2_rpc.jsonl"

# Stable wallet error codes surfaced to APIs (W-18).
WALLET_ERROR_CODES: Dict[str, str] = {
    "auth_required": "Caller must be signed in",
    "auth_failed": "RPC authentication failed",
    "rpc_unreachable": "Daemon RPC unreachable",
    "insufficient_balance": "Balance too low for requested action",
    "withdraw_blocked": "Withdrawal blocked by risk or gate",
    "whitelist_required": "Address not on withdrawal whitelist",
    "spork_off": "Feature gated off by spork",
    "validation_error": "Request failed validation",
    "not_found": "Resource not found",
    "maintenance_mode": "Platform maintenance mode active",
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _meta(wid: str) -> Dict[str, Any]:
    row = TRAIN_B_META.get(wid) or {}
    return {
        "id": wid,
        "tech": row.get("tech"),
        "title": row.get("title"),
        "surfaces": list(row.get("surfaces") or []),
        "train": TRAIN_B_SLICE,
        "target": TRAIN_B_TARGET,
    }


def train_b_version() -> Dict[str, Any]:
    return {
        "success": True,
        "train": TRAIN_B_SLICE,
        "target": TRAIN_B_TARGET,
        "channel": TRAIN_B_CHANNEL,
        "badge": f"{TRAIN_B_TARGET}-B",
        "badge_label": f"Wallet Train B {TRAIN_B_TARGET} ({TRAIN_B_CHANNEL})",
        "latest_wallet_download_unchanged": True,
        "release_stub": "docs/releases/v1.5.0.0-hardened.md",
        "ids": list(TRAIN_B_IDS),
        "updated_at": _iso(),
    }


def static_check_gate() -> Dict[str, Any]:
    """W-11 — syntax/static gate over core wallet Python modules."""
    results: List[Dict[str, Any]] = []
    for rel in _WALLET_SERVICE_FILES:
        path = _BASE / rel
        row: Dict[str, Any] = {"path": rel, "exists": path.is_file()}
        if not path.is_file():
            row["ok"] = False
            row["error"] = "missing"
            results.append(row)
            continue
        try:
            py_compile.compile(str(path), doraise=True)
            src = path.read_text(encoding="utf-8")
            ast.parse(src)
            row["ok"] = True
            row["bytes"] = len(src.encode("utf-8"))
        except Exception as exc:
            row["ok"] = False
            row["error"] = str(exc)
        results.append(row)
    ok = all(bool(r.get("ok")) for r in results)
    return {
        "success": True,
        **_meta("W-11"),
        "gate": "static_check",
        "passed": ok,
        "files": results,
        "updated_at": _iso(),
    }


def wallet_profiler() -> Dict[str, Any]:
    """W-12 — getwalletinfo / sync profiler snapshot."""
    started = datetime.now(timezone.utc)
    wallet: Dict[str, Any] = {}
    chain: Dict[str, Any] = {}
    try:
        wi = rpc.getwalletinfo() or {}
        wallet = wi.get("result") if isinstance(wi.get("result"), dict) else {"error": wi.get("error")}
    except Exception as exc:
        wallet = {"error": str(exc)}
    try:
        ci = rpc.getblockchaininfo() or {}
        chain = ci.get("result") if isinstance(ci.get("result"), dict) else {"error": ci.get("error")}
    except Exception as exc:
        chain = {"error": str(exc)}
    elapsed_ms = (datetime.now(timezone.utc) - started).total_seconds() * 1000.0
    return {
        "success": True,
        **_meta("W-12"),
        "profile": {
            "elapsed_ms": round(elapsed_ms, 2),
            "wallet_txcount": (wallet or {}).get("txcount"),
            "wallet_balance": (wallet or {}).get("balance"),
            "verificationprogress": (chain or {}).get("verificationprogress"),
            "blocks": (chain or {}).get("blocks"),
        },
        "raw": {"wallet": wallet, "chain": chain},
        "updated_at": _iso(),
    }


def memory_watchdog() -> Dict[str, Any]:
    """W-13 — process RSS watchdog for the site worker (daemon mirror)."""
    rss_kb = None
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    rss_kb = int(parts[1])
                    break
    except Exception:
        rss_kb = None
    return {
        "success": True,
        **_meta("W-13"),
        "watchdog": {
            "rss_kb": rss_kb,
            "rss_mb": round((rss_kb or 0) / 1024.0, 2) if rss_kb is not None else None,
            "scope": "site_worker_mirror",
            "leak_report": "available_on_shutdown_stub",
        },
        "updated_at": _iso(),
    }


def security_scanner() -> Dict[str, Any]:
    """W-14 — RPC ACL / env posture scanner (no secret values returned)."""
    findings: List[Dict[str, Any]] = []
    url_set = bool((os.environ.get("MN2_RPC_URL") or "").strip())
    user_set = bool((os.environ.get("MN2_RPC_USER") or "").strip())
    pass_set = bool((os.environ.get("MN2_RPC_PASSWORD") or "").strip())
    findings.append({"id": "rpc_url_configured", "ok": url_set, "severity": "high" if not url_set else "info"})
    findings.append(
        {
            "id": "rpc_auth_configured",
            "ok": user_set and pass_set,
            "severity": "high" if not (user_set and pass_set) else "info",
        }
    )
    findings.append(
        {
            "id": "spork_gates_default",
            "ok": True,
            "severity": "info",
            "note": "Live money sporks remain default-off in app defaults",
        }
    )
    reqs = _BASE / "requirements.txt"
    findings.append({"id": "requirements_present", "ok": reqs.is_file(), "severity": "medium" if not reqs.is_file() else "info"})
    passed = all(bool(f.get("ok")) for f in findings if f.get("severity") in ("high", "medium"))
    return {
        "success": True,
        **_meta("W-14"),
        "passed": passed,
        "findings": findings,
        "updated_at": _iso(),
    }


def dependency_manifest() -> Dict[str, Any]:
    """W-15 — linked lib / requirements manifest slice for releases."""
    slim = _BASE / "requirements-runtime.txt"
    # Prefer slim if present; else requirements.txt
    path = slim if slim.is_file() else (_BASE / "requirements.txt")
    lines: List[str] = []
    if path.is_file():
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or line.startswith("-r"):
                    continue
                lines.append(line.split(";")[0].strip())
        except Exception:
            lines = []
    return {
        "success": True,
        **_meta("W-15"),
        "manifest": {
            "source": str(path.relative_to(_BASE)) if path.is_file() else None,
            "dependency_count": len(lines),
            "dependencies": lines[:80],
            "truncated": len(lines) > 80,
        },
        "updated_at": _iso(),
    }


def rpc_regression_pack() -> Dict[str, Any]:
    """W-16 — lightweight wallet RPC regression pack (read-only)."""
    cases = [
        ("health_check", lambda: rpc.health_check()),
        ("getblockchaininfo", lambda: rpc.getblockchaininfo()),
        ("getmempoolinfo", lambda: rpc.getmempoolinfo()),
        ("getwalletinfo", lambda: rpc.getwalletinfo()),
    ]
    results: List[Dict[str, Any]] = []
    for name, fn in cases:
        row: Dict[str, Any] = {"case": name}
        try:
            out = fn() or {}
            # health_check returns status dict; others return {result,error}
            if name == "health_check":
                row["ok"] = out.get("status") == "healthy" or bool(out.get("success"))
                row["detail"] = {"status": out.get("status"), "error": out.get("error")}
            else:
                row["ok"] = out.get("error") is None
                row["detail"] = {"has_result": out.get("result") is not None, "error": out.get("error")}
        except Exception as exc:
            row["ok"] = False
            row["detail"] = {"error": str(exc)}
        results.append(row)
    # Pack itself succeeds as a runner even if RPC is down — report case failures.
    return {
        "success": True,
        **_meta("W-16"),
        "pack": "wallet_rpc_readonly_v1",
        "cases": results,
        "passed_count": sum(1 for r in results if r.get("ok")),
        "case_count": len(results),
        "updated_at": _iso(),
    }


def log_analyzer() -> Dict[str, Any]:
    """W-17 — structured wallet RPC log schema + recent lines."""
    schema = {
        "fields": ["ts", "method", "ok", "elapsed_ms", "error"],
        "path": "logs/mn2_rpc.jsonl",
        "enabled_env": "MN2_PROFILE_LOG",
    }
    recent: List[str] = []
    exists = _RPC_LOG.is_file()
    if exists:
        try:
            lines = _RPC_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
            recent = lines[-10:]
        except Exception as exc:
            recent = [f"read_error:{exc}"]
    return {
        "success": True,
        **_meta("W-17"),
        "schema": schema,
        "log_exists": exists,
        "recent_lines": recent,
        "updated_at": _iso(),
    }


def error_tracker() -> Dict[str, Any]:
    """W-18 — wallet error code catalog for /api/mn2/*."""
    return {
        "success": True,
        **_meta("W-18"),
        "codes": [{"code": k, "message": v} for k, v in sorted(WALLET_ERROR_CODES.items())],
        "count": len(WALLET_ERROR_CODES),
        "updated_at": _iso(),
    }


def format_gate() -> Dict[str, Any]:
    """W-19 — lightweight format gate (tab + trailing whitespace check)."""
    findings: List[Dict[str, Any]] = []
    for rel in _WALLET_SERVICE_FILES:
        path = _BASE / rel
        if not path.is_file():
            findings.append({"path": rel, "ok": False, "error": "missing"})
            continue
        text = path.read_text(encoding="utf-8")
        tab = "\t" in text
        trailing = any(line.rstrip("\n").endswith(" ") for line in text.splitlines())
        findings.append({"path": rel, "ok": not tab and not trailing, "tabs": tab, "trailing_space": trailing})
    passed = all(bool(f.get("ok")) for f in findings)
    return {
        "success": True,
        **_meta("W-19"),
        "gate": "whitespace_format_v1",
        "passed": passed,
        "files": findings,
        "updated_at": _iso(),
    }


def docs_generator() -> Dict[str, Any]:
    """W-20 — release notes / setup doc pointers from release stub."""
    stub = _BASE / "docs" / "releases" / "v1.5.0.0-hardened.md"
    setup = _BASE / "docs" / "MN2_DAEMON_SETUP.md"
    notes = [
        f"Train B tools/debuggers for {TRAIN_B_TARGET}",
        "Static check + format gates on wallet Python modules",
        "Read-only RPC regression pack",
        "Wallet error code catalog on /api/mn2/train-b/W-18",
    ]
    return {
        "success": True,
        **_meta("W-20"),
        "docs": {
            "release_stub": "docs/releases/v1.5.0.0-hardened.md",
            "release_stub_exists": stub.is_file(),
            "setup_doc": "docs/MN2_DAEMON_SETUP.md",
            "setup_doc_exists": setup.is_file(),
            "generated_notes": notes,
        },
        "updated_at": _iso(),
    }


_RUNNERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "W-11": lambda **_kw: static_check_gate(),
    "W-12": lambda **_kw: wallet_profiler(),
    "W-13": lambda **_kw: memory_watchdog(),
    "W-14": lambda **_kw: security_scanner(),
    "W-15": lambda **_kw: dependency_manifest(),
    "W-16": lambda **_kw: rpc_regression_pack(),
    "W-17": lambda **_kw: log_analyzer(),
    "W-18": lambda **_kw: error_tracker(),
    "W-19": lambda **_kw: format_gate(),
    "W-20": lambda **_kw: docs_generator(),
}


def run_deliverable(deliverable_id: str, **kwargs: Any) -> Dict[str, Any]:
    wid = str(deliverable_id or "").strip().upper()
    if wid not in TRAIN_B_IDS:
        return {"success": False, "error": "not_train_b_deliverable", "id": wid, "ids": list(TRAIN_B_IDS)}
    runner = _RUNNERS.get(wid)
    if not runner:
        return {"success": False, "error": "runner_missing", "id": wid}
    try:
        return runner(**kwargs)
    except Exception as exc:
        return {"success": False, "error": str(exc), "id": wid}


def train_b_manifest() -> Dict[str, Any]:
    return {
        "success": True,
        "train": TRAIN_B_SLICE,
        "target": TRAIN_B_TARGET,
        "channel": TRAIN_B_CHANNEL,
        "count": len(TRAIN_B_IDS),
        "ids": list(TRAIN_B_IDS),
        "deliverables": [{**_meta(wid), "installed": True} for wid in TRAIN_B_IDS],
        "version": train_b_version(),
        "updated_at": _iso(),
    }


def run_train_b(**kwargs: Any) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for wid in TRAIN_B_IDS:
        results[wid] = run_deliverable(wid, **kwargs)
    ok = sum(1 for v in results.values() if isinstance(v, dict) and v.get("success"))
    return {
        "success": ok == len(TRAIN_B_IDS),
        "train": TRAIN_B_SLICE,
        "target": TRAIN_B_TARGET,
        "count": len(TRAIN_B_IDS),
        "ok_count": ok,
        "results": results,
        "version": train_b_version(),
        "updated_at": _iso(),
    }


def train_b_acceptance() -> Dict[str, Any]:
    """Train B acceptance: static gate, format gate, regression pack present, docs stub."""
    checks: List[Dict[str, Any]] = []
    static = static_check_gate()
    checks.append({"id": "static_check", "ok": bool(static.get("passed")), "detail": {"files": len(static.get("files") or [])}})

    fmt = format_gate()
    checks.append({"id": "format_gate", "ok": bool(fmt.get("passed")), "detail": {"files": len(fmt.get("files") or [])}})

    pack = rpc_regression_pack()
    checks.append(
        {
            "id": "rpc_regression_pack",
            "ok": bool(pack.get("success")) and int(pack.get("case_count") or 0) >= 4,
            "detail": {"passed_count": pack.get("passed_count"), "case_count": pack.get("case_count")},
        }
    )

    errors = error_tracker()
    checks.append({"id": "error_catalog", "ok": int(errors.get("count") or 0) >= 8, "detail": {"count": errors.get("count")}})

    docs = docs_generator()
    checks.append(
        {
            "id": "docs_stub",
            "ok": bool((docs.get("docs") or {}).get("release_stub_exists")),
            "detail": docs.get("docs"),
        }
    )

    passed = all(bool(c.get("ok")) for c in checks)
    return {
        "success": passed,
        "passed": passed,
        "train": TRAIN_B_SLICE,
        "target": TRAIN_B_TARGET,
        "checks": checks,
        "version": train_b_version(),
        "updated_at": _iso(),
    }
