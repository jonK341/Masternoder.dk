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
    user_id = resolve_user_id(from_body=False, from_query=True)
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
    if status == "pending" and (order.get("expires_at") or "") < datetime.utcnow().isoformat() + "Z":
        status = "expired"
    out = {
        "success": True,
        "payment_ref": order["payment_ref"],
        "status": status,
        "address": order.get("address"),
        "amount_mn2": order.get("amount_mn2"),
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


@mn2_bp.route("/api/mn2/ops/verify-user", methods=["POST"])
def mn2_ops_verify_user():
    """Add or remove user_id from verified list (Phase 10). Body: user_id, action=add|remove. Requires ops secret."""
    if not _ops_authorized():
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    try:
        data = request.get_json() or {}
        uid = (data.get("user_id") or request.args.get("user_id") or "").strip()
        action = (data.get("action") or request.args.get("action") or "add").strip().lower()
        if not uid:
            return jsonify({"success": False, "error": "user_id required"}), 400
        from backend.services.mn2_verification import add_verified, remove_verified
        if action == "remove":
            ok = remove_verified(uid)
            return jsonify({"success": True, "action": "remove", "removed": ok}), 200
        ok = add_verified(uid)
        return jsonify({"success": True, "action": "add", "added": ok}), 200
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

    user_id = resolve_user_id(from_body=True, from_query=True)
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

    # On-ramp hold gate: MN2 bought via PayPal is not withdrawable until its clearance
    # window passes (defeats buy -> chargeback -> withdraw). Fail-open if service errors.
    try:
        from backend.services.mn2_onramp_service import held_amount as _onramp_held
        held = float(_onramp_held(user_id) or 0)
        if held > 0 and (bal.get("mn2_balance") or 0) - held < amount:
            return jsonify({
                "success": False,
                "error": (f"{held:.4f} MN2 from a recent PayPal purchase is still in its clearance "
                          f"hold window and cannot be withdrawn yet."),
                "code": "onramp_hold",
                "held_mn2": round(held, 8),
            }), 400
    except Exception:
        pass

    # Send (amount - fee) to address (record duration for ledger)
    import time
    t0 = time.perf_counter()
    send_r = sendtoaddress(address, amount_sent)
    duration_ms = round((time.perf_counter() - t0) * 1000, 2)
    if send_r.get("error"):
        return jsonify({"success": False, "error": send_r.get("error", "Send failed")}), 500
    txid = send_r.get("result")
    if not txid or not isinstance(txid, str):
        return jsonify({"success": False, "error": "RPC did not return txid"}), 500

    # Deduct from balance and record ledger
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

    return jsonify({
        "success": True,
        "txid": txid.strip(),
        "explorer_tx_url": _explorer_tx_url(txid),
        "amount_sent": amount_sent,
        "fee": fee,
    }), 200
