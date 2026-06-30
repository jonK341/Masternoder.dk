"""Aggregated MN2 wallet, network, rental, and transaction feeds for UI surfaces."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

_LOCK = threading.Lock()
_CACHE: Dict[str, Dict[str, Any]] = {}
_PUBLIC_TTL = 25
_USER_TTL = 12


def _cached(key: str, ttl: int, builder: Callable[[], Any]) -> Any:
    now = time.time()
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (now - ent.get("ts", 0)) < ttl:
            return ent.get("value")
    value = builder()
    with _LOCK:
        _CACHE[key] = {"value": value, "ts": now}
    return value


def _network_snapshot() -> Dict[str, Any]:
    """Light network slice: peers, daemon connections, block height (best-effort)."""
    out: Dict[str, Any] = {
        "peer_catalog_count": 0,
        "p2p_port": 17646,
        "rpc_port": 9332,
        "connections": None,
        "block_height": None,
        "masternode_count": None,
        "peer_health": None,
    }
    try:
        from backend.services.mn2_network_peers_service import get_network_config, peer_health_from_overview
        cfg = get_network_config("mainnet")
        out["peer_catalog_count"] = len(cfg.get("addnodes") or [])
        out["p2p_port"] = cfg.get("p2p_port")
        out["rpc_port"] = cfg.get("rpc_port")
        out["dns_seeds"] = cfg.get("dns_seeds") or []
    except Exception:
        pass
    try:
        from backend.services import mn2_chainz
        ov = mn2_chainz.network_overview() or {}
        daemon = ov.get("daemon") if isinstance(ov.get("daemon"), dict) else {}
        out["connections"] = daemon.get("connections")
        out["block_height"] = ov.get("block_height")
        out["masternode_count"] = ov.get("masternode_count")
        from backend.services.mn2_network_peers_service import peer_health_from_overview
        out["peer_health"] = peer_health_from_overview(ov)
    except Exception:
        pass
    return out


def wallet_hub(user_id: str) -> Dict[str, Any]:
    """Single payload for profile/wallets overview: balance, network, sporks."""
    uid = (user_id or "").strip() or "default_user"

    def build() -> Dict[str, Any]:
        balance: Dict[str, Any] = {"success": False, "mn2_balance": 0}
        try:
            from backend.services.mn2_wallet_service import get_balance
            balance = get_balance(uid) or balance
        except Exception as exc:
            balance = {"success": False, "error": str(exc), "mn2_balance": 0}

        price: Dict[str, Any] = {}
        try:
            from backend.services import mn2_chainz
            price = {"mn2_usd_price": mn2_chainz.mn2_usd_price()}
        except Exception:
            pass

        sporks: Dict[str, Any] = {}
        try:
            from backend.services import mn2_spork_service as spork
            sporks = spork.gate_status()
        except Exception as exc:
            sporks = {"gates_enabled": True, "error": str(exc)}

        network = _network_snapshot()
        releases: Dict[str, Any] = {}
        try:
            from backend.services.mn2_release_catalog_service import get_release_catalog
            rel = get_release_catalog()
            releases = {
                "version": rel.get("version"),
                "release_base": rel.get("release_base"),
                "github_releases": rel.get("github_releases"),
            }
        except Exception:
            pass

        tx_preview: List[Dict[str, Any]] = []
        try:
            from backend.services.mn2_ledger import get_entries_by_user
            tx_preview = get_entries_by_user(uid, limit=5)
        except Exception:
            pass

        return {
            "success": True,
            "user_id": uid,
            "balance": balance,
            "mn2_usd_price": price.get("mn2_usd_price"),
            "network": network,
            "spork_gates": sporks,
            "releases": releases,
            "recent_transactions_preview": tx_preview,
        }

    return _cached(f"hub:{uid}", _USER_TTL, build)


def _chain_txs_for_address(address: str, limit: int) -> List[Dict[str, Any]]:
    if not address:
        return []
    rows: List[Dict[str, Any]] = []
    try:
        from backend.services import mn2_rpc_client as rpc
        r = rpc.listtransactions(count=min(200, limit * 4))
        if r.get("error") or not isinstance(r.get("result"), list):
            return []
        addr_l = address.strip().lower()
        for tx in r["result"]:
            if not isinstance(tx, dict):
                continue
            tx_addr = (tx.get("address") or "").strip().lower()
            if tx_addr != addr_l:
                continue
            cat = str(tx.get("category") or "")
            if cat not in ("receive", "send", "immature", "generate", "mint", "stake"):
                continue
            rows.append({
                "source": "chain",
                "type": cat,
                "amount": tx.get("amount"),
                "confirmations": tx.get("confirmations"),
                "txid": tx.get("txid"),
                "address": tx.get("address"),
                "created_at": tx.get("timereceived") or tx.get("time"),
            })
            if len(rows) >= limit:
                break
    except Exception:
        pass
    return rows


def recent_transactions_feed(user_id: str, limit: int = 30) -> Dict[str, Any]:
    """Unified recent activity: custodial ledger + on-chain wallet txs + exchange trades."""
    uid = (user_id or "").strip() or "default_user"
    limit = max(1, min(int(limit or 30), 100))

    def build() -> Dict[str, Any]:
        merged: List[Dict[str, Any]] = []

        try:
            from backend.services.mn2_ledger import get_entries_by_user
            for e in get_entries_by_user(uid, limit=limit):
                merged.append({
                    "source": "custodial",
                    "type": e.get("type"),
                    "amount": e.get("amount"),
                    "txid": e.get("txid"),
                    "address": e.get("address"),
                    "created_at": e.get("created_at"),
                    "metadata": e.get("metadata"),
                })
        except Exception:
            pass

        deposit_addr = ""
        try:
            from backend.services.mn2_wallet_service import get_or_create_deposit_address
            da = get_or_create_deposit_address(uid)
            if da.get("success"):
                deposit_addr = (da.get("deposit_address") or "").strip()
        except Exception:
            pass

        for tx in _chain_txs_for_address(deposit_addr, limit=min(15, limit)):
            merged.append(tx)

        try:
            from backend.services.crypto_exchange_service import list_trades
            trades = list_trades(limit=min(20, limit)).get("trades") or []
            for t in trades:
                if not isinstance(t, dict):
                    continue
                buyer = str(t.get("buyer_id") or t.get("user_id") or "")
                seller = str(t.get("seller_id") or "")
                if buyer != uid and seller != uid and uid != "default_user":
                    continue
                merged.append({
                    "source": "exchange",
                    "type": "exchange_trade",
                    "amount": t.get("amount_mn2") or t.get("amount"),
                    "txid": t.get("trade_id") or t.get("id"),
                    "created_at": t.get("ts") or t.get("created_at"),
                    "metadata": {"pair": t.get("pair"), "side": "buy" if buyer == uid else "sell"},
                })
        except Exception:
            pass

        def _sort_key(item: Dict[str, Any]) -> str:
            v = item.get("created_at")
            if v is None:
                return ""
            return str(v)

        merged.sort(key=_sort_key, reverse=True)
        out = merged[:limit]

        try:
            from backend.services.mn2_explorer_urls import explorer_address_url, explorer_tx_url
            for item in out:
                txid = (item.get("txid") or "").strip()
                if txid and len(txid) == 64:
                    item["explorer_tx_url"] = explorer_tx_url(txid)
                addr = (item.get("address") or "").strip()
                if addr:
                    item["explorer_address_url"] = explorer_address_url(addr)
        except Exception:
            pass

        return {
            "success": True,
            "user_id": uid,
            "count": len(out),
            "transactions": out,
        }

    return _cached(f"txfeed:{uid}:{limit}", _USER_TTL, build)


def rental_overview(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Masternode hosting fleet + exchange agent rental catalog (public + optional user rentals)."""
    uid = (user_id or "").strip()

    def build() -> Dict[str, Any]:
        hosting: Dict[str, Any] = {}
        try:
            from backend.services import mn2_masternode_service as mn
            hosting = mn.get_service_status() or {}
        except Exception as exc:
            hosting = {"success": False, "error": str(exc)}

        agent_rental: Dict[str, Any] = {}
        try:
            from backend.services.exchange_rental_service import rental_catalog
            agent_rental = rental_catalog() or {}
        except Exception as exc:
            agent_rental = {"success": False, "error": str(exc)}

        user_rentals: Optional[Dict[str, Any]] = None
        if uid and uid != "default_user":
            try:
                from backend.services.exchange_rental_service import list_user_rentals
                user_rentals = list_user_rentals(uid)
            except Exception:
                user_rentals = {"success": False, "rentals": []}

        listings = agent_rental.get("rentals") or []
        return {
            "success": True,
            "masternode_hosting": {
                "slots_available": hosting.get("slots_available"),
                "hosted_count": hosting.get("hosted_count"),
                "enabled_count": hosting.get("enabled_count"),
                "max_hosted_nodes": hosting.get("max_hosted_nodes"),
                "network": hosting.get("network"),
                "paypal": hosting.get("paypal"),
                "hosting_stats": hosting.get("hosting_stats"),
            },
            "agent_rental": {
                "enabled": agent_rental.get("enabled", True),
                "currency": agent_rental.get("currency", "MN2"),
                "listing_count": len(listings),
                "listings": listings[:8],
            },
            "user_agent_rentals": user_rentals,
        }

    key = f"rental:{uid or 'public'}"
    return _cached(key, _PUBLIC_TTL, build)


def public_network_dashboard() -> Dict[str, Any]:
    """Public network + spork snapshot for explorer and /wallets (no user data)."""
    def build() -> Dict[str, Any]:
        network = _network_snapshot()
        sporks: Dict[str, Any] = {}
        try:
            from backend.services import mn2_spork_service as spork
            sporks = spork.gate_status()
        except Exception as exc:
            sporks = {"error": str(exc)}
        blocks: List[Dict[str, Any]] = []
        try:
            from backend.services.mn2_explorer_data import recent_blocks
            blocks = recent_blocks(limit=8)
        except Exception:
            pass
        mn: Dict[str, Any] = {}
        try:
            from backend.services.mn2_explorer_data import masternodes
            mn = masternodes(limit=10)
        except Exception:
            pass
        platform_txs: List[Dict[str, Any]] = []
        try:
            from backend.services.crypto_exchange_service import list_trades
            for t in (list_trades(limit=10).get("trades") or []):
                if isinstance(t, dict):
                    platform_txs.append({
                        "source": "exchange",
                        "type": "exchange_trade",
                        "amount": t.get("amount_mn2") or t.get("amount"),
                        "created_at": t.get("ts") or t.get("created_at"),
                        "txid": t.get("trade_id") or t.get("id"),
                    })
        except Exception:
            pass
        return {
            "success": True,
            "network": network,
            "spork_gates": sporks,
            "recent_blocks": blocks,
            "masternodes": {"total": mn.get("total"), "enabled": mn.get("enabled")},
            "platform_transactions": platform_txs,
        }

    return _cached("public_network", _PUBLIC_TTL, build)
