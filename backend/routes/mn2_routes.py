"""
MN2 API routes (Phase 2–3): balance, deposit address, transactions.
Auth: user resolved via session > query > identification (same as points/shop).
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 2–3.
"""
import logging
import os
import json
from flask import Blueprint, jsonify, request

_log = logging.getLogger(__name__)

from backend.services.account_resolution_service import resolve_user_id
from backend.services.mn2_wallet_service import get_balance, get_or_create_deposit_address
from backend.services.mn2_ledger import get_entries_by_user, append_entry, count_withdrawals_since, sum_withdrawals_since


def _explorer_base_url() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "mn2_config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return (json.load(f).get("explorer_base_url") or "").strip() or "https://chainz.cryptoid.info/mn2/"
        except Exception:
            pass
    return "https://chainz.cryptoid.info/mn2/"


def _explorer_tx_url(txid: str) -> str:
    if not (txid or "").strip():
        return ""
    base = _explorer_base_url().rstrip("/")
    return f"{base}/tx.dws?txid={txid.strip()}"


def _load_mn2_config() -> dict:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "mn2_config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"withdrawal_fee": 0.001, "confirmations": 6}


mn2_bp = Blueprint("mn2", __name__)


@mn2_bp.route("/api/mn2/balance", methods=["GET"])
def mn2_balance():
    """Return the current user's in-app MN2 balance (unified points) and shop rate (coins_per_mn2)."""
    user_id = resolve_user_id(from_body=False, from_query=True)
    result = get_balance(user_id)
    if not result.get("success"):
        return jsonify({"success": False, "error": result.get("error", "Unknown error")}), 500
    config = _load_mn2_config()
    coins_per_mn2 = float(config.get("coins_per_mn2") or 100)
    shop_revenue_address = (config.get("shop_revenue_address") or "").strip()
    base = _explorer_base_url().rstrip("/")
    shop_revenue_explorer_url = f"{base}/address.dws?addr={shop_revenue_address}" if shop_revenue_address else ""
    payload = {
        "success": True,
        "user_id": result.get("user_id"),
        "mn2_balance": result.get("mn2_balance", 0),
        "coins_per_mn2": coins_per_mn2,
        "shop_revenue_address": shop_revenue_address or None,
        "shop_revenue_explorer_url": shop_revenue_explorer_url or None,
    }
    if config.get("withdrawal_requires_verification"):
        try:
            from backend.services.mn2_verification import is_verified
            payload["withdrawal_verified"] = is_verified(result.get("user_id") or "")
        except Exception:
            payload["withdrawal_verified"] = False
    try:
        from backend.services.mn2_chainz import chainz_ticker_usd_with_updated
        ticker = chainz_ticker_usd_with_updated()
        if isinstance(ticker, dict) and ticker.get("price") is not None:
            payload["mn2_usd_price"] = round(ticker["price"], 8)
            if ticker.get("last_updated_iso"):
                payload["mn2_usd_price_updated_iso"] = ticker["last_updated_iso"]
    except Exception:
        pass
    try:
        from backend.services.mn2_hold_registry import get_holds
        holds = get_holds(result.get("user_id") or user_id)
        payload["liquid_mn2"] = holds.get("liquid_mn2")
        payload["held_mn2"] = holds.get("held_mn2")
        payload["withdrawable_mn2"] = holds.get("withdrawable_mn2")
        payload["holds"] = holds.get("holds")
    except Exception:
        pass
    return jsonify(payload), 200


@mn2_bp.route("/api/mn2/price", methods=["GET"])
def mn2_price():
    """Return MN2/USD price and coins_per_mn2 (Phase 9: live price feed). No auth required for public price."""
    config = _load_mn2_config()
    coins_per_mn2 = float(config.get("coins_per_mn2") or 100)
    payload = {"success": True, "coins_per_mn2": coins_per_mn2}
    try:
        from backend.services.mn2_chainz import chainz_ticker_usd_with_updated
        ticker = chainz_ticker_usd_with_updated()
        if isinstance(ticker, dict) and ticker.get("price") is not None:
            payload["mn2_usd_price"] = round(ticker["price"], 8)
            if ticker.get("last_updated_iso"):
                payload["last_updated_iso"] = ticker["last_updated_iso"]
    except Exception:
        pass
    return jsonify(payload), 200


def _user_facing_rpc_error(rpc_error: str) -> str:
    """Turn RPC error into a short message for the profile/API (no server internals)."""
    if not rpc_error:
        return "Wallet temporarily unavailable."
    err = (rpc_error or "").strip()
    if "401" in err:
        return "Wallet RPC authentication failed. Server must set MN2_RPC_USER and MN2_RPC_PASSWORD to match the wallet node."
    if "403" in err:
        return "Wallet RPC access forbidden. Check RPC user/password."
    if "connection" in err.lower() or "refused" in err.lower() or "timeout" in err.lower():
        return "Wallet RPC unreachable. Ensure the MN2 wallet node is running and MN2_RPC_URL is correct."
    if len(err) > 120:
        return err[:117] + "..."
    return err


@mn2_bp.route("/api/mn2/deposit-address", methods=["GET"])
def mn2_deposit_address():
    """Return the deposit address for the current user (create via RPC if first time)."""
    user_id = resolve_user_id(from_body=False, from_query=True)
    result = get_or_create_deposit_address(user_id)
    if not result.get("success"):
        err = result.get("error", "Unknown error")
        return jsonify({
            "success": False,
            "error": _user_facing_rpc_error(err),
            "user_id": user_id,
            "deposit_address": None,
        }), 200
    addr = result.get("deposit_address") or ""
    base = _explorer_base_url().rstrip("/")
    explorer_address_url = f"{base}/address.dws?addr={addr}" if addr else ""
    return jsonify({
        "success": True,
        "user_id": result.get("user_id"),
        "deposit_address": addr,
        "explorer_address_url": explorer_address_url,
    }), 200


@mn2_bp.route("/api/mn2/transactions", methods=["GET"])
def mn2_transactions():
    """Return ledger entries for the current user with explorer links."""
    # Server-resolved identity only: a caller can't read another account's ledger by
    # passing ?user_id= (privacy; matches the §9.2 hardening). Falls back to identification.
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    limit = min(100, max(1, int(request.args.get("limit", 50))))
    entries = get_entries_by_user(user_id, limit=limit)
    base = _explorer_base_url().rstrip("/")
    out = []
    for e in entries:
        item = dict(e)
        if (e.get("txid") or "").strip():
            item["explorer_tx_url"] = _explorer_tx_url(e["txid"])
        else:
            item["explorer_tx_url"] = None
        addr = (e.get("address") or "").strip()
        if addr:
            item["explorer_address_url"] = f"{base}/address.dws?addr={addr}"
        else:
            item["explorer_address_url"] = None
        out.append(item)
    return jsonify({"success": True, "user_id": user_id, "transactions": out}), 200


@mn2_bp.route("/api/mn2/statement", methods=["GET"])
def mn2_statement():
    """
    Personal MN2 audit log + tax export (Top-10 #4). Server-resolved identity ONLY.
    Lists every ledger event with a signed balance delta and a derived running balance,
    plus per-type and per-year summaries. ?year=YYYY filters the rows (summaries cover all);
    ?format=csv returns a tax/accounting export.
    """
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "Sign in to view your statement.", "code": "auth_required"}), 401

    # Convention for the derived balance view (mn2_balance perspective):
    _INFLOW = {"deposit", "staking_reward", "onramp_purchase", "unstake", "p2p_buy", "p2p_escrow_return"}
    _OUTFLOW = {"withdrawal", "shop_payment", "onramp_clawback", "stake", "p2p_sell_escrow"}

    entries = get_entries_by_user(user_id, limit=100000)  # newest-first
    chrono = list(reversed(entries))
    running = 0.0
    all_rows = []
    for e in chrono:
        t = (e.get("type") or "").strip()
        try:
            amt = float(e.get("amount") or 0)
        except (TypeError, ValueError):
            amt = 0.0
        delta = amt if t in _INFLOW else (-amt if t in _OUTFLOW else 0.0)
        running = round(running + delta, 8)
        meta = e.get("metadata") or {}
        txid = (e.get("txid") or "").strip()
        all_rows.append({
            "created_at": e.get("created_at"),
            "type": t,
            "amount_mn2": round(amt, 8),
            "delta_mn2": round(delta, 8),
            "running_balance_mn2": running,
            "fee": meta.get("fee"),
            "txid": txid or None,
            "address": (e.get("address") or "") or None,
            "explorer_tx_url": _explorer_tx_url(txid) if txid else None,
        })

    year = (request.args.get("year") or "").strip()
    view_rows = [r for r in all_rows if (r.get("created_at") or "").startswith(year)] if year else all_rows

    by_type = {}
    by_year = {}
    for r in all_rows:
        bt = by_type.setdefault(r["type"], {"count": 0, "total_mn2": 0.0})
        bt["count"] += 1
        bt["total_mn2"] = round(bt["total_mn2"] + r["amount_mn2"], 8)
        y = (r.get("created_at") or "")[:4]
        if y:
            yr = by_year.setdefault(y, {"inflow_mn2": 0.0, "outflow_mn2": 0.0, "net_mn2": 0.0, "events": 0})
            yr["events"] += 1
            if r["delta_mn2"] >= 0:
                yr["inflow_mn2"] = round(yr["inflow_mn2"] + r["delta_mn2"], 8)
            else:
                yr["outflow_mn2"] = round(yr["outflow_mn2"] - r["delta_mn2"], 8)
            yr["net_mn2"] = round(yr["inflow_mn2"] - yr["outflow_mn2"], 8)

    if (request.args.get("format") or "").lower() == "csv":
        import csv
        import io
        from flask import Response
        cols = ["created_at", "type", "amount_mn2", "delta_mn2", "running_balance_mn2", "fee", "txid", "address"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in reversed(view_rows):  # chronological for accounting
            writer.writerow(row)
        fname = f"mn2_statement_{year or 'all'}.csv"
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={fname}"})

    return jsonify({
        "success": True,
        "user_id": user_id,
        "year": year or None,
        "rows": view_rows[::-1],  # newest-first for display
        "current_balance_mn2": running,
        "summary": {
            "events": len(all_rows),
            "by_type": by_type,
            "by_year": by_year,
        },
        "disclaimer": ("Informational record derived from your in-app MN2 ledger. Not tax advice — "
                       "consult a professional. Balance is a derived view and may differ from on-chain."),
    }), 200


@mn2_bp.route("/api/mn2/wallet-activity", methods=["GET"])
def mn2_wallet_activity():
    """Last N UTC days of MN2 ledger aggregates (deposits, outflows, net) for profile monitor."""
    user_id = resolve_user_id(from_body=False, from_query=True)
    try:
        days = int(request.args.get("days", 5))
    except (TypeError, ValueError):
        days = 5
    days = max(1, min(days, 31))
    try:
        from backend.services.mn2_ledger import get_wallet_activity_days

        buckets = get_wallet_activity_days(user_id, days=days)
        return jsonify({"success": True, "user_id": user_id, "days": days, "buckets": buckets}), 200
    except Exception as e:
        _log.exception("mn2_wallet_activity failed user_id=%s", user_id)
        return jsonify({"success": False, "error": str(e), "user_id": user_id, "days": days, "buckets": []}), 500


@mn2_bp.route("/api/mn2/order-payment", methods=["POST"])
def mn2_create_order_payment():
    """Create an on-chain order payment (Phase 8). Body: item_id, quantity. Returns address, amount_mn2, payment_ref, expires_at."""
    user_id = resolve_user_id(from_body=True, from_query=True)
    try:
        data = request.get_json() or {}
        item_id = (data.get("item_id") or request.args.get("item_id") or "").strip()
        quantity = max(1, int(data.get("quantity", 1)))
    except Exception:
        return jsonify({"success": False, "error": "Invalid request"}), 400
    if not item_id:
        return jsonify({"success": False, "error": "item_id required"}), 400
    from backend.routes.shop_routes import _get_shop_items
    items = _get_shop_items() or []
    item = next((i for i in items if (i.get("id") or "") == item_id), None)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404
    price = item.get("price", 0)
    if isinstance(price, dict):
        return jsonify({"success": False, "error": "On-chain MN2 payment only for coin-priced items"}), 400
    total_coins = int(price) * quantity
    config = _load_mn2_config()
    coins_per_mn2 = float(config.get("coins_per_mn2") or 100)
    if coins_per_mn2 <= 0:
        return jsonify({"success": False, "error": "MN2 price not configured"}), 400
    price_mn2 = total_coins / coins_per_mn2
    try:
        from backend.services.mn2_rpc_client import getnewaddress
        r = getnewaddress()
        if r.get("error"):
            return jsonify({"success": False, "error": r.get("error", "Could not get address")}), 200
        address = (r.get("result") or "").strip()
        if not address:
            return jsonify({"success": False, "error": "RPC did not return address"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200
    from backend.services.mn2_order_payment_service import create_order_payment
    order = create_order_payment(
        user_id=user_id,
        item_id=item_id,
        item_name=item.get("name", ""),
        quantity=quantity,
        price_coins=total_coins,
        price_mn2=price_mn2,
        address=address,
    )
    base = _explorer_base_url().rstrip("/")
    explorer_address_url = f"{base}/address.dws?addr={address}" if address else ""
    return jsonify({
        "success": True,
        "payment_ref": order["payment_ref"],
        "address": address,
        "amount_mn2": order["amount_mn2"],
        "expires_at": order["expires_at"],
        "item_id": item_id,
        "item_name": order["item_name"],
        "quantity": quantity,
        "explorer_address_url": explorer_address_url,
    }), 200


@mn2_bp.route("/api/mn2/order-payment/status", methods=["GET"])
def mn2_order_payment_status():
    """Get status of an on-chain order payment. Query: payment_ref."""
    payment_ref = (request.args.get("payment_ref") or (request.get_json() or {}).get("payment_ref") or "").strip()
    if not payment_ref:
        return jsonify({"success": False, "error": "payment_ref required"}), 400
    from backend.services.mn2_order_payment_service import get_order
    from datetime import datetime
    order = get_order(payment_ref)
    if not order:
        return jsonify({"success": False, "error": "Order not found"}), 404
    status = order.get("status", "pending")
    # A "confirming" order has a seen tx and must not be shown as expired.
    if status == "pending" and (order.get("expires_at") or "") < datetime.utcnow().isoformat() + "Z":
        status = "expired"
    config = _load_mn2_config()
    out = {
        "success": True,
        "payment_ref": order["payment_ref"],
        "status": status,
        "address": order.get("address"),
        "amount_mn2": order.get("amount_mn2"),
        "amount_received": order.get("amount_received"),
        "confirmations": int(order.get("confirmations") or 0),
        "confirmations_required": int(config.get("confirmations") or 6),
        "item_id": order.get("item_id"),
        "quantity": order.get("quantity"),
        "txid": order.get("txid"),
        "fulfilled_at": order.get("fulfilled_at"),
    }
    if order.get("txid"):
        out["explorer_tx_url"] = _explorer_tx_url(order["txid"])
    return jsonify(out), 200


def _scan_deposits_authorized() -> bool:
    """If MN2_SCAN_SECRET is set, require X-Scanner-Token header or ?token= to match. Otherwise allow."""
    secret = (os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (request.headers.get("X-Scanner-Token") or request.args.get("token") or "").strip()
    return token == secret


def _ops_authorized() -> bool:
    """If MN2_SCAN_SECRET or MN2_OPS_SECRET is set, require token. Otherwise allow (dev)."""
    secret = (os.environ.get("MN2_OPS_SECRET") or os.environ.get("MN2_SCAN_SECRET") or "").strip()
    if not secret:
        return True
    token = (request.headers.get("X-Scanner-Token") or request.headers.get("X-Ops-Token") or request.args.get("token") or "").strip()
    return token == secret


@mn2_bp.route("/api/mn2/ops/create-addresses", methods=["POST", "GET"])
def mn2_ops_create_addresses():
    """Ask the daemon to create N deposit addresses and store as pool_1, pool_2, ... (max 100). Requires MN2_OPS_SECRET or MN2_SCAN_SECRET if set."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        count = 1
        if request.method == "POST" and request.get_json():
            count = int(request.get_json().get("count", 1))
        else:
            count = int(request.args.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, 100))
    from backend.services.mn2_wallet_service import create_deposit_addresses
    try:
        result = create_deposit_addresses(count)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "created": [],
            "count": 0,
        }), 200
    if not result.get("success"):
        return jsonify({
            "success": False,
            "error": result.get("error", "Failed to create addresses"),
            "created": result.get("created", []),
            "count": len(result.get("created", [])),
        }), 200
    return jsonify({
        "success": True,
        "created": result["created"],
        "count": result["count"],
        "message": f"Created {result['count']} deposit address(es); assigned as pool_1, pool_2, ... (used when users request deposit-address).",
    }), 200


@mn2_bp.route("/api/mn2/ops/verified-users", methods=["GET"])
def mn2_ops_list_verified():
    """List verified user_ids (Phase 10). Requires MN2_OPS_SECRET or MN2_SCAN_SECRET if set."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_verification import list_verified
        return jsonify({"success": True, "user_ids": list_verified()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/withdrawal-risk", methods=["GET"])
def mn2_ops_withdrawal_risk():
    """Recent withdrawal risk assessments (Top-10 #3). Query: ?limit=N&min_level=elevated|high. Ops-secret gated."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "logs", "mn2_withdrawal_risk.jsonl")
        limit = int(request.args.get("limit", 100))
        min_level = (request.args.get("min_level") or "").strip().lower()
        rank = {"low": 0, "elevated": 1, "high": 2}
        rows = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if min_level and rank.get((row.get("level") or "low"), 0) < rank.get(min_level, 0):
                        continue
                    rows.append(row)
        rows = rows[-limit:][::-1]
        return jsonify({"success": True, "count": len(rows), "events": rows}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/treasury-address", methods=["POST", "GET"])
def mn2_ops_treasury_address():
    """
    Generate a daemon-wallet address for **funding reserves** (proof-of-reserves backing).
    Unlike deposit pool addresses, this is NOT added to the deposit-scanner address map, so
    coins sent here raise on-chain assets WITHOUT being credited as a user liability — exactly
    what's needed to back existing in-app balances. Tracked in data/mn2_treasury_addresses.json.
    Requires ops secret.
    """
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from datetime import datetime, timezone
        from backend.services import mn2_rpc_client as rpc
        r = rpc.getnewaddress()
        addr = r.get("result") if isinstance(r, dict) else None
        if not addr:
            err = (r.get("error") if isinstance(r, dict) else None) or "getnewaddress returned no address"
            return jsonify({"success": False, "error": str(err)}), 502
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "data", "mn2_treasury_addresses.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                store = json.load(f)
        except Exception:
            store = {}
        if not isinstance(store, dict):
            store = {}
        addrs = store.get("addresses") or []
        addrs.append({"address": addr, "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
        store["addresses"] = addrs
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
        return jsonify({
            "success": True,
            "treasury_address": addr,
            "note": ("Send reserve-backing MN2 here. This address belongs to the staking daemon "
                     "wallet (counts toward proof-of-reserves) but is NOT a user deposit address, "
                     "so the deposit scanner will not credit it to any account."),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/holders", methods=["GET"])
def mn2_ops_holders():
    """
    Index of MN2 users to pick from when managing the withdrawal allowlist.
    Returns user_id, deposit_address, mn2_balance, mn2_staked, verified — sorted by
    holdings desc. Query: ?with_balance=1 (only non-zero holders), ?limit=N. Ops-secret gated.
    """
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_wallet_service import get_address_to_user_map
        from backend.services.mn2_verification import list_verified
        from backend.services.unified_points_database import unified_points_db

        user_to_addr = {uid: addr for addr, uid in get_address_to_user_map().items()}
        verified = set(list_verified())

        # Read MN2 balances straight from the file-backed points store (logs/unified_points/*.json)
        # — pure file IO, no per-user SQL (the SQL path stalls across many users).
        uids = set(user_to_addr.keys())
        try:
            uids |= {fn[:-5] for fn in os.listdir(unified_points_db.points_dir) if fn.endswith(".json") and fn[:-5]}
        except Exception:
            pass

        only_holders = (request.args.get("with_balance") or "").lower() in ("1", "true", "yes")
        limit = int(request.args.get("limit", 500))
        rows = []
        for uid in uids:
            systems = {}
            try:
                raw = unified_points_db._load_file_store(uid)
                systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
            except Exception:
                systems = {}
            bal = float(systems.get("mn2_balance", 0) or 0)
            staked = float(systems.get("mn2_staked", 0) or 0)
            if only_holders and bal <= 0 and staked <= 0:
                continue
            rows.append({
                "user_id": uid,
                "deposit_address": user_to_addr.get(uid),
                "mn2_balance": round(bal, 8),
                "mn2_staked": round(staked, 8),
                "verified": uid in verified,
            })
        rows.sort(key=lambda r: (r["mn2_balance"] + r["mn2_staked"]), reverse=True)
        return jsonify({
            "success": True,
            "count": len(rows),
            "verified_count": len(verified),
            "users": rows[:limit],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/verify-user", methods=["POST"])
def mn2_ops_verify_user():
    """
    Add or remove a user from the withdrawal allowlist (Phase 10).
    Body: { user_id | address, action: add|remove }. `address` is resolved to its
    owning user_id via the deposit-address map, so you can verify by wallet address.
    Requires ops secret.
    """
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        uid = (data.get("user_id") or request.args.get("user_id") or "").strip()
        addr = (data.get("address") or request.args.get("address") or "").strip()
        action = (data.get("action") or request.args.get("action") or "add").strip().lower()
        if not uid and addr:
            from backend.services.mn2_wallet_service import get_address_to_user_map
            uid = (get_address_to_user_map().get(addr) or "").strip()
            if not uid:
                return jsonify({"success": False, "error": "No user found for that deposit address"}), 404
        if not uid:
            return jsonify({"success": False, "error": "user_id or address required"}), 400
        from backend.services.mn2_verification import add_verified, remove_verified
        if action == "remove":
            ok = remove_verified(uid)
            return jsonify({"success": True, "action": "remove", "user_id": uid, "removed": ok}), 200
        ok = add_verified(uid)
        return jsonify({"success": True, "action": "add", "user_id": uid, "added": ok}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/webhook-outbox", methods=["GET"])
def mn2_ops_webhook_outbox():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.webhook_outbox import stats
        return jsonify(stats()), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/webhook-outbox/process", methods=["POST"])
def mn2_ops_webhook_outbox_process():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.webhook_outbox import process_pending
        data = request.get_json(silent=True) or {}
        limit = int(data.get("limit") or request.args.get("limit") or 50)
        return jsonify(process_pending(limit=limit)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/sybil-clusters", methods=["GET"])
def mn2_ops_sybil_clusters():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_sybil_graph import ops_clusters
        return jsonify(ops_clusters(
            min_score=float(request.args.get("min_score", 0.6)),
            limit=int(request.args.get("limit", 50)),
        )), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/float-gate", methods=["GET"])
def mn2_ops_float_gate():
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_float_gate import assess
        amt = float(request.args.get("amount_mn2") or 0)
        return jsonify(assess(amt)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/swap/quote", methods=["GET", "POST"])
def mn2_swap_quote():
    data = request.get_json(silent=True) or {}
    side = (data.get("side") or request.args.get("side") or "sell").strip().lower()
    try:
        amt = float(data.get("mn2_amount") or request.args.get("mn2_amount") or 0)
    except (TypeError, ValueError):
        amt = 0
    try:
        from backend.services.mn2_internal_amm import quote
        return jsonify(quote(side, amt)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/swap/execute", methods=["POST"])
def mn2_swap_execute():
    user_id = resolve_user_id(from_body=True, from_query=True)
    data = request.get_json(silent=True) or {}
    try:
        from backend.services.mn2_internal_amm import execute as swap_exec
        r = swap_exec(
            user_id,
            (data.get("quote_id") or "").strip(),
            (data.get("side") or "sell").strip().lower(),
            float(data.get("mn2_amount") or 0),
        )
        return jsonify(r), 200 if r.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/conservation-gate", methods=["GET"])
def mn2_ops_conservation_gate():
    """Unified money conservation gate (staking + casino tournaments + arena + generation health)."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.mn2_conservation_gate import conservation_gate
        return jsonify(conservation_gate()), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/points-drift", methods=["GET"])
def mn2_ops_points_drift():
    """File vs SQL unified points drift scan."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.points_drift_service import scan_all
        limit = min(2000, max(1, int(request.args.get("limit", 500))))
        return jsonify(scan_all(limit=limit)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/agent-kill-switch", methods=["GET", "POST"])
def mn2_ops_agent_kill_switch():
    """Read or set agent automation kill switches."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        from backend.services.agent_kill_switch import get_status, set_switch
        if request.method == "GET":
            return jsonify(get_status()), 200
        data = request.get_json(silent=True) or {}
        return jsonify(set_switch(
            global_halt=data.get("global_halt") if "global_halt" in data else None,
            halted_agents=data.get("halted_agents"),
            halted_verbs=data.get("halted_verbs"),
            reason=str(data.get("reason") or ""),
            set_by="ops",
        )), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/ops/stats", methods=["GET"])
def mn2_ops_stats():
    """Return last N scanner runs and recent RPC call stats (from logs). Requires MN2_SCAN_SECRET or MN2_OPS_SECRET if set."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(base, "logs")
    scanner_log = os.path.join(log_dir, "mn2_deposit_scanner.jsonl")
    rpc_log = os.path.join(log_dir, "mn2_rpc.jsonl")
    out = {"scanner_runs": [], "rpc_calls_summary": None}
    if os.path.exists(scanner_log):
        try:
            with open(scanner_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
            last_n = 50
            for line in lines[-last_n:]:
                line = line.strip()
                if not line:
                    continue
                try:
                    out["scanner_runs"].append(json.loads(line))
                except Exception:
                    pass
            out["scanner_runs"].reverse()
        except Exception as e:
            out["scanner_error"] = str(e)
    if os.path.exists(rpc_log):
        try:
            with open(rpc_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
            last_100 = lines[-100:]
            ok_count = sum(1 for L in last_100 if '"ok":true' in L or '"ok": True' in L)
            out["rpc_calls_summary"] = {"last_100_ok": ok_count, "last_100_total": len(last_100)}
        except Exception as e:
            out["rpc_error"] = str(e)
    # Daemon staking health (plan sec.9): is the pool actually minting blocks?
    try:
        from backend.services.mn2_rpc_client import staking_health
        out["staking_health"] = staking_health()
    except Exception as e:
        out["staking_health"] = {"status": "unsupported", "error": str(e)}
    # In-app pool snapshot (independent of daemon RPC)
    try:
        from backend.services import mn2_staking_service as _stk
        out["pool"] = {
            "total_staked_mn2": _stk.total_staked(),
            "dynamic_apr_percent": _stk.dynamic_apr(),
        }
    except Exception:
        out["pool"] = None
    return jsonify({"success": True, **out}), 200


@mn2_bp.route("/api/mn2/scan-deposits", methods=["POST"])
def mn2_scan_deposits():
    """Run the deposit scanner once (e.g. from cron). If MN2_SCAN_SECRET is set, require X-Scanner-Token or ?token=."""
    if not _scan_deposits_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    from backend.services.mn2_deposit_scanner import run_scanner
    result = run_scanner()
    status = 200 if result.get("success") else 500
    return jsonify(result), status


# Default max withdrawals per user per 24h when not in config
MN2_WITHDRAWAL_RATE_LIMIT_PER_DAY_DEFAULT = 10


@mn2_bp.route("/api/mn2/withdraw", methods=["POST"])
def mn2_withdraw():
    """
    Withdraw MN2 to an external address. Body: { "address": "...", "amount": 1.5 }.
    Deducts full amount from balance; sends (amount - fee) to address. Returns txid and explorer_tx_url.
    """
    from datetime import datetime, timedelta
    from backend.services.mn2_rpc_client import validateaddress, sendtoaddress
    from backend.services.unified_points_database import unified_points_db

    # Identity for withdrawals is resolved server-side ONLY (session > IP/fingerprint
    # identification). A caller-supplied user_id in the body/query is NOT trusted here —
    # otherwise anyone could drain another account by passing its id to this endpoint.
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({
            "success": False,
            "error": "You must be signed in to withdraw.",
            "code": "auth_required",
        }), 401
    try:
        data = request.get_json() or {}
        address = (data.get("address") or data.get("addr") or "").strip()
        try:
            amount = float(data.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0
    except Exception:
        return jsonify({"success": False, "error": "Invalid request body"}), 400

    if not address:
        return jsonify({"success": False, "error": "address is required"}), 400
    if amount <= 0:
        return jsonify({"success": False, "error": "amount must be positive"}), 400

    config = _load_mn2_config()
    if config.get("withdrawal_requires_verification"):
        try:
            from backend.services.mn2_verification import is_verified
            if not is_verified(user_id):
                return jsonify({
                    "success": False,
                    "error": "Withdrawal requires account verification. Please complete verification to withdraw.",
                    "code": "verification_required",
                }), 403
        except Exception:
            return jsonify({"success": False, "error": "Verification check failed"}), 500

    # Password gate: if the account has real-money protection on (default) and a password
    # set, require a fresh password-verification token (POST /api/user/security/verify).
    # Stops a hijacked session from withdrawing without re-proving the password.
    try:
        from backend.services.account_security_service import check_real_money_action
        _verify_token = (data.get("verification_token") or data.get("verify_token") or "").strip() or None
        _blocked = check_real_money_action(user_id, _verify_token)
        if _blocked:
            return jsonify({
                "success": False,
                "error": _blocked,
                "code": "password_verification_required",
            }), 403
    except ImportError:
        pass  # security service unavailable -> don't hard-fail withdrawals

    # Address whitelist (optional) + TOTP 2FA when enabled for this user.
    try:
        from backend.services.mn2_withdrawal_security import check_whitelist_gate, check_totp_gate
        if config.get("withdrawal_requires_whitelist"):
            wl = check_whitelist_gate(user_id, address, True)
            if not wl.get("allowed"):
                return jsonify({
                    "success": False,
                    "error": wl.get("error"),
                    "code": wl.get("code", "whitelist_required"),
                }), 403
        totp_code = (data.get("totp_code") or data.get("otp") or data.get("two_factor_code") or "").strip()
        totp_gate = check_totp_gate(user_id, totp_code)
        if not totp_gate.get("allowed"):
            return jsonify({
                "success": False,
                "error": totp_gate.get("error"),
                "code": totp_gate.get("code", "totp_required"),
            }), 403
    except ImportError:
        pass

    min_w = float(config.get("min_withdrawal") or 0)
    max_w = float(config.get("max_withdrawal") or 0)
    if min_w > 0 and amount < min_w:
        return jsonify({"success": False, "error": f"Minimum withdrawal is {min_w} MN2"}), 400
    if max_w > 0 and amount > max_w:
        return jsonify({"success": False, "error": f"Maximum withdrawal is {max_w} MN2"}), 400

    fee = float(config.get("withdrawal_fee") or 0.001)
    amount_sent = amount - fee
    if amount_sent <= 0:
        return jsonify({"success": False, "error": f"Amount must be greater than withdrawal fee ({fee} MN2)"}), 400

    # Validate address (RPC)
    r = validateaddress(address)
    if r.get("error"):
        return jsonify({"success": False, "error": f"Address check failed: {r['error']}"}), 500
    res = r.get("result")
    is_valid = res is True if isinstance(res, bool) else (isinstance(res, dict) and res.get("isvalid") is True)
    if not is_valid:
        return jsonify({"success": False, "error": "Invalid MN2 address"}), 400

    # New-address cooling-off: a payout address this user has never used is held for
    # `withdrawal_new_address_cooldown_hours` before it can receive funds. Blunts the
    # "hijack session -> instantly drain to attacker address" path. Trusted (reused)
    # addresses pass immediately. Fail-open if the guard errors.
    cooldown_hours = float(config.get("withdrawal_new_address_cooldown_hours") or 0)
    if cooldown_hours > 0:
        try:
            from backend.services.mn2_withdrawal_guard import check_address
            gate = check_address(user_id, address, cooldown_hours)
            if not gate.get("allowed"):
                hrs = gate.get("seconds_remaining", 0) / 3600.0
                return jsonify({
                    "success": False,
                    "error": (f"This is a new withdrawal address. For your security it can be used "
                              f"after a {cooldown_hours:g}h review window (~{hrs:.1f}h remaining)."),
                    "code": "address_cooldown",
                    "seconds_remaining": gate.get("seconds_remaining"),
                    "first_seen": gate.get("first_seen"),
                }), 403
        except ImportError:
            pass

    # Rate limit: N withdrawals per 24h per user (Phase 9: configurable)
    since = (datetime.utcnow() - timedelta(hours=24)).isoformat() + "Z"
    max_per_day = int(config.get("max_withdrawal_per_day") or 0) or MN2_WITHDRAWAL_RATE_LIMIT_PER_DAY_DEFAULT
    if count_withdrawals_since(user_id, since) >= max_per_day:
        return jsonify({
            "success": False,
            "error": f"Withdrawal rate limit exceeded (max {max_per_day} per 24h)",
        }), 429
    max_amount_per_day = float(config.get("max_withdrawal_amount_per_day") or 0)
    if max_amount_per_day > 0:
        already_withdrawn = sum_withdrawals_since(user_id, since)
        if already_withdrawn + amount > max_amount_per_day:
            return jsonify({
                "success": False,
                "error": f"Daily withdrawal cap exceeded (max {max_amount_per_day} MN2 per 24h, already {already_withdrawn:.4f})",
            }), 429

    # Balance check
    bal = get_balance(user_id)
    if not bal.get("success"):
        return jsonify({"success": False, "error": bal.get("error", "Could not get balance")}), 500
    if (bal.get("mn2_balance") or 0) < amount:
        return jsonify({"success": False, "error": "Insufficient balance"}), 400

    # Risk-based step-up (anomaly detection): score this withdrawal (velocity, large amount,
    # new address, fraction of balance). Elevated/high risk re-imposes a password challenge
    # even if the user turned real-money protection off; high risk on a password-less account
    # is blocked with advice to set a password. Fail-open if the service errors.
    try:
        from backend.services.mn2_withdrawal_risk import assess as _risk_assess
        risk = _risk_assess(user_id, address, amount, bal.get("mn2_balance") or 0, config)
    except Exception:
        risk = {"require_step_up": False}
    if risk.get("require_step_up"):
        try:
            from backend.services.account_security_service import has_password, verify_action_token
            _token = (data.get("verification_token") or data.get("verify_token") or "").strip() or None
            if has_password(user_id):
                if not verify_action_token(user_id, _token):
                    return jsonify({
                        "success": False,
                        "error": ("This withdrawal looks unusual (" + ", ".join(risk.get("reasons") or []) +
                                  "). For your security, re-verify your password to continue."),
                        "code": "step_up_required",
                        "risk_level": risk.get("level"),
                        "risk_reasons": risk.get("reasons"),
                    }), 403
            elif risk.get("hard_block_if_no_password"):
                return jsonify({
                    "success": False,
                    "error": ("This withdrawal was flagged as high-risk (" + ", ".join(risk.get("reasons") or []) +
                              "). Set a password on your profile to authorize it."),
                    "code": "risk_blocked",
                    "risk_level": risk.get("level"),
                    "risk_reasons": risk.get("reasons"),
                }), 403
        except ImportError:
            pass

    # Float gate for large withdrawals
    try:
        from backend.services.mn2_float_gate import assess as float_assess
        fg = float_assess(amount)
        if not fg.get("allowed") and fg.get("code") == "float_insufficient":
            return jsonify({
                "success": False,
                "error": "Hot wallet float is below safety threshold for large withdrawals. Try again later or contact support.",
                "code": "float_insufficient",
                "float_gate": fg,
            }), 503
    except ImportError:
        pass

    # Hold gate via unified hold registry (on-ramp, P2P, pending commits).
    try:
        from backend.services.mn2_hold_registry import assert_withdrawable
        hold_gate = assert_withdrawable(user_id, amount)
        if not hold_gate.get("allowed"):
            return jsonify({
                "success": False,
                "error": hold_gate.get("error"),
                "code": hold_gate.get("code", "hold_blocked"),
                "held_mn2": hold_gate.get("held_mn2"),
                "withdrawable_mn2": hold_gate.get("withdrawable_mn2"),
                "holds": hold_gate.get("holds"),
            }), 400
    except ImportError:
        pass

    # Reserve balance before RPC send (two-phase commit).
    commit_id = None
    try:
        from backend.services.mn2_balance_commit import begin_withdrawal, finalize_withdrawal, abort as abort_commit
        reserve = begin_withdrawal(
            user_id, amount, metadata={"address": address, "fee": fee, "amount_sent": amount_sent},
        )
        if not reserve.get("success"):
            return jsonify({"success": False, "error": reserve.get("error", "Could not reserve balance")}), 400
        commit_id = reserve.get("commit_id")
    except ImportError:
        if (bal.get("mn2_balance") or 0) < amount:
            return jsonify({"success": False, "error": "Insufficient balance"}), 400

    import time
    t0 = time.perf_counter()
    send_r = sendtoaddress(address, amount_sent)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    if send_r.get("error"):
        if commit_id:
            try:
                from backend.services.mn2_balance_commit import abort as abort_commit
                abort_commit(commit_id, reason=send_r.get("error", "send failed"))
            except Exception:
                pass
        return jsonify({"success": False, "error": send_r.get("error", "Send failed")}), 500
    txid = send_r.get("result")
    if not txid or not isinstance(txid, str):
        if commit_id:
            try:
                from backend.services.mn2_balance_commit import abort as abort_commit
                abort_commit(commit_id, reason="missing txid")
            except Exception:
                pass
        return jsonify({"success": False, "error": "RPC did not return txid"}), 500

    if commit_id:
        try:
            from backend.services.mn2_balance_commit import finalize_withdrawal
            fin = finalize_withdrawal(
                commit_id,
                txid=txid.strip(),
                address=address,
                fee=fee,
                amount_sent=amount_sent,
                extra_metadata={"withdrawal_duration_ms": duration_ms},
            )
            if not fin.get("success"):
                _log.error("Withdraw finalize failed after RPC send: %s", fin)
        except ImportError:
            commit_id = None

    if not commit_id:
        unified_points_db.add_points(
            user_id,
            "mn2_balance",
            -amount,
            source="mn2_withdrawal",
            metadata={"txid": txid, "address": address, "fee": fee, "amount_sent": amount_sent},
        )
        append_entry(
            user_id=user_id,
            entry_type="withdrawal",
            amount=amount,
            txid=txid.strip(),
            address=address,
            metadata={"fee": fee, "amount_sent": amount_sent, "withdrawal_duration_ms": duration_ms},
        )
    try:
        from backend.services.mn2_withdrawal_guard import record_success
        record_success(user_id, address)
    except Exception:
        pass

    return jsonify({
        "success": True,
        "txid": txid.strip(),
        "explorer_tx_url": _explorer_tx_url(txid),
        "amount_sent": amount_sent,
        "fee": fee,
    }), 200


@mn2_bp.route("/api/mn2/withdraw/security", methods=["GET"])
def mn2_withdraw_security_status():
    """GET — whitelist + TOTP status for the signed-in user."""
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "auth_required", "code": "auth_required"}), 401
    try:
        from backend.services.mn2_withdrawal_security import get_security_status
        cfg = _load_mn2_config()
        status = get_security_status(user_id)
        status["withdrawal_requires_whitelist"] = bool(cfg.get("withdrawal_requires_whitelist"))
        status["withdrawal_new_address_cooldown_hours"] = float(cfg.get("withdrawal_new_address_cooldown_hours") or 0)
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/withdraw/whitelist", methods=["POST"])
def mn2_withdraw_whitelist_mutate():
    """POST { action: add|remove, address } — manage withdrawal address whitelist."""
    user_id = resolve_user_id(from_body=True, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "auth_required"}), 401
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "add").strip().lower()
    address = (data.get("address") or "").strip()
    try:
        from backend.services.mn2_withdrawal_security import add_whitelist_address, remove_whitelist_address
        if action == "remove":
            result = remove_whitelist_address(user_id, address)
        else:
            result = add_whitelist_address(user_id, address)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/withdraw/2fa/setup", methods=["POST"])
def mn2_withdraw_2fa_setup():
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "auth_required"}), 401
    try:
        from backend.services.mn2_withdrawal_security import setup_totp
        return jsonify(setup_totp(user_id)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/withdraw/2fa/enable", methods=["POST"])
def mn2_withdraw_2fa_enable():
    user_id = resolve_user_id(from_body=True, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "auth_required"}), 401
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or data.get("totp_code") or "").strip()
    try:
        from backend.services.mn2_withdrawal_security import enable_totp
        result = enable_totp(user_id, code)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/withdraw/2fa/disable", methods=["POST"])
def mn2_withdraw_2fa_disable():
    user_id = resolve_user_id(from_body=True, from_query=False, use_session=True, use_identification=True)
    if not user_id or user_id == "default_user":
        return jsonify({"success": False, "error": "auth_required"}), 401
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or data.get("totp_code") or "").strip() or None
    try:
        from backend.services.mn2_withdrawal_security import disable_totp
        result = disable_totp(user_id, code)
        return jsonify(result), 200 if result.get("success") else 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/releases", methods=["GET"])
def mn2_releases():
    """Public catalog of MN2 daemon/Qt wallet downloads for /wallets UI."""
    try:
        from backend.services.mn2_release_catalog_service import get_release_catalog
        return jsonify(get_release_catalog())
    except Exception as e:
        _log.exception("mn2_releases failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/network-peers", methods=["GET"])
def mn2_network_peers():
    """Canonical P2P bootstrap peers and conf snippets for wallet operators."""
    try:
        from backend.services.mn2_network_peers_service import conf_snippet, peer_catalog
        fmt = (request.args.get("format") or "").strip().lower()
        if fmt == "conf":
            net = request.args.get("network") or "mainnet"
            body = conf_snippet(net)
            return body, 200, {"Content-Type": "text/plain; charset=utf-8"}
        return jsonify(peer_catalog())
    except Exception as e:
        _log.exception("mn2_network_peers failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/wallet-hub", methods=["GET"])
def mn2_wallet_hub():
    """Aggregated wallet overview: balance, network peers, spork gates, tx preview."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    try:
        from backend.services.mn2_wallet_hub_service import wallet_hub
        return jsonify(wallet_hub(user_id)), 200
    except Exception as e:
        _log.exception("mn2_wallet_hub failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/recent-transactions", methods=["GET"])
def mn2_recent_transactions():
    """Unified recent tx feed: custodial ledger + on-chain deposit txs + exchange trades."""
    user_id = resolve_user_id(from_body=False, from_query=False, use_session=True, use_identification=True)
    limit = min(100, max(1, int(request.args.get("limit", 30))))
    try:
        from backend.services.mn2_wallet_hub_service import recent_transactions_feed
        return jsonify(recent_transactions_feed(user_id, limit=limit)), 200
    except Exception as e:
        _log.exception("mn2_recent_transactions failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/rental-overview", methods=["GET"])
def mn2_rental_overview():
    """Masternode hosting fleet + agent rental listings (+ user rentals when signed in)."""
    user_id = resolve_user_id(from_body=False, from_query=True, use_session=True, use_identification=True)
    try:
        from backend.services.mn2_wallet_hub_service import rental_overview
        return jsonify(rental_overview(user_id if user_id != "default_user" else None)), 200
    except Exception as e:
        _log.exception("mn2_rental_overview failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/network-dashboard", methods=["GET"])
def mn2_network_dashboard():
    """Public network + spork + blocks snapshot for explorer and wallets pages."""
    try:
        from backend.services.mn2_wallet_hub_service import public_network_dashboard
        resp = jsonify(public_network_dashboard())
        resp.headers["Cache-Control"] = "public, max-age=20"
        return resp, 200
    except Exception as e:
        _log.exception("mn2_network_dashboard failed")
        return jsonify({"success": False, "error": str(e)}), 500


@mn2_bp.route("/api/mn2/spork-gates", methods=["GET"])
def mn2_spork_gates():
    """Ops spork gate status for exchange, casino, payout, and maintenance."""
    try:
        from backend.services import mn2_spork_service as spork
        return jsonify({"success": True, **spork.gate_status()}), 200
    except Exception as e:
        _log.exception("mn2_spork_gates failed")
        return jsonify({"success": False, "error": str(e)}), 500
