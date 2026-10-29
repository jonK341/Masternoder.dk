# MN2 Database Migration — masternoder.dk

Closes the gap: the SQLite DB (`instance/database.db`, ~436MB, 39 tables) held users,
profiles, shop purchases, points… but **zero MN2 tables**. Money moved but the DB
couldn't see/join/audit/reconcile it. This migration gives MN2 a first-class,
reconcilable home and stores the public website pages.

> Built and **dry-run locally first**. The live DB is remote and SSH is blocked from
> the sandbox, so the server run is a **guided self-run**: copy the folder over,
> run `probe`, paste output, then run `apply`.

## Real data sources (confirmed by server probe)

MN2 state is **not** in a single address book — it's spread across `data/*.json`:

| File | Shape | Used for |
|------|-------|----------|
| `mn2_ledger.json` | `{entries:[{user_id,type,amount,txid,address,created_at,metadata}]}` (~1917) | `mn2_transactions`, wallets, addresses |
| `mn2_order_payments.json` | `{orders:[{payment_ref,user_id,address,amount_mn2,…}]}` (~78) | link `shop_purchases` by `payment_ref` |
| `mn2_masternode_hosts.json` | `{hosts:[{collateral_address,collateral_txid,broadcast_address,owner_user_id,…}]}` (~44) | masternode wallets/addresses/tx |
| `mn2_treasury_addresses.json` | treasury addresses | `__treasury__` system wallet |
| `mn2_user_addresses.json` / `mn2_address_book.json` | user→address (created lazily; may not exist yet) | addresses if present |

`shop_purchases` has **no single amount column** — it's `price_paid_coins/points/usd`
+ `payment_method`. MN2 amounts come from `mn2_order_payments.amount_mn2`. Only
`payment_method='mn2'` purchases are expected on-chain; coin/point/USD purchases are
**not** a gap.

## What it creates

`mn2_wallets`, `mn2_addresses`, `mn2_address_quota`, `mn2_transactions`,
`mn2_reconciliation_log`, `site_pages`; and ALTERs `shop_purchases` += `mn2_txid`,
`mn2_address`, `onchain`. **Additive, idempotent, read-only on-chain, moves no funds,
never touches `wallet.dat` or the daemon.**

### Phase C — stats + wallet-identity consolidation (`005_compute_stats.py`)

Adds `mn2_metrics` (tall key/value: global, per-type, per-day, per-source),
`mn2_user_stats` (per-user rollup), `mn2_identity_aliases`, `mn2_stats_runs`.
Aggregates every `data/mn2_*.json` + the DB into ~78 metrics (ledger volume in/out/net,
tx counts by type/day, addresses valid/invalid, masternode collateral, p2p/onramp
volume, micro-tx config, treasury, staking, copy-trading, awards, live `mn2_usd_price`,
and the **shop MN2 revenue address** from `/api/mn2/balance`).

**Identity consolidation:** the same human appears under many keys (`Jon`, `jon`,
`user_1774…`, `trader_agent_6`). The stats engine merges identifiers that normalize
to the same string into ONE `canonical_user_id` (safe, deterministic). It does **not**
merge a display name with a `user_id` without evidence — add a manual row to
`mn2_identity_aliases` to force that. This is **DB-level** consolidation only: it does
**not** move coins on-chain.

`mn2_metrics` is the table the empty auto-created `/api/mn2/stats` stub should be wired
to serve from (app-code change — see Notes).

## Files

| File | Purpose |
|------|---------|
| `schema_mn2.sql` | MN2 + `site_pages` DDL (idempotent) |
| `mn2_addr.py` | Pure-stdlib base58check, MN2 version byte 43 / prefix "J" |
| `000_safety_backup.py` | Timestamped DB backup + integrity check |
| `001_create_schema.py` | Phase A: create tables, ALTER `shop_purchases` (`--print-db` helper) |
| `002_backfill_mn2.py` | Phase B: `--probe` (read-only) / backfill / `--reset` |
| `005_compute_stats.py` | Phase C: stats + wallet-identity consolidation |
| `003_crawl_site_pages.py` | Crawl public pages → `site_pages` |
| `004_verify.py` | Row counts + integrity + reconciliation summary |
| `009_camgirls.py` | Phase E: camgirls performers, payouts, PayPal mirror |
| `010_platform_wallet_nft_payments.py` | Phase F: multi-coin wallets, NFT tables, payment token slots, staking/hosting capacity |
| `schema_platform_extensions.sql` | DDL for Phase F (used by 010) |
| `run_server_migration.sh` | `probe` then `apply` (resolves its own folder) |
| `PROBE.sh` | Standalone read-only schema/shape probe |
| `seed_local_sample.py`, `seed_real_shapes.py` | **LOCAL ONLY** fixtures (never run on server) |

> ⚠️ **Do not copy `local_fixture_data/`, `seed_*.py`, `*.db` to the server** — the
> fixtures use the same filenames as real prod data and would overwrite it. Copy only
> the `migration/` scripts.

## Local dry-run (executed here)

```bash
cd migration
python seed_real_shapes.py                                   # builds fixture + test_real.db
python 001_create_schema.py --db ../test_real.db --standins
python 002_backfill_mn2.py --db ../test_real.db --data-dir ../local_fixture_data --probe
python 002_backfill_mn2.py --db ../test_real.db --data-dir ../local_fixture_data
python 004_verify.py ../test_real.db
```

Result: integrity `ok`, 11 wallets / 83 addresses (0 invalid) / 74 tx /
8 purchases linked via `payment_ref` / only 4 real gaps (MN2 payments missing a
txid). Idempotent across re-runs; `--reset` reproduces identical counts.

## Server run (guided self-run, from `/var/www/html`)

1. Copy the `migration/` **scripts** to `/var/www/html/migrations`.
2. Snapshot the node wallet: `mn2-cli backupwallet /var/backups/mn2_wallet_<STAMP>.dat`
3. `./migrations/run_server_migration.sh probe` → paste output back (confirms the real
   ledger `type` taxonomy + `payment_method` values before any write).
4. After review: `./migrations/run_server_migration.sh apply` → backup → schema →
   backfill → crawl → verify. Paste output.
5. Re-run cleanly anytime: `002_backfill_mn2.py … --reset`.

## Notes / next phase

- **type→direction mapping** is keyword + amount-sign based; confirm against the probe
  taxonomy. If wrong, `--reset` and re-run (the MN2 tables are isolated).
- **RPC enrichment (not built yet):** live balances/confirmations and real txid linkage
  need node RPC (`MN2_RPC_URL`, server-only). That's the next phase — reconciles
  `mn2_transactions` against the chain and fills `mn2_reconciliation_log` drift.
- **Non-HD wallet** (`walletversion 61000`): schema supports `wallet_kind`/`hd_seed_ref`/
  `derivation_path` but backfill records legacy/custodial only.
- **Pre-existing FK orphans:** 52 `user_profiles` rows reference missing `user_accounts`
  (unrelated to this migration; backfill sets `foreign_keys=OFF` so they don't block).
