# MN2 database — Top-100 table catalog

Grounded in the **real** `data/*.json` inventory discovered by `PROBE.sh` on the server,
plus the existing SQLite tables. Two layers:

- **TYPED** — a dedicated `CREATE TABLE` with real columns (high-value / frequently joined).
- **RAW** — materialized by `008_ingest_data_stores.py` into `data_store_records`,
  queryable as `SELECT * FROM data_store_records WHERE store_name = '<name>'` with the
  common fields (`user_ref`, `mn2_address`, `amount`, `currency`, `status`, `created_at`)
  already promoted to indexed columns and the full record kept in `payload_json`.

Every one of these gets **rows** from the live `data/` directory — the RAW layer ingests
all of them automatically; the TYPED ones are promoted on top. Nothing here moves funds or
touches the chain.

| # | table / store_name | domain | layer | source | purpose |
|---|---|---|---|---|---|
| 1 | mn2_wallets | wallet | TYPED | ledger+harvest | one canonical custodial wallet per user |
| 2 | mn2_addresses | wallet | TYPED | all stores | every valid MN2 address, linked to wallet+user |
| 3 | mn2_address_quota | wallet | TYPED | config | per-user daily address quota |
| 4 | mn2_transactions | chain | TYPED | ledger, payments, payouts | all MN2 tx (in/out) with ref linkage |
| 5 | mn2_reconciliation_log | chain | TYPED | computed | db-vs-chain drift + on-chain linkage gaps |
| 6 | mn2_identity_aliases | identity | TYPED | all stores | alias -> canonical_user_id map |
| 7 | mn2_user_stats | identity | TYPED | computed | per-user rollup (tx, volume, nodes, points) |
| 8 | mn2_metrics | metrics | TYPED | computed | tall metrics table (global/type/day/user/source) |
| 9 | mn2_stats_runs | metrics | TYPED | computed | audit of each stats run |
| 10 | mn2_micro_tx_plan | microtx | TYPED | simulation | simulated small-send plan (never broadcast) |
| 11 | site_pages | content | TYPED | crawl | public page text/html/links |
| 12 | data_store_catalog | warehouse | TYPED | 008 | inventory of every JSON store + shape/flags |
| 13 | data_store_records | warehouse | TYPED | 008 | raw conformed rows for ALL stores |
| 14 | camgirls_performers | camgirls | TYPED | camgirls_performers.json | performer profiles + payout/paypal |
| 15 | camgirls_payout_addresses | camgirls | TYPED | camgirls_payout_addresses.json | MN2 payout addresses, linked to wallets |
| 16 | camgirls_paypal_orders | camgirls | TYPED | camgirls_paypal_orders.json | revenue tracking (NO live capture) |
| 17 | camgirls_activity | camgirls | TYPED | camgirls_activity.json | achievements + activity points |
| 18 | user_accounts | core | EXISTING | db | platform accounts |
| 19 | user_profiles | core | EXISTING | db | profiles (wallet framing tab target) |
| 20 | shop_purchases | shop | EXISTING+ALTER | db | purchases + mn2_txid/mn2_address/onchain |
| 21 | camgirls_fanclub | camgirls | RAW | camgirls_fanclub.json | fan club memberships |
| 22 | camgirls_favorites | camgirls | RAW | camgirls_favorites.json | user favorite performers |
| 23 | camgirls_age_verified | camgirls | RAW | camgirls_age_verified.json | age-verification records |
| 24 | camgirls_chat | camgirls | RAW | camgirls_chat.jsonl | chat messages (jsonl) |
| 25 | camgirls_agent_models | camgirls | RAW | camgirls_agent_models.json | agent-driven model config |
| 26 | mn2_ledger | chain | RAW+TYPED | mn2_ledger.json | 1917-entry master ledger (also -> tx) |
| 27 | mn2_order_payments | shop | RAW+TYPED | mn2_order_payments.json | 78 MN2 shop payments (-> tx, purchase link) |
| 28 | mn2_masternode_hosts | masternode | RAW+TYPED | mn2_masternode_hosts.json | 44 hosted nodes + collateral |
| 29 | mn2_masternode_orders | masternode | RAW | mn2_masternode_orders.json | 696 node slot orders |
| 30 | mn2_masternode_config | masternode | RAW | mn2_masternode_config.json | collateral/slot config |
| 31 | mn2_treasury_addresses | treasury | RAW+TYPED | mn2_treasury_addresses.json | platform treasury addresses |
| 32 | mn2_config | config | RAW | mn2_config.json | ticker/decimals/confirmations |
| 33 | mn2_p2p_listings | p2p | RAW | mn2_p2p_listings.json | 12 OTC sell listings |
| 34 | mn2_p2p_orders | p2p | RAW | mn2_p2p_orders.json | 40 OTC trades |
| 35 | mn2_p2p_payouts | p2p | RAW | mn2_p2p_payouts.json | agent payout balances |
| 36 | mn2_onramp_orders | onramp | RAW | mn2_onramp_orders.json | USD->MN2 onramp via PayPal |
| 37 | mn2_staking_terms | staking | RAW | mn2_staking_terms.json | staking products/terms |
| 38 | mn2_staking_reserve | staking | RAW | mn2_staking_reserve.json | reserve balance |
| 39 | mn2_staking_notify_prefs | staking | RAW | mn2_staking_notify_prefs.json | notification prefs |
| 40 | mn2_copy_trading | trading | RAW | mn2_copy_trading.json | copy-trading followers |
| 41 | mn2_micro_tx_state | microtx | RAW | mn2_micro_tx_state.json | per-user micro-tx run state |
| 42 | mn2_micro_tx_config | microtx | RAW | mn2_micro_tx_config.json | min/max/fee/daily limits |
| 43 | mn2_worker_sessions | infra | RAW | mn2_worker_sessions.json | worker session log |
| 44 | mn2_rpc_failover | infra | RAW | mn2_rpc_failover.json | RPC endpoint failover state |
| 45 | mn2_ping_watch | infra | RAW | mn2_ping_watch.json | node ping/health |
| 46 | mn2_explorer_probe_state | infra | RAW | mn2_explorer_probe_state.json | explorer probe results |
| 47 | mn2_agent_peer_tx_state | agent | RAW | mn2_agent_peer_tx_state.json | agent peer tx cursor/runs |
| 48 | mn2_user_addresses | wallet | RAW | mn2_user_addresses.json | wallet-service address store |
| 49 | agent_wallets | agent | RAW+harvest | agent_wallets.json | agent MN2 wallets (harvested) |
| 50 | agent_crypto_wallet_agents | agent | RAW | agent_crypto_wallet_agents.json | crypto wallet agents |
| 51 | agent_staking_agents | agent | RAW | agent_staking_agents.json | staking agents |
| 52 | agent_treasury | agent | RAW | agent_treasury.json | agent treasury |
| 53 | agent_calendar | agent | RAW | agent_calendar.json | agent schedule |
| 54 | agent_leaderboard_rewards | agent | RAW | agent_leaderboard_rewards.json | leaderboard rewards |
| 55 | agent_learning_knowledge | agent | RAW | agent_learning_knowledge.json | learned knowledge base |
| 56 | agent_marketplace_config | agent | RAW | agent_marketplace_config.json | marketplace config |
| 57 | aggregator_mn2_awards | rewards | RAW | aggregator_mn2_awards.json | aggregator MN2 awards |
| 58 | achievements | gamification | RAW | achievements.json | user achievements |
| 59 | account_sessions | core | RAW | account_sessions.json | session log |
| 60 | battle_v2_state | battle | RAW | battle_v2_state.json | battle engine state |
| 61 | battle_minimal_content | battle | RAW | battle_minimal_content.json | battle content |
| 62 | battle_social_state | battle | RAW | battle_social_state.json | battle social graph |
| 63 | exchange_mn2_pool_config | exchange | RAW | exchange_mn2_pool_config.json | pool config |
| 64 | crypto_exchange__mn2_pool_state | exchange | RAW | crypto_exchange/mn2_pool_state.json | pool state |
| 65 | crypto_exchange__mn2_pool_reserve | exchange | RAW | crypto_exchange/mn2_pool_reserve.json | pool reserve |
| 66 | crypto_exchange__wallets__exchange_agent_mn2_yield | exchange | RAW+harvest | crypto_exchange/wallets/*.json | exchange agent wallets |
| 67 | logs__unified_points__exchange_mn2_pool_reserve | points | RAW* | logs/unified_points/*.json | unified points reserve (*--include-archived) |
| 68 | logs__unified_points__exchange_agent_mn2_yield | points | RAW* | logs/unified_points/*.json | agent yield points |
| 69 | logs__unified_points__exchange_agent_mn2_pool | points | RAW* | logs/unified_points/*.json | agent pool points |
| 70 | mn2_staking_notify_state | staking | RAW | logs/mn2_staking_notify_state.json | notify run state |
| 71 | shop_items | shop | PROPOSED | db/shop | catalog items (promote if present) |
| 72 | shop_inventory | shop | PROPOSED | db/shop | stock levels |
| 73 | shop_orders | shop | PROPOSED | db/shop | order headers |
| 74 | shop_order_items | shop | PROPOSED | db/shop | order line items |
| 75 | shop_revenue_daily | shop | PROPOSED | computed | daily revenue rollup |
| 76 | mn2_price_history | market | PROPOSED | /api probe | MN2/USD price snapshots over time |
| 77 | mn2_supply | market | PROPOSED | chain | circulating/total supply |
| 78 | mn2_block_stats | chain | PROPOSED | RPC (gated) | height/difficulty/hashrate per run |
| 79 | mn2_masternode_status | masternode | PROPOSED | RPC (gated) | live node status/last-seen |
| 80 | mn2_address_balances | wallet | PROPOSED | RPC (gated) | live per-address confirmed balance |
| 81 | user_kyc | compliance | PROPOSED | db | KYC/age-verification status |
| 82 | user_points_ledger | gamification | PROPOSED | unified_points | points accrual/spend ledger |
| 83 | user_achievements | gamification | PROPOSED | achievements.json | per-user achievement unlocks |
| 84 | referrals | growth | PROPOSED | db | referral graph + rewards |
| 85 | payouts_queue | treasury | PROPOSED | computed | queued outgoing payouts (gated) |
| 86 | payout_batches | treasury | PROPOSED | computed | batch grouping of payouts |
| 87 | fees_ledger | finance | PROPOSED | computed | platform fee accrual by source |
| 88 | revenue_by_source | finance | PROPOSED | computed | shop/camgirls/onramp/p2p revenue split |
| 89 | onramp_quotes | onramp | PROPOSED | mn2_onramp_orders.json | rate quotes/spread history |
| 90 | p2p_escrow | p2p | PROPOSED | mn2_p2p_orders.json | escrow state per trade |
| 91 | staking_positions | staking | PROPOSED | mn2_staking_*.json | open positions per user |
| 92 | staking_reward_events | staking | PROPOSED | computed | reward distribution events |
| 93 | copy_trading_signals | trading | PROPOSED | mn2_copy_trading.json | leader signals |
| 94 | copy_trading_follower_trades | trading | PROPOSED | mn2_copy_trading.json | replicated trades |
| 95 | notifications | core | PROPOSED | db | user notifications |
| 96 | audit_log | core | PROPOSED | db | admin/agent action audit |
| 97 | feature_flags | core | PROPOSED | config jsons | enabled flags per sub-app |
| 98 | app_versions | core | PROPOSED | config | sub-app version registry (camgirls v12 gate) |
| 99 | rpc_health | infra | PROPOSED | mn2_rpc_failover.json | RPC latency/uptime samples |
| 100 | crawler_runs | content | PROPOSED | 003 | crawl run audit (pages/status/bytes) |

## Layer status

- **Built + dry-run now (1–70):** TYPED tables created by `schema_mn2.sql`; RAW rows
  materialized by `008`; camgirls promoted by `009`; MN2 wallet/tx/stats by `002/005/007`.
  RAW* (67–70) live under `logs/` and need `--include-archived`.
- **PROPOSED (71–100):** documented next-wave tables. Most are derived rollups
  (`computed`) or need a live source we don't yet read:
  - **RPC-gated (78–80):** require daemon read access — a separate, explicitly authorized
    phase. Never enabled by the migration.
  - **Shop tables (71–75):** need the live shop schema/source you'll paste.
  - **Money-movement tables (85–86):** tracking only; live payouts stay gated.

## Querying the RAW layer

```sql
-- all camgirls chat messages
SELECT * FROM data_store_records WHERE store_name='camgirls_chat';
-- every record carrying an MN2 address, grouped by store
SELECT store_name, COUNT(*) FROM data_store_records
 WHERE mn2_address IS NOT NULL GROUP BY store_name;
-- all USD revenue-like records
SELECT store_name, record_key, amount, currency, status
  FROM data_store_records WHERE currency='usd' ORDER BY amount DESC;
```
