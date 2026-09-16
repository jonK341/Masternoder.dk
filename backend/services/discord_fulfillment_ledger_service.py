"""Discord community fulfillment ledger — order list for MN2 Discord members."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")
_LEDGER_FILE = "discord_fulfillment_ledger.json"
_ORDER_LIST_FILE = "discord_order_list.json"
_MN2_CHANNEL_CONFIG = os.path.join(_BASE, "data", "discord_mn2_channel.json")

_DEFAULT_LINE_IDS = ("account_link", "role_sync", "casino_vip_role", "hosting_vip_role", "mn2_credit", "trophy_grant")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _data_dir() -> str:
    return os.path.join(_BASE, "data")


def _ledger_path() -> str:
    return os.path.join(_data_dir(), _LEDGER_FILE)


def _order_list_path() -> str:
    return os.path.join(_data_dir(), _ORDER_LIST_FILE)


def _bot_token() -> str:
    return (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()


def _guild_id() -> str:
    return (os.environ.get("DISCORD_GUILD_ID") or "").strip()


def _mn2_channel_id() -> Optional[str]:
    env_id = (os.environ.get("DISCORD_MN2_CHANNEL_ID") or "").strip()
    if env_id.isdigit():
        return env_id
    if os.path.isfile(_MN2_CHANNEL_CONFIG):
        try:
            with open(_MN2_CHANNEL_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cid = str((cfg or {}).get("channel_id") or "").strip()
            if cid.isdigit():
                return cid
        except Exception:
            pass
    return None


def _discord_api_get(path: str, params: Optional[Dict[str, str]] = None) -> Tuple[Optional[Any], Optional[str]]:
    token = _bot_token()
    if not token:
        return None, "bot_token_missing"
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"https://discord.com/api/v10{path}{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "MasternoderBot/1.0 (+[REDACTED])",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None, None
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return None, f"HTTP {exc.code}: {err_body or exc.reason}"
    except Exception as exc:
        return None, str(exc)


def scan_local_linked_users() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.isdir(_IDENT_DIR):
        return rows
    for name in sorted(os.listdir(_IDENT_DIR)):
        if not name.startswith("discord_") or not name.endswith(".json"):
            continue
        path = os.path.join(_IDENT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data.get("linked"):
                continue
            discord_id = str(data.get("discord_id") or name.replace("discord_", "").replace(".json", "")).strip()
            if not discord_id:
                continue
            rows.append(
                {
                    "discord_id": discord_id,
                    "user_id": (data.get("user_id") or "").strip() or None,
                    "discord_username": data.get("discord_username") or data.get("username"),
                    "source": "local_linked",
                }
            )
        except Exception:
            continue
    return rows


def fetch_discord_guild_members(limit: int = 1000) -> Dict[str, Any]:
    """Fetch guild members via Discord API (requires bot token + guild id)."""
    guild = _guild_id()
    token = _bot_token()
    if not token or not guild:
        return {"success": False, "members": [], "error": "bot_or_guild_not_configured", "api_used": False}

    members: List[Dict[str, Any]] = []
    after: Optional[str] = None
    pages = 0
    err: Optional[str] = None
    while pages < 10 and len(members) < limit:
        params: Dict[str, str] = {"limit": "1000"}
        if after:
            params["after"] = after
        data, api_err = _discord_api_get(f"/guilds/{guild}/members", params)
        if api_err:
            err = api_err
            break
        if not isinstance(data, list) or not data:
            break
        for m in data:
            user = m.get("user") if isinstance(m, dict) else {}
            if not isinstance(user, dict):
                continue
            uid = str(user.get("id") or "").strip()
            if not uid:
                continue
            members.append(
                {
                    "discord_id": uid,
                    "discord_username": user.get("global_name") or user.get("username"),
                    "user_id": None,
                    "source": "discord_api_guild",
                }
            )
        after = members[-1]["discord_id"] if members else None
        pages += 1
        if len(data) < 1000:
            break

    return {
        "success": not err,
        "members": members[:limit],
        "error": err,
        "api_used": True,
        "pages": pages,
    }


def fetch_discord_channel_authors(limit: int = 200) -> Dict[str, Any]:
    """Fetch recent message authors from the MN2 Discord channel."""
    channel_id = _mn2_channel_id()
    token = _bot_token()
    if not token or not channel_id:
        return {
            "success": False,
            "members": [],
            "error": "mn2_channel_or_bot_not_configured",
            "api_used": False,
        }

    data, api_err = _discord_api_get(f"/channels/{channel_id}/messages", {"limit": "100"})
    if api_err:
        return {"success": False, "members": [], "error": api_err, "api_used": True}

    seen: Set[str] = set()
    members: List[Dict[str, Any]] = []
    for msg in data if isinstance(data, list) else []:
        author = msg.get("author") if isinstance(msg, dict) else {}
        if not isinstance(author, dict) or author.get("bot"):
            continue
        uid = str(author.get("id") or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        members.append(
            {
                "discord_id": uid,
                "discord_username": author.get("global_name") or author.get("username"),
                "user_id": None,
                "source": "discord_api_channel",
            }
        )
        if len(members) >= limit:
            break

    return {"success": True, "members": members, "error": None, "api_used": True, "channel_id": channel_id}


def _mn2_balance_for_user(user_id: Optional[str]) -> float:
    if not user_id:
        return 0.0
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(user_id) or {}
        return float((pts.get("points") or {}).get("mn2_balance") or 0)
    except Exception:
        return 0.0


def _discord_username_for_user(user_id: str) -> Optional[str]:
    try:
        from backend.services.wallet_v2_service import _discord_profile_from_user

        profile = _discord_profile_from_user(user_id) or {}
        return profile.get("username")
    except Exception:
        return None


def _line_template(
    line_id: str,
    status: str = "pending",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    labels = {
        "account_link": "Account link verified",
        "role_sync": "Linked role metadata sync",
        "casino_vip_role": "Casino VIP role",
        "hosting_vip_role": "Hosting VIP role",
        "mn2_credit": "MN2 community credit",
        "trophy_grant": "Community trophy grant",
    }
    row: Dict[str, Any] = {
        "id": line_id,
        "label": labels.get(line_id, line_id),
        "status": status,
        "fulfilled_at": _iso() if status == "fulfilled" else None,
    }
    if metadata:
        row["metadata"] = metadata
    return row


def _compute_order_lines(
    discord_id: str,
    user_id: Optional[str],
    mn2_balance: float,
    existing_lines: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    existing = {ln.get("id"): ln for ln in (existing_lines or []) if isinstance(ln, dict) and ln.get("id")}
    lines: List[Dict[str, Any]] = []

    linked = bool(user_id)
    min_vip = float(os.environ.get("CASINO_DISCORD_VIP_MIN_MN2", "100"))
    casino_vip = linked and mn2_balance >= min_vip
    hosting_vip = False
    if linked:
        try:
            from backend.services.discord_hosting_vip_service import check_hosting_vip_eligibility

            hosting_vip = bool((check_hosting_vip_eligibility(user_id) or {}).get("eligible"))
        except Exception:
            pass

    specs: List[Tuple[str, str]] = [
        ("account_link", "fulfilled" if linked else "pending"),
        ("role_sync", "fulfilled" if linked else "pending"),
        ("casino_vip_role", "fulfilled" if casino_vip else ("pending" if linked else "skipped")),
        ("hosting_vip_role", "fulfilled" if hosting_vip else ("pending" if linked else "skipped")),
        ("mn2_credit", "pending"),
        ("trophy_grant", "pending"),
    ]

    for line_id, default_status in specs:
        prev = existing.get(line_id) or {}
        if prev.get("status") == "fulfilled":
            lines.append(prev)
            continue
        status = default_status
        if status == "skipped":
            lines.append(_line_template(line_id, status="skipped"))
            continue
        meta: Dict[str, Any] = {}
        if line_id == "mn2_credit":
            meta["default_amount_mn2"] = float(os.environ.get("DISCORD_FULFILLMENT_MN2_CREDIT", "0") or 0)
        if line_id == "trophy_grant":
            meta["trophy_sku"] = os.environ.get("DISCORD_FULFILLMENT_TROPHY_SKU", "discord-community")
        lines.append(_line_template(line_id, status=status, metadata=meta or None))

    return lines


def _aggregate_status(lines: List[Dict[str, Any]]) -> str:
    actionable = [ln for ln in lines if ln.get("status") not in ("skipped", "fulfilled")]
    if not actionable:
        fulfilled = [ln for ln in lines if ln.get("status") == "fulfilled"]
        return "fulfilled" if fulfilled else "pending"
    if all(ln.get("status") == "fulfilled" for ln in lines if ln.get("status") != "skipped"):
        return "fulfilled"
    if any(ln.get("status") == "fulfilled" for ln in lines):
        return "partial"
    return "pending"


def _load_ledger_doc() -> Dict[str, Any]:
    path = _ledger_path()
    with _LOCK:
        if not os.path.isfile(path):
            return {"version": 1, "updated_at": None, "rows": [], "meta": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("rows", [])
                data.setdefault("meta", {})
                return data
        except Exception:
            pass
    return {"version": 1, "updated_at": None, "rows": [], "meta": {}}


def _save_ledger_doc(doc: Dict[str, Any]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    doc["updated_at"] = _iso()
    path = _ledger_path()
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, path)


def _save_order_list_export(doc: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    export = {
        "generated_at": _iso(),
        "total": len(rows),
        "pending": sum(1 for r in rows if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows if r.get("fulfillment_status") == "fulfilled"),
        "sources": doc.get("meta", {}).get("sources", {}),
        "discord_api_used": bool(doc.get("meta", {}).get("discord_api_used")),
        "orders": rows,
    }
    path = _order_list_path()
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)
        os.replace(tmp, path)


def build_order_list(*, use_discord_api: bool = True) -> Dict[str, Any]:
    """Aggregate Discord users + wallet/trophy status into fulfillment ledger."""
    existing_doc = _load_ledger_doc()
    existing_by_id = {
        str(r.get("discord_id")): r
        for r in (existing_doc.get("rows") or [])
        if isinstance(r, dict) and r.get("discord_id")
    }

    merged: Dict[str, Dict[str, Any]] = {}
    source_counts: Dict[str, int] = {"local_linked": 0, "discord_api_guild": 0, "discord_api_channel": 0}

    for row in scan_local_linked_users():
        did = row["discord_id"]
        merged[did] = row
        source_counts["local_linked"] += 1

    api_used = False
    api_notes: List[str] = []
    if use_discord_api and _bot_token():
        guild_result = fetch_discord_guild_members()
        if guild_result.get("api_used"):
            api_used = True
        if guild_result.get("error"):
            api_notes.append(f"guild_members: {guild_result['error']}")
        for row in guild_result.get("members") or []:
            did = row["discord_id"]
            if did not in merged:
                merged[did] = row
                source_counts["discord_api_guild"] += 1
            elif not merged[did].get("discord_username") and row.get("discord_username"):
                merged[did]["discord_username"] = row["discord_username"]

        channel_result = fetch_discord_channel_authors()
        if channel_result.get("api_used"):
            api_used = True
        if channel_result.get("error"):
            api_notes.append(f"channel_authors: {channel_result['error']}")
        for row in channel_result.get("members") or []:
            did = row["discord_id"]
            if did not in merged:
                merged[did] = row
                source_counts["discord_api_channel"] += 1

    rows_out: List[Dict[str, Any]] = []
    for discord_id, seed in sorted(merged.items(), key=lambda x: x[0]):
        user_id = seed.get("user_id")
        if not user_id:
            try:
                from backend.services.discord_link_service import get_user_id_for_discord

                user_id = get_user_id_for_discord(discord_id)
            except Exception:
                user_id = None

        mn2_balance = _mn2_balance_for_user(user_id)
        username = seed.get("discord_username")
        if not username and user_id:
            username = _discord_username_for_user(user_id)

        prev = existing_by_id.get(discord_id) or {}
        lines = _compute_order_lines(
            discord_id,
            user_id,
            mn2_balance,
            existing_lines=prev.get("order_lines"),
        )
        row = {
            "discord_id": discord_id,
            "discord_username": username,
            "user_id": user_id,
            "mn2_balance": mn2_balance,
            "source": seed.get("source") or prev.get("source") or "unknown",
            "fulfillment_status": _aggregate_status(lines),
            "order_lines": lines,
            "created_at": prev.get("created_at") or _iso(),
            "updated_at": _iso(),
        }
        rows_out.append(row)

    doc = {
        "version": 1,
        "updated_at": _iso(),
        "rows": rows_out,
        "meta": {
            "sources": source_counts,
            "discord_api_used": api_used,
            "discord_api_notes": api_notes,
            "bot_configured": bool(_bot_token()),
            "guild_configured": bool(_guild_id()),
            "mn2_channel_configured": bool(_mn2_channel_id()),
        },
    }
    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows_out)

    return {
        "success": True,
        "total": len(rows_out),
        "pending": sum(1 for r in rows_out if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows_out if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows_out if r.get("fulfillment_status") == "fulfilled"),
        "discord_api_used": api_used,
        "sources": source_counts,
        "api_notes": api_notes,
        "ledger_path": _LEDGER_FILE,
        "order_list_path": _ORDER_LIST_FILE,
    }


def get_order_list() -> Dict[str, Any]:
    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    return {
        "success": True,
        "total": len(rows),
        "pending": sum(1 for r in rows if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows if r.get("fulfillment_status") == "fulfilled"),
        "updated_at": doc.get("updated_at"),
        "meta": doc.get("meta") or {},
        "orders": rows,
    }


def get_row_for_discord(discord_id: str) -> Optional[Dict[str, Any]]:
    did = (discord_id or "").strip()
    if not did:
        return None
    for row in _load_ledger_doc().get("rows") or []:
        if str(row.get("discord_id")) == did:
            return row
    return None


def get_user_fulfillment_status(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id or user_id in ("default_user", "guest"):
        return {"success": True, "user_id": user_id, "guest": True, "in_order_list": False}

    discord_id: Optional[str] = None
    try:
        from backend.services.discord_link_service import get_discord_id_for_user

        discord_id = get_discord_id_for_user(user_id)
    except Exception:
        pass

    if not discord_id:
        return {
            "success": True,
            "user_id": user_id,
            "linked": False,
            "in_order_list": False,
            "message": "Link Discord to appear on the community fulfillment order list.",
        }

    row = get_row_for_discord(discord_id)
    if not row:
        build_order_list(use_discord_api=False)
        row = get_row_for_discord(discord_id)

    return {
        "success": True,
        "user_id": user_id,
        "linked": True,
        "discord_id": discord_id,
        "in_order_list": bool(row),
        "fulfillment_status": (row or {}).get("fulfillment_status"),
        "order_lines": (row or {}).get("order_lines") or [],
        "mn2_balance": (row or {}).get("mn2_balance"),
        "order_list_api": "/api/discord/fulfillment/order-list",
    }


def _apply_line_fulfillment(
    row: Dict[str, Any],
    line_items: Optional[List[str]] = None,
    *,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    targets = set(line_items or [ln.get("id") for ln in row.get("order_lines") or [] if ln.get("status") == "pending"])
    applied: List[str] = []
    errors: List[str] = []
    user_id = row.get("user_id")
    discord_id = row.get("discord_id")

    for ln in row.get("order_lines") or []:
        lid = ln.get("id")
        if lid not in targets or ln.get("status") in ("fulfilled", "skipped"):
            continue

        if lid == "mn2_credit":
            amount = float((ln.get("metadata") or {}).get("amount_mn2") or (ln.get("metadata") or {}).get("default_amount_mn2") or 0)
            if amount > 0 and user_id:
                try:
                    from backend.services.unified_points_database import unified_points_db

                    ref = f"discord_fulfill:{discord_id}:{lid}"
                    unified_points_db.add_points(
                        user_id,
                        "mn2_balance",
                        amount,
                        source="discord_fulfillment",
                        metadata={"discord_id": discord_id, "reference": ref, "operator": operator},
                    )
                    try:
                        from backend.services.mn2_ledger import append_entry

                        append_entry(
                            user_id,
                            "deposit",
                            amount,
                            metadata={"source": "discord_fulfillment", "discord_id": discord_id, "reference": ref},
                        )
                    except Exception:
                        pass
                except Exception as exc:
                    errors.append(f"mn2_credit: {exc}")
                    continue

        if lid == "role_sync" and user_id:
            try:
                from backend.services.discord_linked_roles_service import build_metadata_for_user

                build_metadata_for_user(user_id)
            except Exception as exc:
                errors.append(f"role_sync: {exc}")
                continue

        if lid == "hosting_vip_role" and user_id:
            try:
                from backend.services.discord_hosting_vip_service import grant_hosting_vip_role

                grant_hosting_vip_role(user_id, reason="discord_fulfillment")
            except Exception as exc:
                errors.append(f"hosting_vip_role: {exc}")
                continue

        if lid == "trophy_grant" and user_id:
            sku = (ln.get("metadata") or {}).get("trophy_sku") or "discord-community"
            try:
                from backend.routes.shop_routes import _apply_shop_item_effects, _get_shop_items

                item = next((i for i in (_get_shop_items() or []) if i.get("id") == sku), None)
                if item:
                    _apply_shop_item_effects(
                        user_id,
                        sku,
                        item,
                        1,
                        purchase_ref=f"discord_fulfill:{discord_id}",
                    )
            except Exception as exc:
                errors.append(f"trophy_grant: {exc}")
                continue

        ln["status"] = "fulfilled"
        ln["fulfilled_at"] = _iso()
        if operator:
            ln.setdefault("metadata", {})["operator"] = operator
        applied.append(lid)

    row["order_lines"] = _compute_order_lines(
        str(row.get("discord_id")),
        row.get("user_id"),
        float(row.get("mn2_balance") or 0),
        existing_lines=row.get("order_lines"),
    )
    row["fulfillment_status"] = _aggregate_status(row["order_lines"])
    row["updated_at"] = _iso()
    return {"applied": applied, "errors": errors}


def fulfill_order(
    discord_id: str,
    line_items: Optional[List[str]] = None,
    *,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    did = (discord_id or "").strip()
    if not did:
        return {"success": False, "error": "discord_id required"}

    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    target = next((r for r in rows if str(r.get("discord_id")) == did), None)
    if not target:
        build_order_list(use_discord_api=False)
        doc = _load_ledger_doc()
        rows = doc.get("rows") or []
        target = next((r for r in rows if str(r.get("discord_id")) == did), None)
    if not target:
        return {"success": False, "error": "discord_id_not_in_order_list", "discord_id": did}

    result = _apply_line_fulfillment(target, line_items, operator=operator)
    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows)

    return {
        "success": len(result["errors"]) == 0,
        "discord_id": did,
        "fulfillment_status": target.get("fulfillment_status"),
        "applied": result["applied"],
        "errors": result["errors"],
    }


def fulfill_all_pending(*, limit: int = 100, operator: Optional[str] = None) -> Dict[str, Any]:
    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    processed = 0
    fulfilled_count = 0
    errors: List[Dict[str, Any]] = []

    for row in rows:
        if row.get("fulfillment_status") not in ("pending", "partial"):
            continue
        if processed >= limit:
            break
        pending_lines = [ln.get("id") for ln in row.get("order_lines") or [] if ln.get("status") == "pending"]
        if not pending_lines:
            continue
        if not row.get("user_id"):
            errors.append({"discord_id": row.get("discord_id"), "error": "no_linked_user"})
            processed += 1
            continue
        result = _apply_line_fulfillment(row, pending_lines, operator=operator)
        if result["errors"]:
            errors.append({"discord_id": row.get("discord_id"), "errors": result["errors"]})
        else:
            fulfilled_count += 1
        processed += 1

    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows)

    return {
        "success": True,
        "processed": processed,
        "fulfilled_users": fulfilled_count,
        "errors": errors,
        "remaining_pending": sum(1 for r in rows if r.get("fulfillment_status") in ("pending", "partial")),
    }
