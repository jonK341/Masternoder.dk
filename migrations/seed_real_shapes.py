#!/usr/bin/env python3
"""LOCAL FIXTURE mimicking the REAL server shapes discovered by the probe.

Creates in ../data/ :  mn2_ledger.json, mn2_order_payments.json,
mn2_masternode_hosts.json, mn2_treasury_addresses.json
And builds ../test_real.db with the REAL shop_purchases schema (price_paid_*,
payment_ref, payment_method). Uses valid MN2 addresses (version byte 43).
NOT production data. Do not run on the server.
"""
import hashlib
import json
import os
import random
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mn2_addr import hash160_to_address  # noqa: E402

DATA = os.path.abspath(os.path.join(HERE, "..", "local_fixture_data"))
DB = os.path.abspath(os.path.join(HERE, "..", "test_real.db"))
random.seed(4242)


def addr(n):
    return hash160_to_address(hashlib.sha256(f"a{n}".encode()).digest()[:20])


def txid(n):
    return hashlib.sha256(f"tx{n}".encode()).hexdigest()


def main():
    os.makedirs(DATA, exist_ok=True)
    users = [f"user_{3000+i}" for i in range(10)]

    # ---- mn2_ledger.json ----
    types = ["deposit", "withdrawal", "purchase", "staking_reward", "fee", "airdrop"]
    entries = []
    for i in range(60):
        uid = random.choice(users)
        t = random.choice(types)
        has_tx = random.random() < 0.7
        entries.append({
            "user_id": uid, "type": t,
            "amount": round(random.uniform(-50, 200), 4),
            "txid": txid(i) if has_tx else "",
            "address": addr(i), "created_at": "2026-09-2%d 10:00:00" % (i % 9 + 1),
            "metadata": {"src": "fixture"},
        })
    json.dump({"entries": entries}, open(os.path.join(DATA, "mn2_ledger.json"), "w"), indent=2)

    # ---- shop_purchases (REAL schema) + order_payments joined by payment_ref ----
    conn = sqlite3.connect(DB)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS user_accounts(user_id TEXT PRIMARY KEY, username TEXT);
    CREATE TABLE IF NOT EXISTS shop_purchases(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, item_id TEXT,
      item_name TEXT, quantity INTEGER, price_type TEXT,
      price_paid_coins REAL, price_paid_points REAL, price_paid_usd REAL,
      balance_before REAL, balance_after REAL, purchase_status TEXT,
      payment_method TEXT, payment_ref TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.execute("DELETE FROM shop_purchases")
    methods = ["coins", "points", "usd", "mn2"]
    refs = []
    pid = 0
    for uid in users:
        for j in range(4):
            pid += 1
            m = random.choice(methods)
            ref = f"pref_{pid:05d}" if m == "mn2" else f"other_{pid:05d}"
            if m == "mn2":
                refs.append((ref, uid, pid))
            conn.execute(
                """INSERT INTO shop_purchases(user_id,item_id,item_name,quantity,price_type,
                     price_paid_coins,price_paid_points,price_paid_usd,balance_before,balance_after,
                     purchase_status,payment_method,payment_ref)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (uid, f"item_{j}", f"Item {j}", 1, m,
                 10.0 if m == "coins" else 0, 100.0 if m == "points" else 0,
                 5.0 if m == "usd" else 0, 100.0, 90.0, "completed", m, ref))
            conn.execute("INSERT OR IGNORE INTO user_accounts(user_id,username) VALUES(?,?)", (uid, uid))
    conn.commit()

    # order_payments only for the mn2-method purchases; some have a txid, some don't
    orders = []
    for k, (ref, uid, _pid) in enumerate(refs):
        orders.append({
            "payment_ref": ref, "user_id": uid, "address": addr(500 + k),
            "amount_mn2": round(random.uniform(1, 30), 4), "item_id": f"item_{k%4}",
            "item_name": f"Item {k%4}", "quantity": 1, "price_coins": 0,
            "txid": txid(700 + k) if k % 2 == 0 else "",
        })
    json.dump({"orders": orders}, open(os.path.join(DATA, "mn2_order_payments.json"), "w"), indent=2)

    # ---- mn2_masternode_hosts.json ----
    hosts = []
    for h in range(6):
        hosts.append({
            "id": f"mnh_{h}", "label": f"node-{h}", "status": "active",
            "collateral_address": addr(900 + h), "collateral_txid": txid(900 + h),
            "collateral_vout": 0, "broadcast_address": addr(950 + h),
            "owner_user_id": users[h % len(users)], "collateral_mn2": 1000,
        })
    json.dump({"hosts": hosts, "updated_at": "2026-09-26"}, open(os.path.join(DATA, "mn2_masternode_hosts.json"), "w"), indent=2)

    # ---- mn2_treasury_addresses.json ----
    json.dump({"addresses": [{"address": addr(1200 + t), "label": f"treasury_{t}"} for t in range(3)]},
              open(os.path.join(DATA, "mn2_treasury_addresses.json"), "w"), indent=2)

    # ---- extra real-shape sources so the stats engine has inputs ----
    # micro-tx config (the "small transaction start" knobs) + state with duplicate aliases
    json.dump({"enabled": False, "min_amount_mn2": 0.1, "max_amount_mn2": 5.0,
               "fee_mn2": 0.01, "confirmations": 1, "daily_limit_mn2": 50},
              open(os.path.join(DATA, "mn2_micro_tx_config.json"), "w"), indent=2)
    json.dump({"users": {"Jon": {"runs": 3}, "jon": {"runs": 2}, users[0]: {"runs": 5},
                         "Sander Sahk": {"runs": 1}, "trader_agent_6": {"runs": 9}},
               "runs": 20},
              open(os.path.join(DATA, "mn2_micro_tx_state.json"), "w"), indent=2)
    # p2p
    json.dump({f"l_{i}": {"listing_id": f"l_{i}", "seller_id": users[i % len(users)],
                          "mn2_total": 100 + i, "mn2_available": 50, "mn2_reserved": 0,
                          "price_usd_per_mn2": 6.8, "status": "open", "created_at": "2026-09-20"}
               for i in range(5)},
              open(os.path.join(DATA, "mn2_p2p_listings.json"), "w"), indent=2)
    json.dump({f"po_{i}": {"order_id": f"po_{i}", "listing_id": f"l_{i%5}",
                           "buyer_id": users[(i+1) % len(users)], "seller_id": users[i % len(users)],
                           "mn2_amount": 25 + i, "price_usd_per_mn2": 6.8, "usd_amount": (25+i)*6.8,
                           "platform_fee_usd": 0.5, "status": "completed"}
               for i in range(7)},
              open(os.path.join(DATA, "mn2_p2p_orders.json"), "w"), indent=2)
    # onramp
    json.dump({f"q_{i}": {"order_id": f"q_{i}", "user_id": users[i % len(users)],
                          "usd_amount": 50 + i, "mn2_price_usd": 6.8, "mn2_amount": (50+i)/6.8,
                          "status": "completed"}
               for i in range(4)},
              open(os.path.join(DATA, "mn2_onramp_orders.json"), "w"), indent=2)
    # masternode orders (dict keyed by order_id)
    json.dump({f"mnq_{i}": {"order_id": f"mnq_{i}", "user_id": users[i % len(users)], "slots": 2,
                            "mn2_total": 2000, "currency": "mn2", "status": "active"}
               for i in range(6)},
              open(os.path.join(DATA, "mn2_masternode_orders.json"), "w"), indent=2)
    # staking reserve, copy trading, config, awards
    json.dump({"reserve_mn2": 12345.6, "updated_at": "2026-09-25"},
              open(os.path.join(DATA, "mn2_staking_reserve.json"), "w"), indent=2)
    json.dump({"followers": {"Jon": {"copy_from": "trader_agent_6"}, "user_3001": {"copy_from": "trader_agent_5"}}},
              open(os.path.join(DATA, "mn2_copy_trading.json"), "w"), indent=2)
    json.dump({"ticker": "MN2", "decimals": 8, "confirmations": 6, "address_version": 43},
              open(os.path.join(DATA, "mn2_config.json"), "w"), indent=2)
    json.dump([{"user_id": users[0], "amount": 12.5, "reason": "yield"},
               {"user_id": users[1], "amount": 7.0, "reason": "yield"}],
              open(os.path.join(DATA, "aggregator_mn2_awards.json"), "w"), indent=2)

    # ---- sub-app wallet stores ("different sites") for the harvester ----
    json.dump({"agents": [
        {"agent_id": "agent_1", "user_id": users[0], "address": addr(2001), "label": "agent_main"},
        {"agent_id": "agent_2", "owner_user_id": users[1], "address": addr(2002)}]},
        open(os.path.join(DATA, "agent_wallets.json"), "w"), indent=2)
    json.dump({users[2]: {"address": addr(2010), "network": "mn2"},
               users[3]: {"address": addr(2011), "network": "mn2"}},
        open(os.path.join(DATA, "camgirls_payout_addresses.json"), "w"), indent=2)
    exdir = os.path.join(DATA, "crypto_exchange", "wallets")
    os.makedirs(exdir, exist_ok=True)
    json.dump({"wallet_address": addr(2020), "user_id": users[4], "balance_mn2": 33.3},
              open(os.path.join(exdir, "exchange_agent_mn2_yield.json"), "w"), indent=2)
    # a decoy: invalid/foreign string that must NOT be harvested
    json.dump({"note": "not an address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "user_id": users[5]},
              open(os.path.join(DATA, "decoy_no_addresses.json"), "w"), indent=2)

    # ---- camgirls sub-app stores (probe-shaped) for the ingester + promoter ----
    json.dump({"performers": [
        {"performer_id": "cg_01", "stage_name": "Ava", "user_id": users[2], "status": "active",
         "payout_address": addr(2010), "paypal_email": "ava@example.com", "rating": 4.8,
         "followers": 120, "bio": "hello"},
        {"performer_id": "cg_02", "stage_name": "Mia", "user_id": users[3], "status": "active",
         "payout_address": addr(2011), "paypal_email": "mia@example.com", "rating": 4.5,
         "followers": 80, "bio": "hi"}]},
        open(os.path.join(DATA, "camgirls_performers.json"), "w"), indent=2)
    json.dump({"orders": [
        {"order_id": "PP_1", "performer_id": "cg_01", "user_id": users[6], "gross_usd": 25.0,
         "net_usd": 24.3, "fee_usd": 0.7, "currency": "USD", "status": "COMPLETED",
         "capture_id": "CAP_1", "payout_mn2": 3.6, "created_at": "2026-09-01"},
        {"order_id": "PP_2", "performer_id": "cg_02", "user_id": users[7], "gross_usd": 10.0,
         "net_usd": 9.7, "fee_usd": 0.3, "currency": "USD", "status": "COMPLETED",
         "capture_id": "CAP_2", "payout_mn2": 1.45, "created_at": "2026-09-02"}]},
        open(os.path.join(DATA, "camgirls_paypal_orders.json"), "w"), indent=2)
    json.dump({"fanclub": {"cg_01": [users[6], users[7]], "cg_02": [users[8]]}},
              open(os.path.join(DATA, "camgirls_fanclub.json"), "w"), indent=2)
    json.dump({"favorites": {users[6]: ["cg_01"], users[8]: ["cg_02"]}},
              open(os.path.join(DATA, "camgirls_favorites.json"), "w"), indent=2)
    json.dump({"verified": [{"performer_id": "cg_01", "age_verified": True, "verified_at": "2026-08-01"},
                            {"performer_id": "cg_02", "age_verified": True, "verified_at": "2026-08-02"}]},
              open(os.path.join(DATA, "camgirls_age_verified.json"), "w"), indent=2)
    with open(os.path.join(DATA, "camgirls_chat.jsonl"), "w") as fh:
        fh.write(json.dumps({"performer_id": "cg_01", "user_id": users[6], "msg": "hey", "ts": "2026-09-01T10:00:00"}) + "\n")
        fh.write(json.dumps({"performer_id": "cg_02", "user_id": users[8], "msg": "hi", "ts": "2026-09-02T11:00:00"}) + "\n")
    json.dump({"activity": [
        {"performer_id": "cg_01", "kind": "achievement", "label": "first_stream", "points": 50, "occurred_at": "2026-09-01"},
        {"performer_id": "cg_01", "kind": "activity_point", "label": "stream_60m", "points": 30, "occurred_at": "2026-09-01"},
        {"performer_id": "cg_02", "kind": "activity_point", "label": "stream_30m", "points": 15, "occurred_at": "2026-09-02"}]},
        open(os.path.join(DATA, "camgirls_activity.json"), "w"), indent=2)

    conn.close()
    print(f"[fixture] wrote mn2_*.json sources into {DATA}")
    print(f"[fixture] built {DB}: shop_purchases={pid} (mn2-method={len(refs)}), order_payments={len(orders)}, hosts={len(hosts)}")


if __name__ == "__main__":
    main()
