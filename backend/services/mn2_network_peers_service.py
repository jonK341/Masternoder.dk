"""Canonical MN2 P2P peer lists for wallet bootstrap and ops tooling."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PEERS_PATH = os.path.join(_BASE, "data", "mn2_network_peers.json")

_HOST_PORT_RE = re.compile(
    r"^(?P<host>[a-zA-Z0-9._-]+|\d{1,3}(?:\.\d{1,3}){3}|\[[0-9a-fA-F:]+\])(?::(?P<port>\d{1,5}))?$"
)


def _read_config() -> Dict[str, Any]:
    if not os.path.isfile(_PEERS_PATH):
        return {"networks": {}}
    try:
        with open(_PEERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"networks": {}}
    except Exception:
        return {"networks": {}}


def _network_key(network: Optional[str] = None) -> str:
    net = (network or os.environ.get("MN2_NETWORK") or "mainnet").strip().lower()
    if net in ("test", "testnet"):
        return "testnet"
    return "mainnet"


def get_network_config(network: Optional[str] = None) -> Dict[str, Any]:
    """Return peer/DNS config for mainnet or testnet."""
    key = _network_key(network)
    cfg = _read_config()
    nets = cfg.get("networks") if isinstance(cfg.get("networks"), dict) else {}
    block = nets.get(key) if isinstance(nets.get(key), dict) else {}
    return {
        "network": key,
        "p2p_port": int(block.get("p2p_port") or (27646 if key == "testnet" else 17646)),
        "rpc_port": int(block.get("rpc_port") or (19332 if key == "testnet" else 9332)),
        "dns_seeds": list(block.get("dns_seeds") or []),
        "addnodes": list(block.get("addnodes") or []),
        "notes": block.get("notes") or "",
        "version": cfg.get("version"),
        "updated": cfg.get("updated"),
    }


def parse_peer_entry(entry: str, default_port: int) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """
    Parse host, port from an addnode/connect line.
    Returns (host, port, error_message).
    """
    raw = (entry or "").strip()
    if not raw:
        return None, None, "empty entry"
    # Reject legacy malformed entries like 144.91.75.27_17646
    if "_" in raw and ":" not in raw:
        return None, None, f"invalid separator (use host:port, got {raw!r})"
    m = _HOST_PORT_RE.match(raw)
    if not m:
        return None, None, f"invalid peer format: {raw!r}"
    host = m.group("host")
    port_s = m.group("port")
    if port_s is None:
        return host, int(default_port), None
    port = int(port_s)
    if port < 1 or port > 65535:
        return None, None, f"port out of range: {port}"
    return host, port, None


def normalize_addnodes(entries: List[str], default_port: int) -> Tuple[List[str], List[str]]:
    """Return (valid host:port lines, error strings)."""
    valid: List[str] = []
    errors: List[str] = []
    seen = set()
    for entry in entries:
        host, port, err = parse_peer_entry(entry, default_port)
        if err or not host or port is None:
            errors.append(err or f"bad entry: {entry!r}")
            continue
        line = f"{host}:{port}"
        if line not in seen:
            seen.add(line)
            valid.append(line)
    return valid, errors


def conf_snippet(network: Optional[str] = None, include_comments: bool = True) -> str:
    """Generate recommended masternoder2.conf peer bootstrap lines."""
    cfg = get_network_config(network)
    lines: List[str] = []
    if include_comments:
        lines.extend([
            "# --- MN2 network bootstrap (super update) ---",
            f"# P2P port {cfg['p2p_port']}; RPC port {cfg['rpc_port']}.",
            "# Prefer addnode= (keeps DNS seeding + peer relay). Avoid connect=localhost.",
            "listen=1",
            f"port={cfg['p2p_port']}",
            "dns=1",
            "dnsseed=1",
            "discover=1",
            "",
        ])
    if cfg["network"] == "testnet":
        lines.append("testnet=1")
    for peer in cfg["addnodes"]:
        lines.append(f"addnode={peer}")
    return "\n".join(lines) + "\n"


def peer_catalog() -> Dict[str, Any]:
    """Public payload for /api/mn2/network-peers and wallet UI."""
    main = get_network_config("mainnet")
    test = get_network_config("testnet")
    return {
        "success": True,
        "version": _read_config().get("version"),
        "updated": _read_config().get("updated"),
        "mainnet": main,
        "testnet": test,
        "connect_guide": {
            "p2p_port_mainnet": main["p2p_port"],
            "rpc_port_mainnet": main["rpc_port"],
            "p2p_port_testnet": test["p2p_port"],
            "rpc_port_testnet": test["rpc_port"],
            "steps": [
                "Install MasterNoder2 Qt or daemon from /wallets.",
                f"Copy config/masternoder2.conf.example to your datadir; set rpcuser/rpcpassword; rpcport={main['rpc_port']}.",
                f"Add addnode= lines below (P2P port {main['p2p_port']}) — do not use connect=localhost.",
                "Start the wallet; wait for peers (8+) and chain sync in the status bar.",
                "Optional: append the conf_snippet from GET /api/mn2/network-peers?format=conf.",
            ],
        },
        "conf_snippet_mainnet": conf_snippet("mainnet"),
        "conf_snippet_testnet": conf_snippet("testnet"),
    }


def peer_health_from_overview(overview: Dict[str, Any]) -> Dict[str, Any]:
    """Derive peer-health flags from network-overview / daemon extras."""
    daemon = overview.get("daemon") if isinstance(overview.get("daemon"), dict) else {}
    conns = daemon.get("connections")
    try:
        conns_i = int(conns) if conns is not None else None
    except (TypeError, ValueError):
        conns_i = None
    if conns_i is None:
        status = "unknown"
        message = "Daemon RPC unreachable — cannot read peer count."
    elif conns_i == 0:
        status = "critical"
        message = "No P2P peers — add addnode= lines from /api/mn2/network-peers."
    elif conns_i < 4:
        status = "degraded"
        message = f"Low peer count ({conns_i}) — check firewall and addnode list."
    else:
        status = "healthy"
        message = f"{conns_i} peers connected."
    return {
        "status": status,
        "connections": conns_i,
        "message": message,
        "min_recommended_peers": 4,
    }
