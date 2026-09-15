"""
Agent-to-agent MN2 mesh — cron-driven on-chain transfers between agent wallets.

Each agent gets a stable deposit address via user_id `agent:{agent_id}`.
The platform hot wallet sends dust MN2 to the recipient's address; txs are
logged as peer transfers (from_agent → to_agent) for chain activity + monitoring.
"""
from __future__ import annotations

import itertools
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE_FILE = os.path.join(_BASE, "data", "mn2_agent_peer_tx_state.json")
_CFG_FILE = os.path.join(_BASE, "data", "mn2_config.json")

# Platform agents that participate in the mesh when no bound_user_id is set.
_MESH_AGENT_IDS = (
    "monitoring_agent",
    "battle_strategy_agent",
    "analytics_agent",
    "content_generator_agent",
    "workflow_agent",
    "security_agent",
    "ai_intelligence_agent",
    "mn2_scout",
    "mn2_curator",
    "casino_kelly_agent",
    "casino_safe_grinder",
    "casino_meta_oracle",
    "arb_agent_internal",
    "arb_agent_payments",
    "ai_market_trader",
)


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def peer_config() -> Dict[str, Any]:
    root = _read_json(_CFG_FILE)
    peer = root.get("agent_peer_transactions") if isinstance(root.get("agent_peer_transactions"), dict) else {}
    chain = root.get("chain_reward_payouts") if isinstance(root.get("chain_reward_payouts"), dict) else {}
    return {
        "enabled": bool(peer.get("enabled", True)),
        "amount_mn2": float(peer.get("amount_mn2") or 0.00001),
        "max_per_run": int(peer.get("max_per_run") or 50),
        "max_per_pair_per_day": int(peer.get("max_per_pair_per_day") or 24),
        "user_id_prefix": str(peer.get("user_id_prefix") or "agent:"),
        "chain_enabled": bool(chain.get("enabled", False)),
        "min_chain_mn2": float(chain.get("min_amount_mn2") or 0.00001),
    }


def agent_peer_mesh_enabled() -> bool:
    cfg = peer_config()
    return cfg["enabled"] and cfg["chain_enabled"]


def _agent_user_id(agent_id: str, prefix: str) -> str:
    aid = str(agent_id or "").strip()
    if not aid:
        return ""
    if aid.startswith(prefix):
        return aid
    return f"{prefix}{aid}"


def discover_mesh_agents() -> List[Dict[str, str]]:
    """Collect unique agents from wallet config, casino, crypto shop, and settlement map."""
    seen: Dict[str, Dict[str, str]] = {}
    prefix = peer_config()["user_id_prefix"]

    def add(agent_id: str, user_id: Optional[str] = None, source: str = "default") -> None:
        aid = str(agent_id or "").strip()
        if not aid or aid in ("platform_treasury", "agent_treasury"):
            return
        uid = (user_id or "").strip() or _agent_user_id(aid, prefix)
        if aid not in seen:
            seen[aid] = {"agent_id": aid, "user_id": uid, "source": source}

    for aid in _MESH_AGENT_IDS:
        add(aid, source="mesh_defaults")

    try:
        from backend.services.agent_mn2_settlement_service import _AGENT_MAP
        for system, aid in (_AGENT_MAP or {}).items():
            add(aid, source=f"settlement:{system}")
    except Exception:
        pass

    try:
        from backend.services.agent_wallet_service import list_wallets
        for row in list_wallets() or []:
            add(row.get("agent_id") or "", source="agent_wallets")
    except Exception:
        pass

    path = os.path.join(_BASE, "data", "agent_crypto_wallet_agents.json")
    raw = _read_json(path)
    agents = raw.get("agents") if isinstance(raw.get("agents"), list) else []
    for a in agents:
        if not isinstance(a, dict):
            continue
        aid = (a.get("id") or "").strip()
        uid = (a.get("bound_user_id") or a.get("user_id") or "").strip()
        add(aid, uid or None, source="crypto_wallet_agents")

    casino_path = os.path.join(_BASE, "data", "casino_agents.json")
    casino = _read_json(casino_path)
    for aid, row in (casino or {}).items():
        if isinstance(row, dict):
            add(aid, row.get("user_id"), source="casino_agents")

    acct_dir = os.path.join(_BASE, "data", "crypto_exchange", "agent_accounts")
    if os.path.isdir(acct_dir):
        for name in os.listdir(acct_dir):
            if not name.endswith(".json"):
                continue
            row = _read_json(os.path.join(acct_dir, name))
            aid = (row.get("agent_id") or name.replace(".json", "")).strip()
            uid = (row.get("user_id") or row.get("wallet_user_id") or "").strip()
            add(aid, uid or None, source="exchange_agent")

    return list(seen.values())


def _resolve_addresses(agents: List[Dict[str, str]]) -> List[Dict[str, str]]:
    from backend.services.mn2_wallet_service import get_or_create_deposit_address

    out: List[Dict[str, str]] = []
    for row in agents:
        uid = row.get("user_id") or ""
        res = get_or_create_deposit_address(uid)
        if not res.get("success"):
            continue
        addr = (res.get("deposit_address") or "").strip()
        if not addr:
            continue
        out.append({**row, "address": addr})
    return out


def _pair_key(from_id: str, to_id: str) -> str:
    return f"{from_id}->{to_id}"


def _directed_pairs(agent_ids: List[str]) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for a, b in itertools.permutations(agent_ids, 2):
        pairs.append((a, b))
    return pairs


def _load_state() -> dict:
    return _read_json(_STATE_FILE)


def _save_state(state: dict) -> None:
    _write_json(_STATE_FILE, state)


def _pair_daily_count(state: dict, from_id: str, to_id: str) -> int:
    day = _utc_day()
    pairs = state.get("pair_counts") if isinstance(state.get("pair_counts"), dict) else {}
    row = pairs.get(_pair_key(from_id, to_id)) if isinstance(pairs.get(_pair_key(from_id, to_id)), dict) else {}
    if row.get("date") != day:
        return 0
    try:
        return int(row.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _bump_pair_count(state: dict, from_id: str, to_id: str) -> None:
    day = _utc_day()
    pairs = state.setdefault("pair_counts", {})
    key = _pair_key(from_id, to_id)
    row = pairs.setdefault(key, {})
    if row.get("date") != day:
        row["date"] = day
        row["count"] = 0
    row["count"] = int(row.get("count") or 0) + 1


def _send_peer_tx(
    from_agent: Dict[str, str],
    to_agent: Dict[str, str],
    amount: float,
    *,
    slot: int,
    dry_run: bool = False,
) -> Dict[str, Any]:
    ref = f"agent-peer:{from_agent['agent_id']}:{to_agent['agent_id']}:{datetime.now(timezone.utc).strftime('%Y%m%d%H')}:{slot}"
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "reference": ref,
            "from_agent": from_agent["agent_id"],
            "to_agent": to_agent["agent_id"],
            "address": to_agent.get("address"),
            "amount": amount,
        }

    from backend.services.mn2_chain_rewards_service import chain_payouts_enabled
    from backend.services.mn2_ledger import append_entry, is_txid_processed

    if not chain_payouts_enabled():
        return {"success": False, "error": "chain_payouts_disabled"}

    ref_key = f"chain-peer:{ref}"
    if is_txid_processed(ref_key):
        return {"success": True, "duplicate": True, "reference": ref}

    from backend.services.mn2_rpc_client import sendtoaddress

    send = sendtoaddress(to_agent["address"], round(amount, 8))
    if send.get("error"):
        return {"success": False, "error": send.get("error"), "reference": ref}
    txid = (send.get("result") or "").strip()
    if not txid:
        return {"success": False, "error": "rpc_no_txid", "reference": ref}

    meta = {
        "reference": ref,
        "from_agent": from_agent["agent_id"],
        "to_agent": to_agent["agent_id"],
        "to_user_id": to_agent.get("user_id"),
        "cron": True,
        "peer_mesh": True,
        "chain_paid": True,
        "chain_txid": txid,
    }
    append_entry(
        user_id=to_agent.get("user_id") or to_agent["agent_id"],
        entry_type="agent_peer_transaction",
        amount=amount,
        txid=txid,
        address=to_agent.get("address"),
        metadata=meta,
    )

    try:
        from backend.services.agent_db_service import agent_db_service
        agent_db_service.record_agent_activity(
            user_id=to_agent.get("user_id") or "platform_mn2",
            agent_id=from_agent["agent_id"],
            action="agent_peer_send",
            skill="mn2_peer_mesh",
            xp=2,
            points=amount,
            metadata=meta,
        )
        agent_db_service.record_agent_activity(
            user_id=to_agent.get("user_id") or "platform_mn2",
            agent_id=to_agent["agent_id"],
            action="agent_peer_receive",
            skill="mn2_peer_mesh",
            xp=2,
            points=amount,
            metadata=meta,
        )
    except Exception:
        pass

    return {
        "success": True,
        "txid": txid,
        "reference": ref,
        "from_agent": from_agent["agent_id"],
        "to_agent": to_agent["agent_id"],
        "amount": amount,
    }


def run_agent_peer_mesh(
    *,
    max_txs: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Rotate through agent→agent pairs and fire on-chain dust transfers.
    With N agents, up to N*(N-1) directed pairs per full cycle.
    """
    cfg = peer_config()
    out: Dict[str, Any] = {
        "success": True,
        "enabled": cfg["enabled"],
        "chain_enabled": cfg["chain_enabled"],
        "dry_run": dry_run,
        "agents": 0,
        "attempted": 0,
        "on_chain": 0,
        "skipped": 0,
        "errors": [],
        "txids": [],
        "transfers": [],
    }

    if not cfg["enabled"]:
        out["skipped_reason"] = "agent_peer_transactions_disabled"
        return out
    if not cfg["chain_enabled"] and not dry_run:
        out["skipped_reason"] = "chain_reward_payouts_disabled"
        out["success"] = False
        return out

    agents = _resolve_addresses(discover_mesh_agents())
    out["agents"] = len(agents)
    if len(agents) < 2:
        out["skipped_reason"] = "need_at_least_two_agents_with_addresses"
        out["success"] = False
        return out

    by_id = {a["agent_id"]: a for a in agents}
    pairs = _directed_pairs(list(by_id.keys()))
    if not pairs:
        out["skipped_reason"] = "no_pairs"
        return out

    cap = max_txs if max_txs is not None else cfg["max_per_run"]
    cap = max(1, min(cap, 200))
    amount = max(cfg["amount_mn2"], cfg["min_chain_mn2"])

    state = _load_state()
    try:
        start_idx = int(state.get("pair_cursor") or 0)
    except (TypeError, ValueError):
        start_idx = 0

    slot = 0
    idx = start_idx % len(pairs)
    tried = 0

    while out["attempted"] < cap and tried < len(pairs) * 2:
        from_id, to_id = pairs[idx]
        idx = (idx + 1) % len(pairs)
        tried += 1

        if _pair_daily_count(state, from_id, to_id) >= cfg["max_per_pair_per_day"]:
            out["skipped"] += 1
            continue

        from_agent = by_id[from_id]
        to_agent = by_id[to_id]
        out["attempted"] += 1
        try:
            res = _send_peer_tx(from_agent, to_agent, amount, slot=slot, dry_run=dry_run)
            slot += 1
            if res.get("txid"):
                out["on_chain"] += 1
                out["txids"].append(res["txid"])
                out["transfers"].append(
                    {"from": from_id, "to": to_id, "txid": res["txid"], "amount": amount}
                )
                _bump_pair_count(state, from_id, to_id)
            elif res.get("duplicate"):
                out["skipped"] += 1
            elif res.get("dry_run"):
                out["transfers"].append({"from": from_id, "to": to_id, "dry_run": True, "amount": amount})
            else:
                out["errors"].append(f"{from_id}->{to_id}:{res.get('error') or 'failed'}")
        except Exception as e:
            out["errors"].append(f"{from_id}->{to_id}:{str(e)[:120]}")

    if not dry_run:
        state["pair_cursor"] = idx
        state.setdefault("runs", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "agents": len(agents),
                "on_chain": out["on_chain"],
            }
        )
        state["runs"] = state["runs"][-50:]
        _save_state(state)

    if out["errors"] and out["on_chain"] == 0:
        out["success"] = False
    return out
