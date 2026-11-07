#!/usr/bin/env python3
"""Audit on-chain MN2 across daemon datadirs and configured address files (run on server)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

CLI = os.environ.get("MN2_CLI", "/opt/masternoder2d/masternoder2-cli")
WEB = os.environ.get("MN2_WEB_ROOT", "/var/www/html")
DATADIRS = [
    ("ops_hosting", "/var/www/html/config"),
    ("legacy_root", "/root/.masternoder2"),
]


def cli(datadir: str, *args: str, timeout: int = 120):
    cmd = [CLI, f"-datadir={datadir}", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return {"error": err or out or f"exit {proc.returncode}"}
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        if out.lower() in ("true", "false"):
            return out.lower() == "true"
        try:
            return float(out)
        except ValueError:
            return out


def audit_datadir(label: str, datadir: str) -> dict:
    row: dict = {"label": label, "datadir": datadir}
    wpath = os.path.join(datadir, "wallet.dat")
    row["wallet_dat_exists"] = os.path.isfile(wpath)
    row["wallet_dat_bytes"] = os.path.getsize(wpath) if row["wallet_dat_exists"] else 0

    bal = cli(datadir, "getbalance")
    row["getbalance_mn2"] = bal if isinstance(bal, (int, float)) else None
    if isinstance(bal, dict):
        row["getbalance_error"] = bal.get("error")

    info = cli(datadir, "getwalletinfo")
    if isinstance(info, dict) and "error" not in info:
        row["walletinfo"] = {
            k: info.get(k)
            for k in (
                "balance",
                "unconfirmed_balance",
                "immature_balance",
                "txcount",
                "unlocked_until",
            )
            if k in info
        }

    unspent = cli(datadir, "listunspent", "0", "9999999")
    utxos = unspent if isinstance(unspent, list) else []
    by_addr: dict = defaultdict(lambda: {"amount": 0.0, "utxo_count": 0})
    total = 0.0
    collateral_5k = 0
    for utxo in utxos:
        if not isinstance(utxo, dict):
            continue
        amt = float(utxo.get("amount") or 0)
        addr = str(utxo.get("address") or "?")
        total += amt
        if abs(amt - 5000.0) < 1e-6:
            collateral_5k += 1
        bucket = by_addr[addr]
        bucket["amount"] += amt
        bucket["utxo_count"] += 1

    row["utxo_count"] = len(utxos)
    row["listunspent_total_mn2"] = round(total, 8)
    row["collateral_5000_utxos"] = collateral_5k
    row["addresses_with_utxos"] = sorted(
        [
            {"address": a, "amount_mn2": round(v["amount"], 8), "utxo_count": v["utxo_count"]}
            for a, v in by_addr.items()
        ],
        key=lambda x: -x["amount_mn2"],
    )

    received = cli(datadir, "listreceivedbyaddress", "0", "true")
    if isinstance(received, list):
        row["addresses_ever_received"] = sorted(
            [
                {
                    "address": str(item.get("address") or ""),
                    "total_received_mn2": round(float(item.get("amount") or 0), 8),
                    "tx_count": len(item.get("txids") or []),
                }
                for item in received
                if isinstance(item, dict) and (float(item.get("amount") or 0) > 0 or item.get("txids"))
            ],
            key=lambda x: -x["total_received_mn2"],
        )[:100]
    elif isinstance(received, dict) and received.get("error"):
        row["listreceivedbyaddress_error"] = str(received["error"])[:300]

    return row


def collect_all_known_addresses() -> set[str]:
    addrs: set[str] = set()
    base = Path(WEB)

    def walk(obj):
        if isinstance(obj, dict):
            for key, val in obj.items():
                if key in ("address", "addr", "deposit_address", "shop_revenue_address") and isinstance(val, str):
                    if len(val) >= 26:
                        addrs.add(val.strip())
                else:
                    walk(val)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, str) and len(obj) >= 30 and obj[0] in "J":
            addrs.add(obj.strip())

    for pattern in ("data/mn2*.json", "data/agent_treasury.json"):
        for path in base.glob(pattern):
            try:
                walk(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
    meta_path = base / "logs/unified_points/agent_treasury.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8")).get("last_metadata") or {}
            if meta.get("address"):
                addrs.add(str(meta["address"]).strip())
        except Exception:
            pass
    return addrs


def probe_addresses_in_datadir(datadir: str, addresses: set[str]) -> list:
    rows = []
    for addr in sorted(addresses):
        info = cli(datadir, "getaddressinfo", addr)
        recv = cli(datadir, "getreceivedbyaddress", addr, "0")
        row = {"address": addr}
        if isinstance(info, dict) and "error" not in info:
            row["ismine"] = info.get("ismine")
            row["iswatchonly"] = info.get("iswatchonly")
            row["in_ops_wallet"] = bool(info.get("ismine") or info.get("iswatchonly"))
        elif isinstance(info, dict):
            row["getaddressinfo_error"] = str(info.get("error"))[:200]
        if isinstance(recv, (int, float)):
            row["received_mn2"] = round(float(recv), 8)
        elif isinstance(recv, dict):
            row["getreceivedbyaddress_error"] = str(recv.get("error"))[:200]
        rows.append(row)
    return rows


def load_config_addresses() -> list:
    out = []
    files = [
        ("data/agent_treasury.json", lambda d: [{"key": "treasury", "address": d.get("address")}] if d.get("address") else []),
        ("data/mn2_config.json", lambda d: [{"key": "shop_revenue_address", "address": d.get("shop_revenue_address")}] if d.get("shop_revenue_address") else []),
    ]
    base = Path(WEB)
    for rel, extract in files:
        path = base / rel
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            out.append({"file": rel, "error": str(exc)})
            continue
        addrs = extract(data) if isinstance(data, dict) else []
        out.append({"file": rel, "addresses": [a for a in addrs if a.get("address")]})
    for name in ("mn2_user_addresses.json", "mn2_treasury_addresses.json", "mn2_address_book.json"):
        path = base / "data" / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            out.append({"file": f"data/{name}", "error": str(exc)})
            continue
        listed = []
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, str) and len(val) >= 26:
                    listed.append({"key": key, "address": val})
                elif isinstance(val, dict) and val.get("address"):
                    listed.append({"key": key, "address": val["address"]})
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    listed.append({"key": str(i), "address": item})
                elif isinstance(item, dict) and item.get("address"):
                    listed.append({"key": item.get("label") or str(i), "address": item["address"]})
        out.append({"file": f"data/{name}", "address_count": len(listed), "addresses_sample": listed[:25]})
    return out


def main() -> int:
    known = collect_all_known_addresses()
    ops_dd = DATADIRS[0][1]
    report = {
        "datadirs": [audit_datadir(l, d) for l, d in DATADIRS],
        "config_files": load_config_addresses(),
        "known_address_count": len(known),
        "address_probe_ops_wallet": probe_addresses_in_datadir(ops_dd, known),
    }
    spendable = sum(float(r.get("listunspent_total_mn2") or 0) for r in report["datadirs"])
    balance_sum = sum(
        float(r["getbalance_mn2"])
        for r in report["datadirs"]
        if isinstance(r.get("getbalance_mn2"), (int, float))
    )
    db_path = Path(WEB) / "instance/database.db"
    if db_path.is_file():
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cur = conn.execute(
                "SELECT address, user_id, balance, received_total FROM mn2_addresses "
                "ORDER BY COALESCE(balance,0) DESC, COALESCE(received_total,0) DESC LIMIT 50"
            )
            report["mn2_addresses_db"] = [
                {
                    "address": r[0],
                    "user_id": r[1],
                    "balance_db": r[2],
                    "received_total_db": r[3],
                }
                for r in cur.fetchall()
            ]
            conn.close()
        except Exception as exc:
            report["mn2_addresses_db_error"] = str(exc)

    with_balance = [r for r in report["address_probe_ops_wallet"] if (r.get("received_mn2") or 0) > 0]
    report["summary"] = {
        "on_chain_spendable_mn2_all_datadirs": round(spendable, 8),
        "getbalance_sum_all_datadirs": round(balance_sum, 8),
        "total_utxos": sum(int(r.get("utxo_count") or 0) for r in report["datadirs"]),
        "collateral_5000_utxos_total": sum(int(r.get("collateral_5000_utxos") or 0) for r in report["datadirs"]),
        "addresses_with_active_utxos": sum(len(r.get("addresses_with_utxos") or []) for r in report["datadirs"]),
        "known_addresses_tracked": len(known),
        "known_addresses_with_any_received_in_ops_wallet": len(with_balance),
        "total_received_on_tracked_addresses_ops_wallet": round(sum(r.get("received_mn2") or 0 for r in with_balance), 8),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
