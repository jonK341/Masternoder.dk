#!/usr/bin/env python3
"""Phase F — multi-coin wallets, NFT DB, payment instrument slots, staking/hosting capacity.

Applies schema_platform_extensions.sql and backfills from:
  - crypto_assets seed (MN2 + placeholders)
  - mn2_wallets -> user_wallet_accounts
  - user_accounts / user_profiles -> user_financial_profiles
  - data/nft_catalog.json -> nft_catalog_skus
  - data/nft_exchange_state.json -> nft_editions / listings / trades
  - mn2_masternode_hosts.json (optional) -> staking_positions + hosting

DB-only. Never stores raw card numbers — payment_instruments holds provider tokens only.

  python 010_platform_wallet_nft_payments.py --db instance/database.db --data-dir data
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_SQL = os.path.join(HERE, "schema_platform_extensions.sql")

DEFAULT_ASSETS = [
    {
        "asset_code": "mn2",
        "display_name": "MasterNoder Coin",
        "symbol": "MN2",
        "decimals": 8,
        "chain": "mn2",
        "is_native": 1,
        "staking_enabled": 1,
        "hosting_enabled": 1,
        "min_stake": 1000.0,
        "payout_asset_code": "mn2",
        "rpc_profile": "mn2_rpc",
        "sort_order": 0,
    },
    {
        "asset_code": "btc_bridge",
        "display_name": "Bitcoin (hosted)",
        "symbol": "BTC",
        "decimals": 8,
        "chain": "btc",
        "is_native": 0,
        "staking_enabled": 0,
        "hosting_enabled": 1,
        "min_stake": None,
        "payout_asset_code": "btc_bridge",
        "rpc_profile": "btc_watch",
        "sort_order": 10,
    },
    {
        "asset_code": "eth_bridge",
        "display_name": "Ethereum (hosted)",
        "symbol": "ETH",
        "decimals": 18,
        "chain": "eth",
        "is_native": 0,
        "staking_enabled": 1,
        "hosting_enabled": 1,
        "min_stake": 32.0,
        "payout_asset_code": "eth_bridge",
        "rpc_profile": "eth_watch",
        "sort_order": 20,
    },
]


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: str):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return json.load(handle)
    except Exception:
        return None


def apply_schema(conn: sqlite3.Connection) -> None:
    with open(SCHEMA_SQL, encoding="utf-8") as handle:
        conn.executescript(handle.read())
    print("[schema] applied schema_platform_extensions.sql")


def seed_crypto_assets(conn: sqlite3.Connection) -> int:
    n = 0
    for row in DEFAULT_ASSETS:
        conn.execute(
            """
            INSERT INTO crypto_assets (
              asset_code, display_name, symbol, decimals, chain,
              is_native, staking_enabled, hosting_enabled, min_stake,
              payout_asset_code, rpc_profile, sort_order, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(asset_code) DO UPDATE SET
              display_name=excluded.display_name,
              symbol=excluded.symbol,
              staking_enabled=excluded.staking_enabled,
              hosting_enabled=excluded.hosting_enabled,
              min_stake=excluded.min_stake,
              updated_at=excluded.updated_at
            """,
            (
                row["asset_code"],
                row["display_name"],
                row["symbol"],
                row["decimals"],
                row["chain"],
                1 if row.get("is_native") else 0,
                1 if row.get("staking_enabled") else 0,
                1 if row.get("hosting_enabled") else 0,
                row.get("min_stake"),
                row.get("payout_asset_code"),
                row.get("rpc_profile"),
                row.get("sort_order", 0),
                utcnow(),
            ),
        )
        n += 1
    print(f"[assets] seeded/updated {n} crypto_assets rows")
    return n


def backfill_wallet_accounts(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "mn2_wallets"):
        print("[wallets] mn2_wallets missing — skip user_wallet_accounts backfill")
        return 0
    rows = conn.execute(
        """
        SELECT id, user_id, wallet_kind, label,
               balance_confirmed, balance_unconfirmed, address_count, source
        FROM mn2_wallets
        """
    ).fetchall()
    n = 0
    for wid, user_id, kind, label, bal_c, bal_u, addr_c, source in rows:
        conn.execute(
            """
            INSERT INTO user_wallet_accounts (
              user_id, asset_code, wallet_kind, legacy_mn2_wallet_id, label,
              balance_confirmed, balance_unconfirmed, address_count,
              staking_enabled, hosting_enabled, source, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,1,1,?,?)
            ON CONFLICT(user_id, asset_code) DO UPDATE SET
              legacy_mn2_wallet_id=excluded.legacy_mn2_wallet_id,
              balance_confirmed=excluded.balance_confirmed,
              balance_unconfirmed=excluded.balance_unconfirmed,
              address_count=excluded.address_count,
              updated_at=excluded.updated_at
            """,
            (
                user_id,
                "mn2",
                kind or "custodial",
                wid,
                label,
                bal_c or 0,
                bal_u or 0,
                addr_c or 0,
                source or "backfill",
                utcnow(),
            ),
        )
        n += 1
    print(f"[wallets] synced {n} user_wallet_accounts from mn2_wallets")
    return n


def backfill_financial_profiles(conn: sqlite3.Connection) -> int:
    n = 0
    if _table_exists(conn, "user_accounts"):
        for user_id, username in conn.execute(
            "SELECT user_id, username FROM user_accounts"
        ).fetchall():
            display = username or user_id
            conn.execute(
                """
                INSERT INTO user_financial_profiles (user_id, display_name, updated_at)
                VALUES (?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                  display_name=COALESCE(excluded.display_name, user_financial_profiles.display_name),
                  updated_at=excluded.updated_at
                """,
                (user_id, display, utcnow()),
            )
            n += 1
    if _table_exists(conn, "user_profiles"):
        for user_id, display_name in conn.execute(
            "SELECT user_id, display_name FROM user_profiles WHERE display_name IS NOT NULL"
        ).fetchall():
            conn.execute(
                """
                INSERT INTO user_financial_profiles (user_id, display_name, updated_at)
                VALUES (?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                  display_name=COALESCE(excluded.display_name, user_financial_profiles.display_name),
                  updated_at=excluded.updated_at
                """,
                (user_id, display_name, utcnow()),
            )
            n += 1
    print(f"[profiles] upserted user_financial_profiles ({n} passes)")
    return n


def backfill_nft_catalog(conn: sqlite3.Connection, data_dir: str) -> int:
    path = os.path.join(data_dir, "nft_catalog.json")
    data = read_json(path)
    if not isinstance(data, dict):
        print("[nft] nft_catalog.json missing — skip SKU backfill")
        return 0
    n = 0
    for row in data.get("skus") or []:
        if not isinstance(row, dict) or not row.get("sku"):
            continue
        conn.execute(
            """
            INSERT INTO nft_catalog_skus (
              sku, name, series, rarity, supply, price_usd, price_coins,
              trophy_id, emblem_icon, avatar_url, description, metadata_json, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(sku) DO UPDATE SET
              name=excluded.name,
              series=excluded.series,
              rarity=excluded.rarity,
              supply=excluded.supply,
              price_usd=excluded.price_usd,
              price_coins=excluded.price_coins,
              trophy_id=excluded.trophy_id,
              emblem_icon=excluded.emblem_icon,
              avatar_url=excluded.avatar_url,
              description=excluded.description,
              metadata_json=excluded.metadata_json,
              updated_at=excluded.updated_at
            """,
            (
                row.get("sku"),
                row.get("name") or row.get("sku"),
                row.get("series"),
                row.get("rarity"),
                int(row.get("supply") or 0),
                float(row.get("price_usd") or 0),
                int(row.get("price_coins") or 0),
                row.get("trophy_id"),
                row.get("emblem_icon"),
                row.get("avatar_url"),
                row.get("description"),
                json.dumps(
                    {
                        k: v
                        for k, v in row.items()
                        if k
                        not in {
                            "sku",
                            "name",
                            "series",
                            "rarity",
                            "supply",
                            "price_usd",
                            "price_coins",
                            "trophy_id",
                            "emblem_icon",
                            "avatar_url",
                            "description",
                        }
                    },
                    ensure_ascii=False,
                ),
                utcnow(),
            ),
        )
        n += 1
    print(f"[nft] catalog SKUs upserted: {n}")
    return n


def backfill_nft_state(conn: sqlite3.Connection, data_dir: str) -> tuple[int, int, int]:
    path = os.path.join(data_dir, "nft_exchange_state.json")
    data = read_json(path)
    if not isinstance(data, dict):
        print("[nft] nft_exchange_state.json missing — skip editions/listings/trades")
        return 0, 0, 0
    e_n = 0
    for row in data.get("editions") or []:
        if not isinstance(row, dict) or not row.get("edition_id"):
            continue
        sku = str(row.get("sku") or "").strip()
        if not sku:
            continue
        if not conn.execute("SELECT 1 FROM nft_catalog_skus WHERE sku=?", (sku,)).fetchone():
            conn.execute(
                """
                INSERT OR IGNORE INTO nft_catalog_skus (sku, name, supply, updated_at)
                VALUES (?,?,0,?)
                """,
                (sku, row.get("name") or sku, utcnow()),
            )
        conn.execute(
            """
            INSERT INTO nft_editions (
              edition_id, sku, serial, owner_user_id, status,
              mint_source, minted_at, purchase_ref, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?)
            ON CONFLICT(edition_id) DO UPDATE SET
              owner_user_id=excluded.owner_user_id,
              status=excluded.status,
              metadata_json=excluded.metadata_json
            """,
            (
                row.get("edition_id"),
                sku,
                int(row.get("serial") or 0),
                str(row.get("owner_id") or row.get("owner_user_id") or ""),
                row.get("status") or "held",
                row.get("mint_source"),
                row.get("minted_at"),
                row.get("purchase_ref"),
                json.dumps(row, ensure_ascii=False),
            ),
        )
        e_n += 1
    l_n = 0
    for row in data.get("listings") or []:
        if not isinstance(row, dict) or not row.get("listing_id"):
            continue
        conn.execute(
            """
            INSERT INTO nft_market_listings (
              listing_id, edition_id, seller_user_id, price_coins, fee_coins,
              status, created_at, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(listing_id) DO UPDATE SET
              status=excluded.status,
              price_coins=excluded.price_coins,
              metadata_json=excluded.metadata_json
            """,
            (
                row.get("listing_id"),
                row.get("edition_id"),
                str(row.get("seller_id") or row.get("seller_user_id") or ""),
                int(row.get("price_coins") or 0),
                int(row.get("fee_coins") or 0),
                row.get("status") or "open",
                row.get("created_at"),
                json.dumps(row, ensure_ascii=False),
            ),
        )
        l_n += 1
    t_n = 0
    for row in data.get("trades") or []:
        if not isinstance(row, dict):
            continue
        trade_id = row.get("trade_id") or row.get("id")
        if not trade_id:
            continue
        conn.execute(
            """
            INSERT INTO nft_market_trades (
              trade_id, listing_id, edition_id, sku, buyer_user_id, seller_user_id,
              price_coins, fee_coins, traded_at, metadata_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(trade_id) DO UPDATE SET
              metadata_json=excluded.metadata_json
            """,
            (
                trade_id,
                row.get("listing_id"),
                row.get("edition_id"),
                row.get("sku"),
                str(row.get("buyer_id") or row.get("buyer_user_id") or ""),
                str(row.get("seller_id") or row.get("seller_user_id") or ""),
                int(row.get("price_coins") or 0),
                int(row.get("fee_coins") or 0),
                row.get("traded_at") or row.get("created_at"),
                json.dumps(row, ensure_ascii=False),
            ),
        )
        t_n += 1
    print(f"[nft] state: editions={e_n} listings={l_n} trades={t_n}")
    return e_n, l_n, t_n


def seed_hosting_capacity(conn: sqlite3.Connection, data_dir: str) -> None:
    total_mn2 = 500
    hosts = read_json(os.path.join(data_dir, "mn2_masternode_hosts.json"))
    if isinstance(hosts, dict):
        host_list = hosts.get("hosts") or []
        if host_list:
            total_mn2 = max(total_mn2, len(host_list))
    conn.execute(
        """
        INSERT INTO hosting_capacity (asset_code, network, total_slots, reserved_slots, active_slots, updated_at)
        VALUES ('mn2','main',?,?,?,?)
        ON CONFLICT(asset_code, network) DO UPDATE SET
          total_slots=MAX(hosting_capacity.total_slots, excluded.total_slots),
          active_slots=excluded.active_slots,
          updated_at=excluded.updated_at
        """,
        (total_mn2, 0, 0, utcnow()),
    )
    for asset in ("btc_bridge", "eth_bridge"):
        conn.execute(
            """
            INSERT INTO hosting_capacity (asset_code, network, total_slots, reserved_slots, active_slots, updated_at)
            VALUES (?,'main',0,0,0,?)
            ON CONFLICT(asset_code, network) DO NOTHING
            """,
            (asset, utcnow()),
        )
    print(f"[hosting] capacity rows ready (mn2 total_slots>={total_mn2})")


def backfill_staking_from_hosts(conn: sqlite3.Connection, data_dir: str) -> int:
    path = os.path.join(data_dir, "mn2_masternode_hosts.json")
    data = read_json(path)
    if not isinstance(data, dict):
        return 0
    n = 0
    for host in data.get("hosts") or []:
        if not isinstance(host, dict):
            continue
        user_id = str(host.get("owner_user_id") or host.get("user_id") or "").strip()
        if not user_id:
            continue
        collateral = host.get("collateral_address") or host.get("broadcast_address")
        amount = float(host.get("collateral_amount") or host.get("amount") or 0)
        conn.execute(
            """
            INSERT INTO staking_positions (
              user_id, asset_code, position_kind, amount_staked, collateral_address,
              collateral_txid, host_slot_id, status, started_at, metadata_json, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                "mn2",
                "masternode",
                amount,
                collateral,
                host.get("collateral_txid"),
                host.get("host_id") or host.get("slot_id"),
                host.get("status") or "active",
                host.get("created_at") or host.get("started_at"),
                json.dumps(host, ensure_ascii=False),
                utcnow(),
            ),
        )
        n += 1
    if n:
        print(f"[staking] imported {n} masternode positions from mn2_masternode_hosts.json")
    return n


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def run(db_path: str, data_dir: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        apply_schema(conn)
        seed_crypto_assets(conn)
        backfill_wallet_accounts(conn)
        backfill_financial_profiles(conn)
        backfill_nft_catalog(conn, data_dir)
        backfill_nft_state(conn, data_dir)
        seed_hosting_capacity(conn, data_dir)
        backfill_staking_from_hosts(conn, data_dir)
        conn.commit()
    finally:
        conn.close()
    print(f"[done] platform wallet/NFT/payment migration applied to {db_path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="instance/database.db")
    ap.add_argument("--data-dir", default="data")
    args = ap.parse_args()
    db_path = args.db
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)
    data_dir = args.data_dir
    if not os.path.isabs(data_dir):
        data_dir = os.path.join(os.getcwd(), data_dir)
    run(db_path, data_dir)


if __name__ == "__main__":
    main()
