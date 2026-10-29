-- ============================================================================
-- Platform extensions: multi-coin wallets, NFT registry, payment tokens, staking.
-- ADDITIVE / IDEMPOTENT. Never stores raw card numbers (PAN/CVV) — tokens only.
-- ============================================================================

PRAGMA journal_mode=WAL;

-- Supported assets (MN2 today; room for more chains/coins)
CREATE TABLE IF NOT EXISTS crypto_assets (
  asset_code          TEXT    PRIMARY KEY,
  display_name        TEXT    NOT NULL,
  symbol              TEXT    NOT NULL,
  decimals            INTEGER NOT NULL DEFAULT 8,
  chain               TEXT    NOT NULL DEFAULT 'mn2',
  is_native           INTEGER NOT NULL DEFAULT 0,
  staking_enabled     INTEGER NOT NULL DEFAULT 0,
  hosting_enabled     INTEGER NOT NULL DEFAULT 0,
  min_stake           REAL,
  payout_asset_code   TEXT,
  rpc_profile         TEXT,
  sort_order          INTEGER NOT NULL DEFAULT 0,
  is_active           INTEGER NOT NULL DEFAULT 1,
  metadata_json       TEXT,
  created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- One custodial wallet row per user per asset (links to legacy mn2_wallets when asset=mn2)
CREATE TABLE IF NOT EXISTS user_wallet_accounts (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id              TEXT    NOT NULL,
  asset_code           TEXT    NOT NULL REFERENCES crypto_assets(asset_code),
  wallet_kind          TEXT    NOT NULL DEFAULT 'custodial',
  legacy_mn2_wallet_id INTEGER,
  label                TEXT,
  balance_confirmed    REAL    NOT NULL DEFAULT 0,
  balance_unconfirmed  REAL    NOT NULL DEFAULT 0,
  address_count        INTEGER NOT NULL DEFAULT 0,
  staking_enabled      INTEGER NOT NULL DEFAULT 0,
  hosting_enabled      INTEGER NOT NULL DEFAULT 0,
  source               TEXT    NOT NULL DEFAULT 'migration',
  metadata_json        TEXT,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (user_id, asset_code)
);
CREATE INDEX IF NOT EXISTS ix_uwa_user ON user_wallet_accounts(user_id);
CREATE INDEX IF NOT EXISTS ix_uwa_asset ON user_wallet_accounts(asset_code);

-- Financial / KYC-adjacent profile (display + compliance fields; no secrets)
CREATE TABLE IF NOT EXISTS user_financial_profiles (
  user_id              TEXT    PRIMARY KEY,
  display_name         TEXT,
  email                TEXT,
  country_code         TEXT,
  preferred_fiat       TEXT    NOT NULL DEFAULT 'USD',
  kyc_status           TEXT    NOT NULL DEFAULT 'none',
  kyc_level            INTEGER NOT NULL DEFAULT 0,
  tax_id_token         TEXT,
  billing_name         TEXT,
  billing_line1        TEXT,
  billing_city         TEXT,
  billing_postal       TEXT,
  billing_country      TEXT,
  notes                TEXT,
  metadata_json        TEXT,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Provider token vault (Stripe/PayPal/Braintree refs — never PAN/CVV)
CREATE TABLE IF NOT EXISTS payment_instruments (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id              TEXT    NOT NULL,
  provider             TEXT    NOT NULL,
  instrument_type      TEXT    NOT NULL DEFAULT 'card',
  token_ref            TEXT    NOT NULL,
  fingerprint          TEXT,
  brand                TEXT,
  last4                TEXT,
  exp_month            INTEGER,
  exp_year             INTEGER,
  billing_name         TEXT,
  billing_country      TEXT,
  is_default           INTEGER NOT NULL DEFAULT 0,
  status               TEXT    NOT NULL DEFAULT 'active',
  metadata_json        TEXT,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (provider, token_ref)
);
CREATE INDEX IF NOT EXISTS ix_payinst_user ON payment_instruments(user_id, status);

-- NFT catalog SKUs (from data/nft_catalog.json)
CREATE TABLE IF NOT EXISTS nft_catalog_skus (
  sku                  TEXT    PRIMARY KEY,
  name                 TEXT    NOT NULL,
  series               TEXT,
  rarity               TEXT,
  supply               INTEGER NOT NULL DEFAULT 0,
  price_usd            REAL    NOT NULL DEFAULT 0,
  price_coins          INTEGER NOT NULL DEFAULT 0,
  trophy_id            TEXT,
  emblem_icon          TEXT,
  avatar_url           TEXT,
  description          TEXT,
  performer_slug       TEXT,
  metadata_json        TEXT,
  is_active            INTEGER NOT NULL DEFAULT 1,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Minted edition serials (from nft_exchange_state.editions)
CREATE TABLE IF NOT EXISTS nft_editions (
  edition_id           TEXT    PRIMARY KEY,
  sku                  TEXT    NOT NULL REFERENCES nft_catalog_skus(sku),
  serial               INTEGER NOT NULL,
  owner_user_id        TEXT    NOT NULL,
  status               TEXT    NOT NULL DEFAULT 'held',
  mint_source          TEXT,
  minted_at            TEXT,
  purchase_ref         TEXT,
  metadata_json        TEXT,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (sku, serial)
);
CREATE INDEX IF NOT EXISTS ix_nft_editions_owner ON nft_editions(owner_user_id, sku);

CREATE TABLE IF NOT EXISTS nft_market_listings (
  listing_id           TEXT    PRIMARY KEY,
  edition_id           TEXT    NOT NULL REFERENCES nft_editions(edition_id),
  seller_user_id       TEXT    NOT NULL,
  price_coins          INTEGER NOT NULL DEFAULT 0,
  fee_coins            INTEGER NOT NULL DEFAULT 0,
  status               TEXT    NOT NULL DEFAULT 'open',
  created_at           TEXT,
  closed_at            TEXT,
  metadata_json        TEXT
);
CREATE INDEX IF NOT EXISTS ix_nft_listings_status ON nft_market_listings(status, seller_user_id);

CREATE TABLE IF NOT EXISTS nft_market_trades (
  trade_id             TEXT    PRIMARY KEY,
  listing_id           TEXT,
  edition_id           TEXT    NOT NULL,
  sku                  TEXT,
  buyer_user_id        TEXT    NOT NULL,
  seller_user_id       TEXT    NOT NULL,
  price_coins          INTEGER NOT NULL DEFAULT 0,
  fee_coins            INTEGER NOT NULL DEFAULT 0,
  traded_at            TEXT,
  metadata_json        TEXT
);
CREATE INDEX IF NOT EXISTS ix_nft_trades_buyer ON nft_market_trades(buyer_user_id);

-- Multi-coin staking positions (MN2 masternodes + future assets)
CREATE TABLE IF NOT EXISTS staking_positions (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id              TEXT    NOT NULL,
  asset_code           TEXT    NOT NULL REFERENCES crypto_assets(asset_code),
  wallet_account_id    INTEGER REFERENCES user_wallet_accounts(id),
  position_kind        TEXT    NOT NULL DEFAULT 'masternode',
  amount_staked        REAL    NOT NULL DEFAULT 0,
  rewards_accrued      REAL    NOT NULL DEFAULT 0,
  collateral_address   TEXT,
  collateral_txid      TEXT,
  host_slot_id         TEXT,
  status               TEXT    NOT NULL DEFAULT 'pending',
  started_at           TEXT,
  ended_at             TEXT,
  metadata_json        TEXT,
  created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_staking_user ON staking_positions(user_id, asset_code, status);

-- Hosting capacity by asset (500 MN2 spots + expansion for other coins)
CREATE TABLE IF NOT EXISTS hosting_capacity (
  asset_code           TEXT    NOT NULL REFERENCES crypto_assets(asset_code),
  network              TEXT    NOT NULL DEFAULT 'main',
  total_slots          INTEGER NOT NULL DEFAULT 0,
  reserved_slots       INTEGER NOT NULL DEFAULT 0,
  active_slots         INTEGER NOT NULL DEFAULT 0,
  notes                TEXT,
  updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (asset_code, network)
);

CREATE TABLE IF NOT EXISTS hosting_slot_assignments (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_code           TEXT    NOT NULL,
  network              TEXT    NOT NULL DEFAULT 'main',
  slot_index           INTEGER NOT NULL,
  user_id              TEXT,
  order_ref            TEXT,
  collateral_address   TEXT,
  status               TEXT    NOT NULL DEFAULT 'available',
  assigned_at          TEXT,
  metadata_json        TEXT,
  UNIQUE (asset_code, network, slot_index)
);
CREATE INDEX IF NOT EXISTS ix_hosting_assign_user ON hosting_slot_assignments(user_id, status);
