"""Run full profit body once daemon is ready, reinforce learning, save knowledge."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services.exchange_agent_learning_service import learn_from_profit, learning_snapshot
from backend.services.exchange_closer_claw_service import run_closer_tick
from backend.services.exchange_courier_arm_service import run_courier_tick
from backend.services.exchange_datamaxi_cex_spread_service import run_datamaxi_cex_spread_tick
from backend.services.exchange_dual_farm_arm_service import run_dual_farm_arm_tick
from backend.services.exchange_funding_basis_arm_service import run_funding_basis_tick
from backend.services.exchange_latch_sniper_service import run_latch_tick
from backend.services.exchange_precision_swing_service import run_precision_swing_tick
from backend.services.exchange_profit_head_service import load_control, run_head_tick
from backend.services.exchange_profit_order_book_service import run_profit_order_book_tick
from backend.services.exchange_spread_hunter_arm_service import run_spread_hunter_tick
from backend.services.exchange_technique_executor_service import run_technique_executor_tick


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _summary(res: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": res.get("success"),
        "summary": res.get("summary"),
        "skip": res.get("skip_reason") or res.get("reason"),
        "executed": bool(
            res.get("executed")
            or res.get("fired")
            or res.get("handed_to_hunter")
            or res.get("opened")
            or res.get("ready_to_exec")
        ),
    }


def main() -> int:
    iso = _iso()
    jobs = [
        ("pbook", lambda: run_profit_order_book_tick(force=True, apply=True)),
        ("executor", lambda: run_technique_executor_tick(force=True)),
        ("datamaxi", lambda: run_datamaxi_cex_spread_tick(force=True)),
        ("hunter", lambda: run_spread_hunter_tick(force=True)),
        ("basis", lambda: run_funding_basis_tick(force=True)),
        ("swing", lambda: run_precision_swing_tick(force=True)),
        ("courier", lambda: run_courier_tick(force=True)),
        ("latch", lambda: run_latch_tick(force=True)),
        ("closer", lambda: run_closer_tick(force=True)),
        ("dual_farm", lambda: run_dual_farm_arm_tick(force=True)),
        ("head", lambda: run_head_tick(force=True)),
    ]
    results: Dict[str, Any] = {}
    for name, fn in jobs:
        try:
            res = fn()
            results[name] = _summary(res)
            print(name, results[name].get("summary") or results[name])
        except Exception as exc:
            results[name] = {"success": False, "error": str(exc)[:200]}
            print(name, "ERROR", exc)

    agents = [
        "arb_profit_head",
        "arb_live_dual_farm",
        "arb_spread_hunter",
        "arb_tech_executor",
    ]
    learn_out: Dict[str, Any] = {}
    for aid in agents:
        acct = arb.read_account(aid)
        if not acct.get("skills"):
            acct["skills"] = [
                "spatial_arb",
                "cutting_edge",
                "prefund",
                "learning",
                "technique_executor",
            ]
        before = learning_snapshot(acct)
        learned = learn_from_profit(acct, 0.05)
        acct["last_action"] = {
            "note": "daemon_ready_techniques_cycle",
            "ts": iso,
            "results": {k: (v.get("skip") or v.get("summary")) for k, v in results.items()},
        }
        acct["ticks"] = int(acct.get("ticks") or 0) + 1
        arb.write_account(acct)
        learn_out[aid] = {"before": before, "after": learning_snapshot(acct), "reward": learned}

    kb_path = os.path.join(getattr(ex, "_BASE", "/var/www/html"), "data", "agent_learning_knowledge.json")
    raw: Dict[str, Any] = {}
    if os.path.isfile(kb_path):
        try:
            loaded = json.load(open(kb_path))
            raw = loaded if isinstance(loaded, dict) else {"entries": loaded}
        except Exception:
            raw = {}
    entries = raw.get("entries")
    if not isinstance(entries, list):
        entries = []
    entry = {
        "id": f"profit-body-ready-{iso}",
        "source": "profit_daemon",
        "title": "Daemon ready — techniques cycle knowledge",
        "text": (
            "Full body ran with all limbs enabled after daemon load. "
            "Cutting-edge bands fire/latch/skip; DataMaxi playbook gates; "
            "basis paper signals; precision swing levels. "
            f"Results={json.dumps(results, default=str)[:1200]}"
        ),
        "rulebook_ref": ["docs/PROFIT_DAEMON_BODY.md", "docs/PROFIT_TRADING_PROFILES.md"],
        "created_at": iso,
        "limbs": list(results.keys()),
        "learning": {aid: v.get("after") for aid, v in learn_out.items()},
    }
    entries.append(entry)
    raw["entries"] = entries[-200:]
    raw["updated_at"] = iso
    if "description" not in raw:
        raw["description"] = (
            "Agent-learned technology and knowledge. Wired to rulebooks and compendium."
        )
    os.makedirs(os.path.dirname(kb_path), exist_ok=True)
    json.dump(raw, open(kb_path, "w"), indent=2)
    print("KNOWLEDGE_SAVED", kb_path, "entries", len(raw["entries"]))
    print(
        "LEARN",
        {
            aid: {
                "iq": v["after"].get("intelligence"),
                "mastery": v["after"].get("mastery_pct"),
            }
            for aid, v in learn_out.items()
        },
    )
    ctrl = load_control()
    print(
        "HEAD",
        {
            "pause": ctrl.get("manual_body_pause"),
            "limbs": {k: x.get("enabled") for k, x in (ctrl.get("limbs") or {}).items()},
            "kill": (ctrl.get("kill_shot") or {}).get("symbol"),
            "prefund": (ctrl.get("prefund_hint") or {}).get("symbol"),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
