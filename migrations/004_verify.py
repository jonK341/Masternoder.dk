#!/usr/bin/env python3
"""Verify the migrated DB: row counts, integrity checks, reconciliation summary."""
import sqlite3
import sys

TABLES = [
    "mn2_wallets", "mn2_addresses", "mn2_address_quota", "mn2_transactions",
    "mn2_reconciliation_log", "mn2_identity_aliases", "mn2_user_stats",
    "mn2_metrics", "mn2_stats_runs", "site_pages",
    "data_store_catalog", "data_store_records",
    "camgirls_performers", "camgirls_payout_addresses", "camgirls_paypal_orders",
    "camgirls_activity",
    "user_accounts", "user_profiles", "shop_purchases",
]


def main(db):
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    print(f"== integrity_check: {conn.execute('PRAGMA integrity_check').fetchone()[0]} ==")
    print(f"== foreign_key_check: {conn.execute('PRAGMA foreign_key_check').fetchall() or 'clean'} ==")
    print("\n== row counts ==")
    for t in TABLES:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:26} {n}")
        except sqlite3.Error as e:
            print(f"  {t:26} MISSING ({e})")

    print("\n== MN2 sanity ==")
    print("  invalid addresses        :",
          conn.execute("SELECT COUNT(*) FROM mn2_addresses WHERE is_valid=0").fetchone()[0])
    print("  orphan addresses         :",
          conn.execute("SELECT COUNT(*) FROM mn2_addresses a LEFT JOIN mn2_wallets w ON a.wallet_id=w.id WHERE w.id IS NULL").fetchone()[0])
    print("  wallets w/ count mismatch:",
          conn.execute("""SELECT COUNT(*) FROM mn2_wallets w WHERE address_count <>
                          (SELECT COUNT(*) FROM mn2_addresses a WHERE a.wallet_id=w.id)""").fetchone()[0])
    print("  duplicate addresses      :",
          conn.execute("SELECT COUNT(*) FROM (SELECT address FROM mn2_addresses GROUP BY address HAVING COUNT(*)>1)").fetchone()[0])

    print("\n== purchases on-chain linkage ==")
    print("  onchain=1 (MN2-linked)   :",
          conn.execute("SELECT COUNT(*) FROM shop_purchases WHERE onchain=1").fetchone()[0])
    print("  onchain=0 (off-chain:    :",
          conn.execute("SELECT COUNT(*) FROM shop_purchases WHERE onchain=0 OR onchain IS NULL").fetchone()[0],
          "coins/points/usd, not a gap)")

    print("\n== reconciliation_log by status ==")
    for status, n in conn.execute(
            "SELECT status, COUNT(*) FROM mn2_reconciliation_log GROUP BY status"):
        print(f"  {status:12} {n}")

    print("\n== site_pages (crawled) ==")
    for path, st, sz in conn.execute(
            "SELECT path, http_status, byte_size FROM site_pages ORDER BY path"):
        print(f"  {path:24} {st}  {sz}B")

    print("\n== MN2 stats (Phase C) ==")
    try:
        n_metrics = conn.execute("SELECT COUNT(*) FROM mn2_metrics").fetchone()[0]
        n_users = conn.execute("SELECT COUNT(*) FROM mn2_user_stats").fetchone()[0]
        n_alias = conn.execute("SELECT COUNT(*) FROM mn2_identity_aliases").fetchone()[0]
        merged = conn.execute(
            "SELECT COUNT(*) FROM mn2_user_stats WHERE alias_count > 1").fetchone()[0]
        print(f"  metric rows            : {n_metrics}")
        print(f"  canonical users        : {n_users}  (with merged aliases: {merged})")
        print(f"  identity aliases       : {n_alias}")
        print("  headline metrics:")
        for key in ("ledger.entries_total", "ledger.volume_net", "transactions.total",
                    "addresses.total", "masternodes.hosts", "payments.count",
                    "shop.purchases_onchain", "microtx.enabled", "price.mn2_usd"):
            row = conn.execute(
                "SELECT value_num, value_text FROM mn2_metrics WHERE metric_key=? AND scope='global' "
                "ORDER BY as_of DESC LIMIT 1", (key,)).fetchone()
            if row:
                print(f"    {key:28} {row[0] if row[0] is not None else row[1]}")
        last = conn.execute(
            "SELECT run_at, status, users_computed, metrics_written FROM mn2_stats_runs "
            "ORDER BY id DESC LIMIT 1").fetchone()
        if last:
            print(f"  last stats run         : {last[0]} status={last[1]} users={last[2]} metrics={last[3]}")
    except sqlite3.Error as e:
        print(f"  (stats tables not present yet: {e})")

    print("\n== data stores (Phase E) ==")
    try:
        ns = conn.execute("SELECT COUNT(*) FROM data_store_catalog").fetchone()[0]
        nr = conn.execute("SELECT COUNT(*) FROM data_store_records").fetchone()[0]
        na = conn.execute("SELECT COUNT(*) FROM data_store_catalog WHERE has_mn2_address=1").fetchone()[0]
        npay = conn.execute("SELECT COUNT(*) FROM data_store_catalog WHERE has_paypal=1").fetchone()[0]
        print(f"  stores catalogued      : {ns}  (records={nr})")
        print(f"  stores w/ MN2 address  : {na}")
        print(f"  stores w/ paypal/revenue: {npay}")
        print("  top stores by records  :")
        for name, n in conn.execute(
                "SELECT store_name, record_count FROM data_store_catalog ORDER BY record_count DESC LIMIT 12"):
            print(f"    {name:48} {n}")
    except sqlite3.Error as e:
        print(f"  (data-store tables not present yet: {e})")

    print("\n== camgirls (Phase E2) ==")
    try:
        perf = conn.execute("SELECT COUNT(*) FROM camgirls_performers").fetchone()[0]
        addr = conn.execute("SELECT COUNT(*) FROM camgirls_payout_addresses").fetchone()[0]
        bad = conn.execute("SELECT COUNT(*) FROM camgirls_payout_addresses WHERE is_valid=0").fetchone()[0]
        pp = conn.execute("SELECT COUNT(*) FROM camgirls_paypal_orders").fetchone()[0]
        gross = conn.execute("SELECT ROUND(COALESCE(SUM(gross_usd),0),2) FROM camgirls_paypal_orders").fetchone()[0]
        act = conn.execute("SELECT COUNT(*) FROM camgirls_activity").fetchone()[0]
        pts = conn.execute("SELECT ROUND(COALESCE(SUM(points),0),2) FROM camgirls_activity").fetchone()[0]
        ptx = conn.execute("SELECT COUNT(*) FROM mn2_transactions WHERE ref_type='camgirls_payout'").fetchone()[0]
        ver = conn.execute("SELECT DISTINCT version FROM camgirls_performers").fetchall()
        print(f"  performers             : {perf}  versions={[v[0] for v in ver]}")
        print(f"  payout addresses       : {addr}  (invalid={bad})")
        print(f"  paypal orders          : {pp}  gross=${gross}")
        print(f"  activity rows / points : {act} / {pts}")
        print(f"  MN2 payout txs mirrored: {ptx}")
    except sqlite3.Error as e:
        print(f"  (camgirls tables not present yet: {e})")
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "../local_replica.db")
