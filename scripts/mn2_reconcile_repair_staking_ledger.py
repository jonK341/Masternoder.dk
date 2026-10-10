#!/usr/bin/env python3
"""
Backfill stake / unstake / staking_reward ledger rows to match canonical stores:
  - live staked: unified points `mn2_staked` (same basis as PoR external users)
  - rewards: mn2_staking_rewards.jsonl per user

Dry-run by default. Use --apply to append repair ledger entries (no balance movement).

Run on server: cd /var/www/html && python3 scripts/mn2_reconcile_repair_staking_ledger.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_REPAIR_META = "mn2_reconcile_repair_staking_ledger"
_TOL = 1e-6


def _ledger_net_stake(entries: list, uid: str) -> float:
    net = 0.0
    for e in entries:
        if e.get("user_id") != uid:
            continue
        t = e.get("type")
        amt = float(e.get("amount", 0) or 0)
        if t == "stake":
            net += amt
        elif t == "unstake":
            net -= amt
    return round(net, 8)


def _ledger_reward(entries: list, uid: str) -> float:
    return round(
        sum(
            float(e.get("amount", 0) or 0)
            for e in entries
            if e.get("user_id") == uid and e.get("type") == "staking_reward"
        ),
        8,
    )


def _external_points_staked() -> dict[str, float]:
    from backend.services.mn2_proof_of_reserves_service import _POINTS_DIR, _is_paper_mn2_account

    out: dict[str, float] = {}
    try:
        names = [fn for fn in os.listdir(_POINTS_DIR) if fn.endswith(".json")]
    except Exception:
        return out
    for fn in names:
        uid = fn[:-5]
        if _is_paper_mn2_account(uid, os.path.join(_POINTS_DIR, fn)):
            continue
        try:
            with open(os.path.join(_POINTS_DIR, fn), encoding="utf-8") as f:
                raw = json.load(f) or {}
        except Exception:
            continue
        systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
        staked = float(systems.get("mn2_staked", 0) or 0)
        bal = float(systems.get("mn2_balance", 0) or 0)
        if abs(staked) <= _TOL and bal <= _TOL:
            continue
        out[uid] = round(staked, 8)
    return out


def _external_reward_rows() -> dict[str, float]:
    from backend.services.mn2_staking_reconcile_service import _is_paper_user

    path = os.path.join(ROOT, "data", "mn2_staking_rewards.jsonl")
    out: dict[str, float] = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            uid = str(row.get("user_id") or "")
            if not uid or _is_paper_user(uid):
                continue
            out[uid] = round(out.get(uid, 0.0) + float(row.get("reward_mn2", 0) or 0), 8)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    from backend.services import mn2_ledger

    entries = mn2_ledger._load_entries()
    stake_targets = _external_points_staked()
    reward_targets = _external_reward_rows()
    users = set(stake_targets) | set(reward_targets)

    stake_repairs: list[tuple[str, str, float]] = []
    reward_repairs: list[tuple[str, float]] = []

    for uid in sorted(users):
        target_stake = stake_targets.get(uid, 0.0)
        net = _ledger_net_stake(entries, uid)
        delta = round(target_stake - net, 8)
        if abs(delta) > _TOL:
            if delta > 0:
                stake_repairs.append((uid, "stake", delta))
            else:
                stake_repairs.append((uid, "unstake", -delta))

        target_rw = reward_targets.get(uid, 0.0)
        led_rw = _ledger_reward(entries, uid)
        rd = round(target_rw - led_rw, 8)
        if abs(rd) > _TOL:
            if rd < 0:
                print(f"WARN: ledger rewards exceed jsonl for {uid}: ledger={led_rw} jsonl={target_rw}")
                continue
            reward_repairs.append((uid, rd))

    print(f"stake repairs: {len(stake_repairs)} reward repairs: {len(reward_repairs)}")
    for uid, typ, amt in stake_repairs:
        print(f"  {typ} {uid} {amt}")
    for uid, amt in reward_repairs:
        print(f"  staking_reward {uid} {amt}")

    if not stake_repairs and not reward_repairs:
        print("no repair needed")
        return 0
    if not args.apply:
        print("dry-run only — pass --apply to write ledger entries")
        return 1

    for uid, typ, amt in stake_repairs:
        mn2_ledger.append_entry(
            uid,
            typ,
            amt,
            metadata={"repair": _REPAIR_META},
        )
    for uid, amt in reward_repairs:
        mn2_ledger.append_entry(
            uid,
            "staking_reward",
            amt,
            metadata={"repair": _REPAIR_META},
        )
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
