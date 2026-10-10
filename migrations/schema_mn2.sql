-- ============================================================================
-- masternoder.dk :: MN2 migration -- Phase A schema (ADDITIVE / NON-DESTRUCTIVE)
-- ----------------------------------------------------------------------------
-- Creates the MN2 first-class tables + a site_pages content table.
-- Every statement is idempotent (IF NOT EXISTS). Existing tables are NEVER
-- dropped or rewritten. The shop_purchases ALTERs are applied by the Python
-- runner (001_create_schema.py) because SQLite lacks ADD COLUMN IF NOT EXISTS.
-- Target engine: SQLite (DATABASE_URL scheme confirmed = sqlite).
-- ============================================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ---------------------------------------------------------------------------
-- 1. mn2_wallets -- one custodial wallet per user (closes gap #1)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mn2_wallets (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id              TEXT    NOT NULL UNIQUE,          -- -> user_accounts.user_id
  wallet_kind          TEXT    NOT NULL DEFAULT 'custodial',  -- custodial | custodial_hd
  account_name         TEXT,                             -- legacy node account name (node-managed model)
  hd_seed_ref          TEXT,                             -- encrypted seed reference (app-HD model), nullable
  label                TEXT,
  balance_confirmed    REAL    NOT NULL DEFAULT 0,
  balance_unconfirmed  REAL    NOT NULL DEFAULT 0,
  address_count        INTEGER NOT NULL DEFAULT 0,
  source               TEXT    NOT NULL DEFAULT 'backfill',  -- backfill | rpc | created
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mn2_wallets_account ON mn2_wallets(account_name);

-- ---------------------------------------------------------------------------
-- 2. mn2_addresses -- every address, owned by a wallet (closes gap #1)
--    MN2 P2PKH version byte = 43 (0x2B), base58 prefix "J" (confirmed).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mn2_addresses (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  address         TEXT    NOT NULL UNIQUE,
  wallet_id       INTEGER NOT NULL REFERENCES mn2_wallets(id) ON DELETE CASCADE,
  user_id         TEXT    NOT NULL,
  account_name    TEXT,
  derivation_path TEXT,                                   -- HD model only; null for legacy keypool
  label           TEXT,
  is_change       INTEGER NOT NULL DEFAULT 0,             -- 0/1
  is_valid        INTEGER NOT NULL DEFAULT 1,             -- base58check + version byte 43 verified
  balance         REAL    NOT NULL DEFAULT 0,
  received_total  REAL    NOT NULL DEFAULT 0,
  first_seen      TIMESTAMP,
  last_used       TIMESTAMP,
  source          TEXT    NOT NULL DEFAULT 'address_book',-- address_book | rpc | imported
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mn2_addresses_user   ON mn2_addresses(user_id);
CREATE INDEX IF NOT EXISTS ix_mn2_addresses_wallet ON mn2_addresses(wallet_id);

-- ---------------------------------------------------------------------------
-- 3. mn2_address_quota -- enforces the 5 addresses/day rule (closes gap #3)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mn2_address_quota (
  user_id          TEXT    NOT NULL,
  quota_date       TEXT    NOT NULL,                      -- YYYY-MM-DD (UTC)
  addresses_issued INTEGER NOT NULL DEFAULT 0,
  quota_limit      INTEGER NOT NULL DEFAULT 5,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, quota_date)
);

-- ---------------------------------------------------------------------------
-- 4. mn2_transactions -- on-chain tx ledger (closes gap #4: drift risk)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mn2_transactions (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  txid          TEXT    NOT NULL,
  vout          INTEGER,
  direction     TEXT    NOT NULL,                         -- in | out
  address       TEXT,
  user_id       TEXT,
  amount        REAL    NOT NULL DEFAULT 0,
  fee           REAL,
  confirmations INTEGER NOT NULL DEFAULT 0,
  blockhash     TEXT,
  blockheight   INTEGER,
  status        TEXT    NOT NULL DEFAULT 'pending',       -- pending | confirmed | failed
  kind          TEXT,                                     -- purchase | withdrawal | deposit | staking | settlement | reward
  ref_type      TEXT,                                     -- e.g. shop_purchase
  ref_id        TEXT,                                     -- e.g. shop_purchases.id
  raw_json      TEXT,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (txid, vout, direction, address)
);
CREATE INDEX IF NOT EXISTS ix_mn2_tx_user   ON mn2_transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_mn2_tx_ref    ON mn2_transactions(ref_type, ref_id);
CREATE INDEX IF NOT EXISTS ix_mn2_tx_status ON mn2_transactions(status);

-- ---------------------------------------------------------------------------
-- 5. mn2_reconciliation_log -- DB vs chain audit trail (closes gap #4)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mn2_reconciliation_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  scope       TEXT    NOT NULL,                           -- wallet | address | tx | global
  entity_id   TEXT,
  db_value    REAL,
  chain_value REAL,
  drift       REAL,
  status      TEXT    NOT NULL,                           -- ok | mismatch | fixed | error
  detail      TEXT
);
CREATE INDEX IF NOT EXISTS ix_mn2_recon_scope ON mn2_reconciliation_log(scope, status);

-- ---------------------------------------------------------------------------
-- 6. site_pages -- content crawled from the public website pages
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS site_pages (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  path         TEXT    NOT NULL UNIQUE,                   -- e.g. /shop
  url          TEXT    NOT NULL,
  title        TEXT,
  http_status  INTEGER,
  content_text TEXT,                                      -- visible text (tags stripped)
  content_html TEXT,                                      -- raw HTML
  byte_size    INTEGER,
  links_json   TEXT,                                      -- JSON array of discovered links
  crawled_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================================================
-- STATS + IDENTITY layer (Phase C): "as many MN2 stats as possible" and
-- "connect all the different user wallets to one real (canonical) wallet".
-- All additive, DB-only, computed from data/*.json + mn2_transactions.
-- NO funds move here. mn2_metrics is the table the empty /api/mn2/stats stub
-- should be wired to serve from.
-- ===========================================================================

-- 7. mn2_identity_aliases -- resolve the same human appearing under many keys
--    ('Jon', 'jon', 'user_1774175477730_f8q8laos5', 'trader_agent_6', ...) to
--    ONE canonical wallet identity. Deterministic normalization + manual overrides.
CREATE TABLE IF NOT EXISTS mn2_identity_aliases (
  alias             TEXT    NOT NULL,                     -- raw identifier as seen in sources
  canonical_user_id TEXT    NOT NULL,                     -- resolved single wallet identity
  source            TEXT,                                 -- which file/endpoint it came from
  method            TEXT    NOT NULL DEFAULT 'normalize', -- exact | normalize | manual
  confidence        REAL    NOT NULL DEFAULT 1.0,
  created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (alias, source)
);
CREATE INDEX IF NOT EXISTS ix_mn2_alias_canon ON mn2_identity_aliases(canonical_user_id);

-- 8. mn2_user_stats -- per canonical-user rollup (the "one real wallet" view)
CREATE TABLE IF NOT EXISTS mn2_user_stats (
  canonical_user_id   TEXT    PRIMARY KEY,
  display_label       TEXT,
  alias_count         INTEGER NOT NULL DEFAULT 0,
  address_count       INTEGER NOT NULL DEFAULT 0,
  valid_address_count INTEGER NOT NULL DEFAULT 0,
  tx_count            INTEGER NOT NULL DEFAULT 0,
  total_in            REAL    NOT NULL DEFAULT 0,
  total_out           REAL    NOT NULL DEFAULT 0,
  net                 REAL    NOT NULL DEFAULT 0,         -- ledger-derived balance
  masternode_count    INTEGER NOT NULL DEFAULT 0,
  collateral_total    REAL    NOT NULL DEFAULT 0,
  order_payment_count INTEGER NOT NULL DEFAULT 0,
  order_payment_mn2   REAL    NOT NULL DEFAULT 0,
  p2p_order_count     INTEGER NOT NULL DEFAULT 0,
  onramp_order_count  INTEGER NOT NULL DEFAULT 0,
  micro_tx_runs       INTEGER NOT NULL DEFAULT 0,
  staking_reserve     REAL    NOT NULL DEFAULT 0,
  first_seen          TIMESTAMP,
  last_seen           TIMESTAMP,
  updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. mn2_metrics -- tall/flexible stat store (global, per-type, per-day, per-user)
CREATE TABLE IF NOT EXISTS mn2_metrics (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  metric_key  TEXT    NOT NULL,                           -- e.g. ledger.entries_total
  value_num   REAL,
  value_text  TEXT,
  scope       TEXT    NOT NULL DEFAULT 'global',          -- global | type | day | user | source
  scope_id    TEXT    NOT NULL DEFAULT '',
  as_of       TEXT    NOT NULL DEFAULT '',                -- '' for timeless, else YYYY-MM-DD
  source      TEXT,
  updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (metric_key, scope, scope_id, as_of)
);
CREATE INDEX IF NOT EXISTS ix_mn2_metrics_key ON mn2_metrics(metric_key, scope);

-- 10. mn2_stats_runs -- audit of each stats computation
CREATE TABLE IF NOT EXISTS mn2_stats_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  run_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status          TEXT    NOT NULL,                       -- ok | partial | error
  users_computed  INTEGER NOT NULL DEFAULT 0,
  metrics_written INTEGER NOT NULL DEFAULT 0,
  detail          TEXT
);

-- 11. mn2_micro_tx_plan -- SIMULATION ONLY of the "small transaction start".
--     Rows are the exact sendtoaddress calls that WOULD be made; nothing here is
--     broadcast. status is always 'simulated' unless a later, explicitly-authorized
--     live phase changes it. No RPC is ever called by the simulator.
CREATE TABLE IF NOT EXISTS mn2_micro_tx_plan (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_run      TEXT    NOT NULL,                         -- batch id (timestamp)
  from_user_id  TEXT,
  from_address  TEXT,
  to_address    TEXT,
  amount_mn2    REAL    NOT NULL DEFAULT 0,
  fee_mn2       REAL    NOT NULL DEFAULT 0,
  total_debit   REAL    NOT NULL DEFAULT 0,
  rpc_method    TEXT    NOT NULL DEFAULT 'sendtoaddress',
  status        TEXT    NOT NULL DEFAULT 'simulated',     -- simulated | rejected | (live only: sent)
  reason        TEXT,                                     -- e.g. below_min | over_daily_limit | ok
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_mn2_microtx_plan_run ON mn2_micro_tx_plan(plan_run, status);

-- ---------------------------------------------------------------------------
-- 12. data_store_catalog -- inventory of EVERY data/*.json store on the box.
--     One row per discovered file: shape, record count, field union, and flags
--     for whether it carries user refs / MN2 addresses / amounts / paypal data.
--     This is the index that answers "what else is useful in the database".
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_store_catalog (
  store_name        TEXT    PRIMARY KEY,                  -- e.g. camgirls_performers
  file_path         TEXT    NOT NULL,
  kind              TEXT,                                 -- dict | list | jsonl
  record_count      INTEGER NOT NULL DEFAULT 0,
  top_keys_json     TEXT,                                 -- JSON: top-level keys (dict) or elem0 keys (list)
  record_fields_json TEXT,                                -- JSON: union of record field names
  has_user_ref      INTEGER NOT NULL DEFAULT 0,
  has_mn2_address   INTEGER NOT NULL DEFAULT 0,
  has_amount        INTEGER NOT NULL DEFAULT 0,
  has_paypal        INTEGER NOT NULL DEFAULT 0,
  byte_size         INTEGER,
  content_hash      TEXT,                                 -- sha1 of file (change detection)
  ingested_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 13. data_store_records -- raw "conformed" layer: one row per record of every
--     ingested store, with the full payload preserved AND the common fields
--     (user_ref, mn2_address, amount, currency, status, created_at) promoted to
--     real columns so they are queryable/joinable. This materializes rows for
--     all ~100 logical entities at once without hand-guessing 100 schemas.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_store_records (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  store_name    TEXT    NOT NULL,
  record_key    TEXT    NOT NULL,                         -- dict key, or list index, or jsonl line no
  user_ref      TEXT,                                     -- nearest user identifier in the record
  mn2_address   TEXT,                                     -- a checksum-valid MN2 address, if present
  amount        REAL,                                     -- amount-like numeric, if present
  currency      TEXT,                                     -- mn2 | usd | coins | points | ...
  status        TEXT,
  created_at    TEXT,
  payload_json  TEXT    NOT NULL,                         -- full original record
  ingested_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (store_name, record_key)
);
CREATE INDEX IF NOT EXISTS ix_dsr_store ON data_store_records(store_name);
CREATE INDEX IF NOT EXISTS ix_dsr_user  ON data_store_records(user_ref);
CREATE INDEX IF NOT EXISTS ix_dsr_addr  ON data_store_records(mn2_address);

-- ---------------------------------------------------------------------------
-- 14. camgirls_* -- typed promotion of the camgirls sub-app stores.
--     DB-level content only. paypal_orders is REVENUE TRACKING (mirror of the
--     existing camgirls_paypal_orders.json); it does NOT initiate live captures.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS camgirls_performers (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  performer_id  TEXT    NOT NULL UNIQUE,
  stage_name    TEXT,
  user_ref      TEXT,
  status        TEXT,
  payout_address TEXT,
  paypal_email  TEXT,
  rating        REAL,
  followers     INTEGER NOT NULL DEFAULT 0,
  bio           TEXT,
  payload_json  TEXT,
  version       TEXT    NOT NULL DEFAULT '11.0.0',        -- bumped to 12.0.0 only by an authorized live phase
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS camgirls_payout_addresses (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  performer_id  TEXT,
  user_ref      TEXT,
  address       TEXT    NOT NULL UNIQUE,
  is_valid      INTEGER NOT NULL DEFAULT 1,
  network       TEXT    NOT NULL DEFAULT 'mn2',
  linked_wallet_id INTEGER,                               -- -> mn2_wallets.id when consolidated
  payload_json  TEXT,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS camgirls_paypal_orders (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id      TEXT    NOT NULL UNIQUE,
  performer_id  TEXT,
  user_ref      TEXT,
  gross_usd     REAL    NOT NULL DEFAULT 0,
  net_usd       REAL,
  fee_usd       REAL,
  currency      TEXT    NOT NULL DEFAULT 'USD',
  status        TEXT,                                     -- COMPLETED | APPROVED | PENDING | ...
  capture_id    TEXT,
  payout_mn2    REAL,                                     -- MN2 credited to performer, if any
  payout_txid   TEXT,
  created_at    TEXT,
  payload_json  TEXT,
  ingested_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS camgirls_activity (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  performer_id  TEXT,
  user_ref      TEXT,
  kind          TEXT,                                     -- achievement | activity_point | tip | stream | ...
  points        REAL    NOT NULL DEFAULT 0,
  amount        REAL,
  currency      TEXT,
  label         TEXT,
  occurred_at   TEXT,
  payload_json  TEXT,
  ingested_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (performer_id, kind, label, occurred_at)
);
CREATE INDEX IF NOT EXISTS ix_cg_activity_perf ON camgirls_activity(performer_id, kind);
