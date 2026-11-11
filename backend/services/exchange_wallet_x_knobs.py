"""Exchange-wallet X-* enrichment catalog — 50 enrichments × 12 improvement knobs.

Machine-readable walkthrough used by the v32.6.6.0 mega plan and
``exchange_wallet_mega_prototype_service``.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

ALL_KNOBS: Tuple[str, ...] = (
    "optimize_performance",
    "enhance_security",
    "improve_reliability",
    "scale_capacity",
    "reduce_latency",
    "increase_throughput",
    "add_monitoring",
    "enable_auto_recovery",
    "improve_caching",
    "enhance_logging",
    "add_analytics",
    "upgrade_algorithm",
)

# Mega ship installs these four at level ≥1 on every shipped X-*.
MEGA_MIN_KNOBS: Tuple[str, ...] = (
    "enhance_security",
    "add_monitoring",
    "enable_auto_recovery",
    "add_analytics",
)

KNOB_META: Dict[str, Dict[str, str]] = {
    "optimize_performance": {
        "label": "Optimize performance",
        "exchange_meaning": "Cut CPU/IO on the hot path for this enrichment (quotes, signs, probes, settles).",
    },
    "enhance_security": {
        "label": "Enhance security",
        "exchange_meaning": "Tighten ACL, signing, secret handling, and withdraw/trade policy for this enrichment.",
    },
    "improve_reliability": {
        "label": "Improve reliability",
        "exchange_meaning": "Add retries, idempotency keys, and dual-write/safe-fail behavior.",
    },
    "scale_capacity": {
        "label": "Scale capacity",
        "exchange_meaning": "Raise concurrency / open-order / venue / socket limits without breaking correctness.",
    },
    "reduce_latency": {
        "label": "Reduce latency",
        "exchange_meaning": "Lower end-to-end lag (bookTicker, fill notify, RPC round-trip, UI step).",
    },
    "increase_throughput": {
        "label": "Increase throughput",
        "exchange_meaning": "Batch and parallelize reads/settles so more actions complete per second.",
    },
    "add_monitoring": {
        "label": "Add monitoring",
        "exchange_meaning": "Expose health/metrics/alerts tiles for this enrichment.",
    },
    "enable_auto_recovery": {
        "label": "Enable auto-recovery",
        "exchange_meaning": "Reconnect, resubscribe, rewind, or resume after faults without operator babysitting.",
    },
    "improve_caching": {
        "label": "Improve caching",
        "exchange_meaning": "Add TTL/stale-safe caches for books, balances, PoR, or readiness probes.",
    },
    "enhance_logging": {
        "label": "Enhance logging",
        "exchange_meaning": "Structured audit logs for trades, settles, withdraws, and gate decisions.",
    },
    "add_analytics": {
        "label": "Add analytics",
        "exchange_meaning": "PnL, fee, slippage, failover, or funnel analytics for this enrichment.",
    },
    "upgrade_algorithm": {
        "label": "Upgrade algorithm",
        "exchange_meaning": "Replace heuristics with a smarter fee/route/size/anomaly/scoring model.",
    },
}

# (id, tech, title, pillar, surfaces)
_X_ROWS: Tuple[Tuple[str, str, str, str, Tuple[str, ...]], ...] = (
    ("X-01", "Quantum Processor", "Parallel signature + batch withdraw approve", "custody", ("daemon",)),
    ("X-02", "Neural Network", "Quote / slippage / fill-probability estimator", "desk", ("web", "qt")),
    ("X-03", "Blockchain Ledger", "Trading ledger + PoR export per venue", "custody", ("web", "ops")),
    ("X-04", "Cloud Sync", "Encrypted exchange-settings + API-key vault sync", "custody", ("qt", "web")),
    ("X-05", "Distributed Cache", "Orderbook + balance cache with stale guards", "desk", ("web", "ops")),
    ("X-06", "Microservices", "Split trade-engine / settlement / notify workers", "ops", ("web", "ops")),
    ("X-07", "API Gateway", "Exchange controller gateway with agent trade tokens", "desk", ("web",)),
    ("X-08", "Load Balancer", "Multi-venue + multi-RPC failover for trading", "desk", ("web", "ops")),
    ("X-09", "Service Mesh", "Wallet ↔ exchange ↔ casino-bridge health mesh", "ops", ("ops",)),
    ("X-10", "Container Orchestrator", "Exchange-wallet compose profile", "ops", ("ops",)),
    ("X-11", "Code Analyzer", "Pre-release gate on exchange+wallet patches", "ops", ("ops",)),
    ("X-12", "Performance Profiler", "Order latency / settle profiler in control center", "desk", ("web",)),
    ("X-13", "Memory Debugger", "Feed + uwsgi memory watch for exchange processes", "ops", ("ops",)),
    ("X-14", "Security Scanner", "API-key / withdraw ACL / webhook secret scanner", "risk", ("ops",)),
    ("X-15", "Dependency Checker", "Venue SDK + wallet lib manifest in release", "ops", ("ops",)),
    ("X-16", "Test Generator", "Paper-trade + settle + on-chain dry-run regression pack", "ops", ("ops",)),
    ("X-17", "Log Analyzer", "Fill / reject / withdraw structured log viewer", "desk", ("web",)),
    ("X-18", "Error Tracker", "Exchange error codes on wallet + exchange APIs", "desk", ("web",)),
    ("X-19", "Code Formatter", "CI format gate for exchange controller + wallet UI", "ops", ("ops",)),
    ("X-20", "Documentation Generator", "Auto exchange-wallet setup + rail docs from manifest", "ops", ("ops", "web")),
    ("X-21", "Activity Tracker", "Per-user trade / deposit / withdraw activity feed", "desk", ("web", "qt")),
    ("X-22", "Behavior Tracker", "Unusual trading / withdraw pattern hints", "risk", ("web",)),
    ("X-23", "Metric Tracker", "Volume, fees, open interest, MN2 float KPIs", "ops", ("web",)),
    ("X-24", "Event Tracker", "Fill / cancel / deposit event bus → wallet UI", "desk", ("web", "daemon")),
    ("X-25", "Network Scanner", "Venue endpoint / peer quality for trading rails", "ops", ("ops",)),
    ("X-26", "Vulnerability Scanner", "CVE + key-leak sweep before live gate", "risk", ("ops",)),
    ("X-27", "File Scanner", "Hot-wallet / cold-wallet file integrity checks", "custody", ("daemon", "ops")),
    ("X-28", "Database Scanner", "Ledger vs chain vs venue balance consistency", "custody", ("web", "ops")),
    ("X-29", "Endpoint Scanner", "Exchange RPC / webhook / controller ACL audit", "risk", ("ops",)),
    ("X-30", "Config Scanner", "Exchange + wallet conf lint (spork-aware)", "ops", ("ops", "web")),
    ("X-31", "Health Monitor", "Green/amber/red for daemon + venue + payout rails", "ops", ("web", "qt")),
    ("X-32", "Resource Monitor", "CPU/RAM/disk for feed + daemon beside wallet", "ops", ("web", "ops")),
    ("X-33", "Uptime Monitor", "Exchange SLA + wallet uptime tiles", "ops", ("web",)),
    ("X-34", "Alert Monitor", "Discord/email on stuck settle, unlock, or sync stall", "ops", ("ops", "web")),
    ("X-35", "Metric Monitor", "Prometheus exporter for trades, rejects, withdraws", "ops", ("ops",)),
    ("X-36", "GPS Coordinator", "Region-aware venue preference (optional)", "desk", ("web",)),
    ("X-37", "Location Tracker", "Masternode / venue status map for operators", "ops", ("web",)),
    ("X-38", "Geofence Manager", "Withdraw allow-list + geo/policy fence", "risk", ("daemon", "web")),
    ("X-39", "Route Optimizer", "Best venue / fee / settle route picker", "desk", ("web",)),
    ("X-40", "Navigation System", "Guided deposit → trade → withdraw flow", "desk", ("qt", "web")),
    ("X-41", "ML Predictor", "Confirm-time, fee, and adverse-selection hint", "risk", ("web", "qt")),
    ("X-42", "Auto Scaler", "Auto throttle orders under venue / disk pressure", "ops", ("web", "ops")),
    ("X-43", "Self Healer", "Auto resubscribe feeds + rewind incomplete settles", "ops", ("web", "ops")),
    ("X-44", "Adaptive Learner", "Per-session fee / size / venue policy", "desk", ("web",)),
    ("X-45", "Pattern Matcher", "Label exchange / platform / bridge addresses", "custody", ("qt", "web")),
    ("X-46", "Anomaly Detector", "Block anomalous trade or withdraw before broadcast", "risk", ("qt", "daemon", "web")),
    ("X-47", "Optimization Engine", "IBD + book warm + startup profile for traders", "ops", ("daemon", "web")),
    ("X-48", "Decision Maker", "Recommended next action strip", "desk", ("qt", "web")),
    ("X-49", "Workflow Orchestrator", "One-click unlock → fund → trade → backup", "desk", ("qt", "web")),
    ("X-50", "Event-Driven Processor", "Unified trade+wallet event bus", "desk", ("daemon", "web")),
)

# Product-confirmed priority install set (custody / desk / risk / ops).
PRIORITY_BY_PILLAR: Dict[str, Tuple[str, ...]] = {
    "custody": ("X-03", "X-04", "X-27", "X-38"),
    "desk": ("X-02", "X-05", "X-08", "X-39", "X-40"),
    "risk": ("X-22", "X-41", "X-46", "X-48"),
    "ops": ("X-09", "X-31", "X-34", "X-35", "X-43"),
}

PRIORITY_IDS: Tuple[str, ...] = tuple(
    eid for pillar in ("custody", "desk", "risk", "ops") for eid in PRIORITY_BY_PILLAR[pillar]
)

# Train F core rail (T5.01–T5.10): X-01…X-10.
TRAIN_F_CORE_IDS: Tuple[str, ...] = tuple(f"X-{i:02d}" for i in range(1, 11))

# Train F desk quality (T5.11–T5.20): X-11…X-20 tools & debuggers.
TRAIN_F_DESK_IDS: Tuple[str, ...] = tuple(f"X-{i:02d}" for i in range(11, 21))

# Train F market + risk sensing (T5.21–T5.30): X-21…X-30 trackers & scanners.
TRAIN_F_SENSE_IDS: Tuple[str, ...] = tuple(f"X-{i:02d}" for i in range(21, 31))


def _pa(**kwargs: str) -> Dict[str, str]:
    """Fill all 12 knobs; missing keys get a short default from kwargs."""
    out = {k: "" for k in ALL_KNOBS}
    out.update(kwargs)
    for k, v in list(out.items()):
        if not v:
            out[k] = f"Install {k} for this priority enrichment."
    return out


# Explicit 12-knob walkthroughs for the priority install set.
_PRIORITY_ACTIONS: Dict[str, Dict[str, str]] = {
    "X-02": _pa(
        optimize_performance="Score quotes in-process from cached books; no cold venue hits on estimator.",
        enhance_security="Never leak venue keys; estimator is advisory only until SPORK_112.",
        improve_reliability="If book missing, return flat estimate + low confidence (no crash).",
        reduce_latency="Serve estimate from ≤5s book/price cache.",
        add_monitoring="Expose confidence_pct + expected_move_bps on desk strip.",
        enable_auto_recovery="Fall back to internal mid when external cache empty.",
        improve_caching="Reuse external price cache + wallet mid.",
        enhance_logging="Log symbol, direction, confidence, venue_count.",
        add_analytics="Track estimate vs realized fill slippage.",
        upgrade_algorithm="Blend gap + dispersion into fill-probability hint.",
    ),
    "X-03": _pa(
        optimize_performance="Index PoR + PPP ledger joins; avoid full-file scans on every glance.",
        enhance_security="Redact balances in exports; gate raw rows behind SPORK_119.",
        improve_reliability="If PoR RPC fails, return last good snapshot + error flag.",
        scale_capacity="Paginate ledger export; support ≥10k rows without blocking workers.",
        reduce_latency="Cache PoR snapshot ≤60s; venue filter in-memory after first read.",
        increase_throughput="Batch multi-venue PoR glances in one request.",
        add_monitoring="Emit glance lag + ledger_count; amber when PoR stale.",
        enable_auto_recovery="On corrupt JSONL line, skip + continue; rewind reader offset.",
        improve_caching="TTL cache for por_glance keyed by venue+limit.",
        enhance_logging="Audit who exported PoR/ledger and which venue filter was used.",
        add_analytics="Coverage ratio, liability delta, per-venue fill/fail counts.",
        upgrade_algorithm="Weighted PoR coverage including pending settles + hot-float.",
    ),
    "X-04": _pa(
        optimize_performance="Lazy-load vault index; decrypt only requested labels.",
        enhance_security="Encrypted vault at rest; never return raw secrets in status APIs.",
        improve_reliability="Vault missing → empty status success with encryption_available flag.",
        add_monitoring="Secret + wallet counts on custody tile.",
        enable_auto_recovery="Recreate vault file structure if corrupted header detected.",
        improve_caching="Cache vault_status ≤10s.",
        enhance_logging="Audit vault open / label list (no secret values).",
        add_analytics="Secret_count / wallet_count trend for ops.",
        upgrade_algorithm="Prefer hardware-backed key when available; else file vault.",
    ),
    "X-05": _pa(
        optimize_performance="Serve book/balance from TTL cache on desk reads.",
        enhance_security="Do not cache secrets; redact balances in shared caches.",
        improve_reliability="Stale-while-revalidate: serve stale + flag when refresh fails.",
        reduce_latency="Target ≤100ms cached book path.",
        improve_caching="TTL + stale guards on orderbook and balance snapshots.",
        add_monitoring="Cache hit/miss + age on desk health.",
        enable_auto_recovery="Invalidate and refetch on checksum mismatch.",
        enhance_logging="Log cache key, age, hit/miss.",
        add_analytics="Hit rate and stale-serve counts.",
        upgrade_algorithm="Adaptive TTL by symbol volatility.",
    ),
    "X-08": _pa(
        optimize_performance="Parallel venue probes; short RPC failover probe budget.",
        enhance_security="Never auto-broadcast on failover; credentials stay in vault; ACL on promote.",
        improve_reliability="Idempotent promote/failback; sticky active RPC until standby healthy.",
        scale_capacity="Track N venues + primary/standby RPC without serial bottlenecks.",
        reduce_latency="Fail-fast unhealthy venue; prefer lowest RTT ready venue.",
        increase_throughput="Concurrent readiness probes; reuse HTTP sessions.",
        add_monitoring="Badge active RPC + preferred/standby venue.",
        enable_auto_recovery="Auto failback when primary healthy; gated by SPORK_117.",
        improve_caching="Cache readiness ≤15s; RPC status_summary ≤5s.",
        enhance_logging="Log promote_reason, venue switch, SPORK_112 gate.",
        add_analytics="Failover count, time-on-standby, probe fail rates.",
        upgrade_algorithm="Score venues by creds + latency + live_ready + errors.",
    ),
    "X-09": _pa(
        optimize_performance="Single mesh snapshot fan-in for wallet/exchange/bridge.",
        enhance_security="Mesh status is read-only; no money paths.",
        improve_reliability="Partial mesh OK: show red only for failed nodes.",
        add_monitoring="Green/amber/red edges on wallet↔exchange↔casino.",
        enable_auto_recovery="Suggest healer (X-43) when mesh edge red.",
        enhance_logging="Log mesh edge failures with component ids.",
        add_analytics="Edge uptime ratios.",
        upgrade_algorithm="Weight edges by recent error rate + SPORK_101 services enforcement.",
    ),
    "X-22": _pa(
        optimize_performance="Reuse withdrawal risk assess features for behavior hints.",
        enhance_security="Hints never bypass SPORK_118 hard block.",
        improve_reliability="Unknown user → low-risk empty pattern set.",
        add_monitoring="Count unusual pattern hits per day.",
        enable_auto_recovery="Offer lower amount / known address resume.",
        enhance_logging="Log pattern ids without raw secrets.",
        add_analytics="Pattern histogram for withdraw vs trade.",
        upgrade_algorithm="Velocity + new-address + % balance composite.",
    ),
    "X-27": _pa(
        optimize_performance="Hash only critical custody files (vault, security, addresses).",
        enhance_security="Integrity miss blocks live withdraw until ops ACK.",
        improve_reliability="Missing optional file → amber, not hard fail.",
        add_monitoring="Integrity tile: ok/amber/red + file list.",
        enable_auto_recovery="Re-run scan after vault rewrite.",
        enhance_logging="Log path + sha16 + size (no contents).",
        add_analytics="Integrity fail rate over time.",
        upgrade_algorithm="Merkle over custody file set for quick compare.",
    ),
    "X-31": _pa(
        optimize_performance="Reuse daemon probe + exchange health in one call.",
        enhance_security="Health APIs never expose keys.",
        improve_reliability="Probe never raises; always returns structured status.",
        add_monitoring="Green/amber/red for daemon + venue + payout rails.",
        enable_auto_recovery="Link to X-43 when daemon unhealthy.",
        enhance_logging="Append health probe JSONL.",
        add_analytics="Time-to-recover after red.",
        upgrade_algorithm="Composite score: RPC + exchange + failover preferred.",
    ),
    "X-34": _pa(
        optimize_performance="Derive alerts from existing health/failover without extra probes.",
        enhance_security="Alert payloads redact balances and secrets.",
        improve_reliability="Alert builder never fails the request; empty list on error.",
        add_monitoring="Stuck settle / unlock / sync stall / spork maintenance alerts.",
        enable_auto_recovery="Alerts include suggested X-43 action.",
        enhance_logging="Log alert_id + severity.",
        add_analytics="Alert volume by severity.",
        upgrade_algorithm="Dedupe alerts within TTL window.",
    ),
    "X-35": _pa(
        optimize_performance="Export counters from in-memory + small JSON snapshots.",
        enhance_security="Metrics omit PII and secrets.",
        improve_reliability="Missing explorer metrics → exchange-only subset.",
        add_monitoring="Prometheus-style snapshot for trades/rejects/withdraws/gates.",
        enhance_logging="Log scrape age.",
        add_analytics="Gate deny counts by spork reason.",
        upgrade_algorithm="Label metrics by enrichment id + pillar.",
    ),
    "X-38": _pa(
        optimize_performance="Whitelist check is O(n) small list in-process.",
        enhance_security="SPORK_121 forces whitelist; TOTP remains independent.",
        improve_reliability="Empty whitelist + required → hard block with clear code.",
        add_monitoring="Whitelist required/enforced + count on custody tile.",
        enable_auto_recovery="Guide user to add address before retry.",
        enhance_logging="Audit whitelist add/remove + gate denials.",
        add_analytics="Deny rate for whitelist fence.",
        upgrade_algorithm="Optional geo/policy tags on allow-list entries.",
    ),
    "X-39": _pa(
        optimize_performance="Rank venues from cached readiness; no live order.",
        enhance_security="Route picker never enables live legs without SPORK_112.",
        improve_reliability="If no venues, return empty route with reason.",
        reduce_latency="Prefer lowest RTT ready venue for reads.",
        add_monitoring="Show preferred + alternatives on desk.",
        enable_auto_recovery="Re-rank after failover promote.",
        improve_caching="Reuse failover ranking ≤15s.",
        enhance_logging="Log chosen venue_id + score inputs.",
        add_analytics="Route win rate vs fee/slippage.",
        upgrade_algorithm="Score = ready + creds + latency + recent errors.",
    ),
    "X-40": _pa(
        optimize_performance="Prefetch deposit address + quote in parallel on guided start.",
        enhance_security="Step-up on withdraw; always run X-46; gates 116/120.",
        improve_reliability="Each step returns resume token; retry trade without double-spend.",
        scale_capacity="Many concurrent guided sessions per user without clobbering state.",
        reduce_latency="Deep-link deposit→trade→withdraw; skip redundant refreshes.",
        increase_throughput="Batch status bundle (por+failover+gates) in one status call.",
        add_monitoring="Funnel metrics: deposit_ok / trade_ok / withdraw_assessed / withdraw_sent.",
        enable_auto_recovery="If trade fails (no balance), keep deposit address and retry later.",
        improve_caching="Cache deposit address per user; cache quote ≤2 minutes with quote_id.",
        enhance_logging="Structured step log: user, step, mode=on_chain_custody, ids.",
        add_analytics="Conversion + time-per-step for the guided funnel.",
        upgrade_algorithm="Recommend next step from balances, PoR, and anomaly score.",
    ),
    "X-41": _pa(
        optimize_performance="Predict from cached prices only (no network in tick).",
        enhance_security="Disclaimer required; never auto-trade from predictor.",
        improve_reliability="No mids → flat + low confidence.",
        add_monitoring="confidence_pct + edge_uplift on risk strip.",
        enable_auto_recovery="Fall back to flat when cache empty.",
        improve_caching="Read last external price cache.",
        enhance_logging="Log symbol, direction, confidence.",
        add_analytics="Prediction vs next mid move calibration.",
        upgrade_algorithm="Blend gap, dispersion, coverage into edge_uplift_bps.",
    ),
    "X-43": _pa(
        optimize_performance="Healer only runs cheap local checks first.",
        enhance_security="Promote gated by SPORK_117; never broadcast money.",
        improve_reliability="Idempotent heal plan; dry-run by default.",
        add_monitoring="List heal actions + whether auto_promote allowed.",
        enable_auto_recovery="Resubscribe/rewind suggestions when settles stuck.",
        enhance_logging="Log heal plan steps and gate results.",
        add_analytics="Heal success vs manual ops intervenes.",
        upgrade_algorithm="Order heal steps by blast radius (RPC → feed → settle).",
    ),
    "X-46": _pa(
        optimize_performance="Risk assess in-process; avoid extra RPC unless float-gate needs it.",
        enhance_security="Hard-block high score when SPORK_118 on; bind to broadcast.",
        improve_reliability="Fail closed on assessor error for live broadcast.",
        scale_capacity="Score burst withdrawals without lock contention on risk log.",
        reduce_latency="Sync assess before send; no post-broadcast scoring.",
        increase_throughput="Batch assess for multi-out drafts; single log append.",
        add_monitoring="Count blocks / step-ups / allows; alert on block spikes.",
        enable_auto_recovery="After block, offer safe resume (lower amount / known address).",
        improve_caching="Cache recent payout addresses per user for new-address detection.",
        enhance_logging="Immutable risk log with score, reasons, kind=trade|withdraw.",
        add_analytics="False-positive rate, block reasons histogram.",
        upgrade_algorithm="Tune thresholds with velocity + % balance + new address + float.",
    ),
    "X-48": _pa(
        optimize_performance="Decision strip from already-fetched wallet + gates + risk.",
        enhance_security="Never recommend live venue trade while SPORK_112 off.",
        improve_reliability="Always return ≥1 safe next action (deposit/status).",
        add_monitoring="Show top recommendation + reasons on desk/risk strip.",
        enable_auto_recovery="If withdraw blocked, recommend whitelist or lower amount.",
        enhance_logging="Log chosen action id + inputs summary.",
        add_analytics="Action accept rate.",
        upgrade_algorithm="Rank deposit / trade / withdraw / wait by balances + gates + anomaly.",
    ),
}


def _default_action(enrichment_id: str, title: str, knob: str) -> str:
    """Generic but concrete install text when no priority override exists."""
    subject = title
    templates = {
        "optimize_performance": f"Speed up {subject}: profile hot path and remove sync waits.",
        "enhance_security": f"Lock down {subject}: ACL, secrets, and policy checks before money moves.",
        "improve_reliability": f"Harden {subject}: retries, idempotency, and safe degradation.",
        "scale_capacity": f"Raise limits for {subject}: more concurrency without correctness loss.",
        "reduce_latency": f"Cut lag in {subject}: tighter timeouts and faster notify path.",
        "increase_throughput": f"Batch/parallelize {subject} so more actions complete per second.",
        "add_monitoring": f"Watch {subject}: health tile, metrics, and alert hooks.",
        "enable_auto_recovery": f"Self-heal {subject}: reconnect/resume after faults.",
        "improve_caching": f"Cache {subject} reads with TTL and stale guards.",
        "enhance_logging": f"Audit {subject} with structured logs (ids, gates, outcomes).",
        "add_analytics": f"Measure {subject}: KPIs, funnels, and error/fee analytics.",
        "upgrade_algorithm": f"Upgrade {subject} scoring/routing/sizing heuristics to v2 model.",
    }
    return templates.get(knob, f"Improve {enrichment_id} via {knob}.")


def enrichment_meta(enrichment_id: str) -> Optional[Dict[str, Any]]:
    eid = str(enrichment_id or "").strip().upper()
    for row in _X_ROWS:
        if row[0] == eid:
            return {
                "id": row[0],
                "tech": row[1],
                "title": row[2],
                "pillar": row[3],
                "surfaces": list(row[4]),
                "priority": eid in PRIORITY_IDS,
                "priority_pillar": next(
                    (pillar for pillar, ids in PRIORITY_BY_PILLAR.items() if eid in ids),
                    None,
                ),
            }
    return None


def list_enrichments() -> List[Dict[str, Any]]:
    return [enrichment_meta(row[0]) for row in _X_ROWS]  # type: ignore[misc]


def priority_manifest() -> Dict[str, Any]:
    return {
        "success": True,
        "count": len(PRIORITY_IDS),
        "ids": list(PRIORITY_IDS),
        "by_pillar": {k: list(v) for k, v in PRIORITY_BY_PILLAR.items()},
        "mega_min_knobs": list(MEGA_MIN_KNOBS),
    }


def knobs_for(enrichment_id: str, *, installed_min_only: bool = False) -> Dict[str, Any]:
    meta = enrichment_meta(enrichment_id)
    if not meta:
        return {"success": False, "error": "unknown_enrichment", "id": enrichment_id}
    eid = meta["id"]
    overrides = _PRIORITY_ACTIONS.get(eid) or {}
    items: List[Dict[str, Any]] = []
    for i, knob in enumerate(ALL_KNOBS, start=1):
        level = 1 if knob in MEGA_MIN_KNOBS else 0
        if installed_min_only and level < 1:
            continue
        km = KNOB_META[knob]
        items.append(
            {
                "n": i,
                "knob": knob,
                "label": km["label"],
                "exchange_meaning": km["exchange_meaning"],
                "install": overrides.get(knob) or _default_action(eid, meta["title"], knob),
                "level": level,
                "mega_min": knob in MEGA_MIN_KNOBS,
            }
        )
    return {
        "success": True,
        "enrichment": meta,
        "knob_count": len(items),
        "mega_min_knobs": list(MEGA_MIN_KNOBS),
        "knobs": items,
    }


def walkthrough(*, enrichment_id: Optional[str] = None, installed_min_only: bool = False) -> Dict[str, Any]:
    """Full or single-enrichment walkthrough of the 12 knobs."""
    if enrichment_id:
        one = knobs_for(enrichment_id, installed_min_only=installed_min_only)
        return {
            "success": bool(one.get("success")),
            "count": 1 if one.get("success") else 0,
            "total_knob_slots": 12 if one.get("success") else 0,
            "enrichments": [one] if one.get("success") else [],
            "error": one.get("error"),
        }
    rows = [knobs_for(row[0], installed_min_only=installed_min_only) for row in _X_ROWS]
    return {
        "success": True,
        "count": len(rows),
        "total_knob_slots": len(rows) * (4 if installed_min_only else 12),
        "mega_min_knobs": list(MEGA_MIN_KNOBS),
        "knob_glossary": [
            {"knob": k, **KNOB_META[k]} for k in ALL_KNOBS
        ],
        "enrichments": rows,
        "priority_ids": list(PRIORITY_IDS),
        "priority_by_pillar": {k: list(v) for k, v in PRIORITY_BY_PILLAR.items()},
    }
