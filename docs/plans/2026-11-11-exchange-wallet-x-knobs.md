---
title: Exchange wallet X-* — 12 improvement knobs walkthrough
type: feat
date: 2026-11-11
parent: docs/plans/2026-11-11-wallet-v1.6.6.0-giga-upgrade-plan.md
target: v32.6.6.0
---

# 12 improvement knobs per X-* enrichment

Source knobs (from `docs/50_AGENT_TECHS_COMPLETE.md`):

1. `optimize_performance`
2. `enhance_security`
3. `improve_reliability`
4. `scale_capacity`
5. `reduce_latency`
6. `increase_throughput`
7. `add_monitoring`
8. `enable_auto_recovery`
9. `improve_caching`
10. `enhance_logging`
11. `add_analytics`
12. `upgrade_algorithm`

**Exchange meaning (all X-*):**

| Knob | What “install” means on the exchange wallet |
| ---- | ------------------------------------------- |
| optimize_performance | Cut CPU/IO on this enrichment’s hot path |
| enhance_security | Tighter ACL / signing / withdraw-trade policy |
| improve_reliability | Retries, idempotency, safe degradation |
| scale_capacity | More concurrency / venues / sockets safely |
| reduce_latency | Lower book/fill/RPC/UI lag |
| increase_throughput | Batch + parallelize settles/reads |
| add_monitoring | Health tiles, metrics, alerts |
| enable_auto_recovery | Reconnect / rewind / resume after faults |
| improve_caching | TTL + stale-safe caches |
| enhance_logging | Structured trade/settle/withdraw audit |
| add_analytics | PnL / fee / slippage / funnel analytics |
| upgrade_algorithm | Smarter fee / route / size / anomaly model |

**Mega ship rule:** every shipped X-* installs at least these four at level ≥1: `enhance_security`, `add_monitoring`, `enable_auto_recovery`, `add_analytics`.

Machine catalog: `backend/services/exchange_wallet_x_knobs.py` (50 × 12 = 600 install texts).

---

## Priority install set (confirmed)

| Pillar | Enrichments |
| ------ | ----------- |
| Custody | X-03 PoR ledger, X-04 vault sync, X-27 integrity, X-38 withdraw fence |
| Trading desk | X-02 estimator, X-05 book cache, X-08 failover, X-39 route, X-40 guided flow |
| Risk | X-22 behavior, X-41 predictor, X-46 anomaly, X-48 decision strip |
| Ops | X-09 mesh, X-31 health, X-34 alerts, X-35 metrics, X-43 self healer |

APIs: `GET /api/exchange/wallet-mega/priority`, `GET|POST /api/exchange/wallet-mega/priority/run`, `GET|POST /api/exchange/wallet-mega/priority/<id>`.

### X-03 — Trading ledger + PoR glance (custody)

| # | Knob | Install |
| - | ---- | ------- |
| 1 | optimize_performance | Index PoR + PPP ledger joins; avoid full-file scans on every glance |
| 2 | enhance_security | Redact balances in exports; admin-only raw PoR; no venue secrets in glance |
| 3 | improve_reliability | If PoR RPC fails, return last good snapshot + error flag |
| 4 | scale_capacity | Paginate ledger export; ≥10k rows without blocking workers |
| 5 | reduce_latency | Cache PoR snapshot ≤60s; venue filter in-memory after first read |
| 6 | increase_throughput | Batch multi-venue PoR glances in one request |
| 7 | add_monitoring | Emit glance lag + ledger_count; amber when PoR stale |
| 8 | enable_auto_recovery | Skip corrupt JSONL lines; rewind reader offset |
| 9 | improve_caching | TTL cache for por_glance keyed by venue+limit |
| 10 | enhance_logging | Audit who exported PoR/ledger and which venue filter |
| 11 | add_analytics | Coverage ratio, liability delta, per-venue fill/fail counts |
| 12 | upgrade_algorithm | Weighted PoR coverage including pending settles + hot-float |

### X-08 — Multi-venue + multi-RPC failover (desk)

| # | Knob | Install |
| - | ---- | ------- |
| 1 | optimize_performance | Parallel venue probes; short RPC failover probe budget |
| 2 | enhance_security | Never auto-broadcast on failover; vault credentials; ACL on promote |
| 3 | improve_reliability | Idempotent promote/failback; sticky active RPC until standby healthy |
| 4 | scale_capacity | Track N venues + primary/standby RPC without serial bottlenecks |
| 5 | reduce_latency | Fail-fast unhealthy venue; prefer lowest RTT ready venue for reads |
| 6 | increase_throughput | Concurrent readiness probes; reuse HTTP sessions |
| 7 | add_monitoring | Badge active RPC + preferred/standby venue on wallets/exchange |
| 8 | enable_auto_recovery | Auto failback to primary when healthy; resubscribe feeds after promote |
| 9 | improve_caching | Cache readiness ≤15s; RPC status_summary ≤5s |
| 10 | enhance_logging | Log promote_reason, venue switch, SPORK_112 gate |
| 11 | add_analytics | Failover count, time-on-standby, venue probe fail rates |
| 12 | upgrade_algorithm | Score venues by creds + latency + live_ready + recent errors |

### X-40 — Guided deposit → trade → withdraw (desk)

| # | Knob | Install |
| - | ---- | ------- |
| 1 | optimize_performance | Prefetch deposit address + quote in parallel on guided start |
| 2 | enhance_security | Step-up on withdraw; always run X-46 assess; no live venue unless SPORK_112 |
| 3 | improve_reliability | Resume token per step; retry trade without double-spend |
| 4 | scale_capacity | Many concurrent guided sessions per user without clobbering state |
| 5 | reduce_latency | Deep-link deposit→trade→withdraw; skip redundant refreshes |
| 6 | increase_throughput | Batch status bundle (PoR+failover+gates) in one status call |
| 7 | add_monitoring | Funnel metrics: deposit_ok / trade_ok / withdraw_assessed / withdraw_sent |
| 8 | enable_auto_recovery | If trade fails (no balance), keep deposit address and retry later |
| 9 | improve_caching | Cache deposit address per user; cache quote ≤2 minutes with quote_id |
| 10 | enhance_logging | Structured step log: user, step, mode=on_chain_custody, ids |
| 11 | add_analytics | Conversion + time-per-step for the guided funnel |
| 12 | upgrade_algorithm | Recommend next step from balances, PoR, and anomaly score |

### X-46 — Anomaly detector before broadcast (risk)

| # | Knob | Install |
| - | ---- | ------- |
| 1 | optimize_performance | In-process risk assess; avoid extra RPC unless float-gate needs it |
| 2 | enhance_security | Hard-block high score; require step-up; bind assess to broadcast gate |
| 3 | improve_reliability | Fail closed on assessor error for live broadcast |
| 4 | scale_capacity | Score burst withdrawals without lock contention on risk log |
| 5 | reduce_latency | Sync assess before send; no post-broadcast scoring |
| 6 | increase_throughput | Batch assess for multi-out drafts; single log append |
| 7 | add_monitoring | Count blocks / step-ups / allows; alert on block spikes |
| 8 | enable_auto_recovery | After block, offer safe resume (lower amount / known address) |
| 9 | improve_caching | Cache recent payout addresses per user for new-address detection |
| 10 | enhance_logging | Immutable risk log with score, reasons, kind=trade\|withdraw |
| 11 | add_analytics | False-positive rate, block reasons histogram, trade vs withdraw mix |
| 12 | upgrade_algorithm | Tune thresholds with velocity + % balance + new address + float coverage |

---

## Remaining X-01…X-50

Every other enrichment gets the same 12 knobs with generated install text in `exchange_wallet_x_knobs.py` (`walkthrough()`). Pillars:

- **custody:** X-01, X-03, X-04, X-27, X-28, X-45
- **desk:** X-02, X-05, X-07, X-08, X-12, X-17, X-18, X-21, X-24, X-36, X-39, X-40, X-44, X-48, X-49, X-50
- **risk:** X-14, X-22, X-26, X-29, X-38, X-41, X-46
- **ops:** X-06, X-09, X-10, X-11, X-13, X-15, X-16, X-19, X-20, X-23, X-25, X-30–X-35, X-37, X-42, X-43, X-47

API (once routes are wired): `GET /api/exchange/wallet-mega/knobs` and `GET /api/exchange/wallet-mega/knobs/<id>`.
