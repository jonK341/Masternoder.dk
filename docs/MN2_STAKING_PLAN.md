# MN2 staking on Masternoder.dk — implementation plan (browser "staking rig" + custodial pool)

This plan adds **MN2 staking** to the **user wallet** so users can stake their in‑app MN2 balance and earn rewards, with a **browser‑based "staking rig"** that runs on the user's **own computer processor** as the visible heartbeat and reward‑weighting signal.

It builds on the existing MN2 wallet stack (`backend/services/mn2_*.py`, `backend/routes/mn2_routes.py`, `data/mn2_config.json`), the unified points + booster system (`backend/services/unified_points_database.py`), and the shop (`backend/routes/shop_routes.py`, `data/monetization_config.json`).

**Related docs:** [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md) · [AGENTS_MN2.md](AGENTS_MN2.md) · [MN2_OPS.md](MN2_OPS.md)

---

## 0. Core constraints (read first)

**MN2 is a Proof‑of‑Stake (PoS) coin** (white paper §3, tokenomics: 50% masternode / 50% staking). PoS "staking" means a **wallet/daemon stays online to mint blocks** — there is **no per‑user CPU mining** in the protocol, and a browser cannot validate MN2 blocks. Real yield comes only from the site's daemon actually staking the pooled coins.

**Architecture: A + B hybrid (locked).**
- **A (real yield):** the site's MN2 daemon **actually PoS‑stakes the pooled custodial balance** (see §9). This is the only true source of staking rewards.
- **B (user CPU + UX):** each user opts in their `mn2_balance`, and the wallet gives them a **browser Web Worker ("staking rig")** that uses their own processor to post periodic proofs. Rig uptime + **longevity** weight how the real pool yield is distributed and power the live "you are staking" UX.

> **Honesty requirement:** UI/disclaimers must state plainly that the browser rig is a **participation/engagement signal**, not on‑chain block validation, and that rewards are paid from the pool's realized staking yield. Never imply the user's CPU mines MN2. Full risk framing in §10.

---

## 1. Goals & non‑goals

**Goals**
- Stake / **instant‑unstake** MN2 from the **user wallet** (no lock, no cooldown).
- Run a **browser staking rig** on the user's own machine (runs at **default uptime settings**, no user tuning required).
- **Longevity rewards:** the longer a user continuously stakes with an active rig, the higher their reward multiplier (tiered).
- **Shop staking boost:** a purchasable booster that multiplies staking rewards for a duration.
- **Reward calculator:** projected earnings from amount × APR × longevity tier × boost × uptime.
- **Staking monitor:** a live view of all users' staking processes (anonymized) with aggregate stats.
- Rewards accrue automatically from **realized daemon yield**, credit to `mn2_balance`, fully ledgered and reconcilable.
- Full **agent/API parity**, auto‑discovered blueprint.

**Non‑goals (this phase)**
- Real per‑user on‑chain validation, user‑hosted masternodes, or a downloadable node.
- Smart‑contract staking. Crediting is custodial and server‑authoritative.

---

## 2. Architecture overview

```
Browser staking rig (Web Worker, user CPU, default settings)
  └── POST /api/mn2/staking/work  (signed heartbeat/proof, throttled)
        │
Flask backend
  ├── mn2_staking_routes.py      (stake / unstake / status / work / calculator / leaderboard / monitor)
  ├── mn2_staking_service.py     (stake state, accrual, longevity, boost, uptime weighting, anti-abuse)
  ├── unified_points_database    (+ "mn2_staked" bucket; reuse add_booster/active_boosters for staking boost)
  ├── shop_routes.py             (+ "staking_boost" booster SKU effect)
  └── mn2_ledger.py              (+ entry types: stake / unstake / staking_reward)
        │
Reward engine (cron + endpoint)
  └── accrue_rewards(): distribute realized pool yield, weighted by
      staked × longevity_multiplier × uptime_weight × active_boost, credited to mn2_balance
        │
MN2 daemon (server) — actually PoS-stakes the pooled custodial coins (real yield; see §9)
```

**Source of truth:** server‑side stake state + ledger. The daemon's realized staking income defines the reward budget; the engine never pays out more than realized yield (minus a configurable site margin).

---

## 3. Data & config

### 3.1 New config: `data/mn2_staking_config.json`
```json
{
  "enabled": true,
  "min_stake": 0.1,
  "max_stake_per_user": 10000,
  "instant_unstake": true,
  "lock_period_hours": 0,
  "unstake_cooldown_hours": 0,
  "base_apr_percent": 5.0,
  "reward_pool_mode": "realized_yield",
  "site_margin_percent": 20.0,
  "accrual_interval_minutes": 60,
  "worker": {
    "enabled": true,
    "use_defaults": true,
    "uptime_weight": 1.25,
    "min_uptime_weight": 1.0,
    "max_uptime_weight": 1.5,
    "heartbeat_interval_seconds": 30,
    "proof_difficulty": 16,
    "grace_missed_heartbeats": 2
  },
  "longevity_tiers": [
    {"id": "bronze",   "min_days": 0,  "multiplier": 1.0,  "label": "Bronze"},
    {"id": "silver",   "min_days": 7,  "multiplier": 1.1,  "label": "Silver (7d+)"},
    {"id": "gold",     "min_days": 30, "multiplier": 1.25, "label": "Gold (30d+)"},
    {"id": "platinum", "min_days": 90, "multiplier": 1.5,  "label": "Platinum (90d+)"}
  ],
  "boost": {
    "shop_effect": "staking_boost",
    "max_stacked_multiplier": 2.0
  },
  "requires_verification": false,
  "disclaimer": "Staking moves your in-app MN2 into the staking pool to earn rewards from realized network staking yield. The browser staking rig uses your device's processor only as a participation signal that boosts your reward share — it does NOT validate MN2 blocks or mine MN2. Rewards are variable, not guaranteed, and depend on actual pool yield. Not financial advice. See full terms and risk disclosure."
}
```

### 3.2 New state files (mirror existing `data/mn2_*` patterns, thread‑locked)
- `data/mn2_stakes.json` — `{ user_id: { staked, since_iso, staking_since_iso (longevity anchor), last_accrued_iso, total_earned, longevity_tier } }`. `staking_since_iso` resets only when stake goes to 0; partial unstakes keep longevity.
- `data/mn2_worker_sessions.json` — per‑user rig uptime accounting (rolling window, last heartbeat, accepted proofs, uptime_ratio).

### 3.3 Ledger (extend `backend/services/mn2_ledger.py`)
- New `entry_type` values: `stake`, `unstake`, `staking_reward`.
- Extend `get_wallet_activity_days()` so `staking_reward` counts as inflow and `stake`/`unstake` are neutral internal moves (keeps reconciliation correct).

### 3.4 Unified points & boosters (extend `backend/services/unified_points_database.py`)
- Add a `mn2_staked` bucket parallel to `mn2_balance` in `_points_payload_from_file`, `_points_payload_from_db`, `_merge_points_payloads`, and `get_all_points` numeric keys.
- Stake = `add_points(uid,"mn2_balance",-amt)` + `add_points(uid,"mn2_staked",+amt)`; unstake reverses; reward = `add_points(uid,"mn2_balance",+reward,source="mn2_staking_reward")`.
- **Reuse existing booster system** for the shop boost: `add_booster(uid, sku_id, duration_minutes, name)` already stores `active_boosters` with `expires_at`; accrual reads them via `get_game_time_and_boosters(uid)`.

### 3.5 Shop staking boost (extend `data/monetization_config.json` + `backend/routes/shop_routes.py`)
- Add SKUs to `shop_booster_skus` with a new effect, e.g.:
```json
{"id": "booster-staking-150-24h", "name": "Staking Boost +50% 24h", "category": "boosts", "effect": "staking_boost", "duration_minutes": 1440, "boost_multiplier": 1.5}
{"id": "booster-staking-200-6h",  "name": "Staking Surge x2 6h",   "category": "boosts", "effect": "staking_boost", "duration_minutes": 360,  "boost_multiplier": 2.0}
```
- Extend `_apply_booster_sku()` to handle `effect == "staking_boost"`: call `add_booster(...)` with the multiplier carried in the booster name/metadata. Purchasable with coins, MN2, or PayPal like other boosters.
- Accrual multiplies a staker's share by the highest active `staking_boost` multiplier (capped by `boost.max_stacked_multiplier`).

---

## 4. Backend service — `backend/services/mn2_staking_service.py`

| Function | Purpose |
|---|---|
| `get_config()` | Load `mn2_staking_config.json` with safe defaults. |
| `stake(user_id, amount)` | Validate (min/max, balance, optional verification), move balance→staked, set `staking_since_iso` if first stake, ledger `stake`. |
| `unstake(user_id, amount)` | **Instant**: move staked→balance immediately, ledger `unstake`; reset longevity anchor only if staked hits 0. |
| `get_stake(user_id)` | Staked, pending rewards, current APR, longevity tier + progress, active boost, rig status, uptime ratio. |
| `submit_work_proof(user_id, proof)` | Validate proof + heartbeat cadence; record uptime; anti‑replay/anti‑sybil. |
| `longevity_multiplier(user_id)` | Days since `staking_since_iso` → tier multiplier from `longevity_tiers`. |
| `active_boost_multiplier(user_id)` | Highest active `staking_boost` booster (capped). |
| `accrue_rewards()` | `weight = staked × longevity × uptime_weight × boost`; `reward = pool_budget × weight / Σweight`; credit + ledger; idempotent per interval. |
| `estimate_rewards(amount, days, uptime, boost, tier)` | Pure calculator for the UI/API projection (§6). |
| `get_staking_leaderboard(limit)` | Top stakers by staked / earned / longevity. |
| `get_staking_monitor(limit)` | Aggregate + per‑user (anonymized) live staking processes for the monitor (§7). |

**Reward budget (realized_yield):** read the daemon's staking income for the interval (via `mn2_rpc_client.listtransactions` filtering `category in ("stake","generate","immature")`, or a `getbalance`/staking‑account delta), subtract `site_margin_percent`, distribute. `base_apr_percent` is a display/fallback cap only.

---

## 5. API — `backend/routes/mn2_staking_routes.py` (auto‑discovered per `register-intelligence` rule)

| Method | Path | Body/Query | Purpose |
|---|---|---|---|
| GET | `/api/mn2/staking/status` | `user_id` | staked, pending, APR, longevity tier, boost, rig status |
| POST | `/api/mn2/stake` | `user_id, amount` | stake MN2 |
| POST | `/api/mn2/unstake` | `user_id, amount` | **instant** unstake |
| POST | `/api/mn2/staking/work` | `user_id, proof, nonce, ts` | rig heartbeat/proof |
| GET | `/api/mn2/staking/calculator` | `amount, days, uptime, boost` | projected rewards (§6) |
| GET | `/api/mn2/staking/leaderboard` | `limit` | top stakers |
| GET | `/api/mn2/staking/monitor` | `limit` | all users' staking processes, anonymized + aggregates (§7) |
| GET/POST | `/api/mn2/staking/ops/accrue` | token | ops: run accrual once (cron) |

Reuse `resolve_user_id`, the `_ops_authorized()` token pattern, and `_explorer_*` helpers from `mn2_routes.py`. Add an `AGENTS_MN2.md` parity section for all new endpoints.

**Reward cron:** `cron/mn2_accrue_rewards.sh` + `cron/masternoder-mn2-accrue.cron.d`, mirroring `cron/mn2_scan_deposits.sh`. Calls `/api/mn2/staking/ops/accrue` every `accrual_interval_minutes`.

---

## 6. Staking calculations

Surface both server‑side (authoritative) and client‑side (instant preview) math:

```
daily_base   = staked × (base_apr_percent / 100) / 365
effective    = daily_base × longevity_multiplier × uptime_weight × boost_multiplier
projected_n  = effective × days
share_of_pool= weight / Σ weight   (shown when realized-yield data is available)
```

- **`estimate_rewards()`** in the service is the single source; `/api/mn2/staking/calculator` exposes it; the wallet UI mirrors the same formula for a live preview as the user types an amount and drags a "days / uptime / boost" slider.
- Status payload returns the user's **current** effective rate, longevity tier + days‑to‑next‑tier, and active boost so projections match reality.

---

## 7. Staking monitor (all users)

A live monitor showing **all staking processes from different users**:

- **API:** `GET /api/mn2/staking/monitor` returns `{ aggregates: { total_staked, active_stakers, active_rigs, pool_apr, rewards_paid_24h, realized_yield_24h }, processes: [ { display_id (anonymized, e.g. "user_3f9…"), staked, longevity_tier, uptime_ratio, rig_active, effective_rate, last_heartbeat } ] }`.
- **UI page** `staking-monitor/index.html` + `static/js/mn2-staking-monitor.js`: live table/cards (polled), aggregate header tiles, and a small chart of staked total / rewards over time. Reuse the site's existing dashboard/table styling.
- **Privacy:** never expose raw `user_id`, addresses, or balances beyond staked amount; hash/truncate identifiers. Honor the regulatory framing (§10).
- Optional admin (ops‑token) variant with non‑anonymized detail for support/reconciliation.

---

## 8. Safety, anti‑abuse & reconciliation

- **Conservation invariant:** `Σ(mn2_balance + mn2_staked)` ≤ net deposits − withdrawals. Extend `scripts/mn2_reconcile.py` to alert on drift.
- **No pay > yield:** payouts never exceed realized pool yield minus margin.
- **Weighting bound:** staked amount **dominates**; longevity, uptime, and boost only modulate (each capped) so CPU/longevity farming can't dominate the pool.
- **Worker anti‑sybil:** proofs nonce/timestamp‑bound, rate‑limited per user, capped uptime weight; default rig settings only (no client‑set weight).
- **Instant unstake guardrails:** unstake is internal balance movement only (no on‑chain send), so it's safe to be instant; existing withdrawal limits still gate moving MN2 off the site.
- **Idempotent accrual:** keyed by interval window; safe for cron retries.

---

## 9. Make the daemon actually stake pooled coins

This is now in scope (not an open question).

1. **Wallet/daemon config (`masternoder2.conf`):** `staking=1`, `enablestaking=1` (per MN2/PIVX‑style flags — confirm exact keys in the [MasterNoder2 repo](https://github.com/jonK341/MasterNoder2)), wallet unlocked for staking only (`walletpassphrase <pw> <timeout> true`).
2. **Consolidate pool:** sweep per‑user deposit addresses' confirmed balances into a dedicated **staking address/account** so coins are eligible to mint (respecting coin‑age/maturity). Keep a small hot balance for withdrawals; the rest stakes.
3. **Read realized yield:** scanner/accrual reads new `stake`/`generate` transactions (`mn2_rpc_client.listtransactions`) since last run → that interval's reward budget.
4. **Ops/health:** extend `mn2_rpc_client.health_check()` and `/api/mn2/ops/stats` to report `staking_active`, `staking_weight`, `expected_time_to_reward`, immature/mature balances. Add a `MN2_OPS.md` runbook.
5. **Custody/security:** staking key handling, cold‑storage of reserves, alerting if staking stops — documented in ops.

---

## 10. Regulatory & compliance framing (maximum)

Apply the strongest framing across UI, terms, and API responses:

- **Not financial/investment advice; no solicitation.** Clear, repeated labeling.
- **Variable, non‑guaranteed rewards.** No fixed/promised APY; show "estimated, may change," based on realized pool yield. Avoid the word "interest"; use "staking rewards."
- **Risk disclosure:** market/price volatility, custodial risk, smart‑contractless custodial model, possibility of zero rewards, slashing/maturity nuances, software/operational risk.
- **Eligibility & jurisdiction:** 18+ (or local age of majority), explicit list/gate of **restricted jurisdictions**; geofencing/region block hook; "void where prohibited."
- **AML/KYC:** tie to existing `requires_verification`/withdrawal verification; thresholds for enhanced checks; reserve right to freeze suspicious activity.
- **Terms & consent:** versioned Staking Terms + Risk Disclosure the user must accept before first stake (store acceptance + version + timestamp in the ledger/profile).
- **Tax:** user is responsible for taxes; rewards may be taxable; provide exportable history.
- **No deposit insurance:** funds are not bank deposits and are not insured.
- **Right to modify/suspend:** the program (rates, boosts, availability) can change or end at any time.
- **Browser rig honesty:** explicit statement the rig is engagement‑only and not block validation/mining; CPU‑use notice and easy opt‑out.
- **Data/privacy:** monitor data is anonymized; link to privacy policy.

Implement as: a reusable disclaimer/consent component on the wallet staking panel + monitor, a `data/mn2_staking_terms.json` (versioned text), and a consent gate in `stake()`.

---

## 11. Frontend — placed in the user wallet

### 11.1 Wallet staking panel (`profile/index.html` wallet section)
- Stake/unstake inputs, **staked balance**, **pending + total earned**, **current effective rate**, **longevity tier + progress bar to next tier**, **active boost badge**, and a **"Start staking rig"** toggle (default settings).
- **Calculator widget** (amount + days/uptime/boost preview) using §6 math.
- **Consent/disclaimer gate** (§10) before first stake; reuse the security/password step before staking real MN2.
- Link out to the **staking monitor**.

### 11.2 `static/js/mn2-staking-worker.js` (Web Worker, default uptime)
- Throttled, bounded SHA‑256 proof to `proof_difficulty`, one burst per `heartbeat_interval_seconds`; posts `{user_id,nonce,proof,ts}` to `/api/mn2/staking/work`. Auto‑pauses on hidden tab; visible on/off; runs at config defaults (no user tuning).

### 11.3 `static/js/mn2-staking.js` (wallet controller)
- Polls `/api/mn2/staking/status`, renders the panel + calculator, starts/stops the rig, surfaces tier/boost/uptime and the disclaimer.

### 11.4 Monitor page (`staking-monitor/index.html` + `static/js/mn2-staking-monitor.js`)
- Live anonymized table + aggregate tiles + simple time series (§7).

---

## 12. Phased delivery & checklist

**Phase S1 — Core staking + wallet UI**
- [ ] `mn2_staking_config.json`, `mn2_stakes.json`, `mn2_staked` bucket, ledger entry types.
- [ ] `mn2_staking_service.py`: stake / **instant** unstake / get_stake / longevity.
- [ ] `mn2_staking_routes.py`: status / stake / unstake. Wallet panel in `profile`. Consent gate (§10). Tests.

**Phase S2 — Daemon staking + reward engine**
- [ ] Daemon staking config + pool consolidation (§9); realized‑yield read.
- [ ] `accrue_rewards()` + ops accrue endpoint + cron + reconciliation extension.

**Phase S3 — Browser rig + uptime + longevity weighting**
- [ ] `submit_work_proof()` + `/staking/work`; `mn2-staking-worker.js` (default settings); uptime ratio into accrual.

**Phase S4 — Shop boost + calculator + monitor + parity**
- [ ] `staking_boost` SKUs + `_apply_booster_sku()` handling; boost into accrual.
- [ ] `/staking/calculator` + UI widget; `/staking/monitor` + `staking-monitor` page; `/staking/leaderboard`.
- [ ] `AGENTS_MN2.md` parity section; `MN2_OPS.md` staking runbook; full regulatory text in `mn2_staking_terms.json`.

---

## 13. Decisions (locked from your direction)

| # | Decision |
|---|---|
| 1 | Daemon **actually PoS‑stakes** the pooled coins → `realized_yield` (§9). |
| 2 | **Instant unstake** — no lock, no cooldown. |
| 3 | Rig runs at **default uptime settings**; uptime only modulates, staked amount dominates. |
| 4 | Staking lives in the **user wallet** (profile), not the casino. |
| 5 | **Maximum regulatory framing** (§10) + versioned consent gate. |
| 6 | **Longevity rewards** (tiered multiplier) + **shop staking boost** + **calculator** + **all‑users monitor** included. |
| 7 | **PayPal→MN2 on‑ramp: Model A (custodial) first (S6), then Model B (P2P auction) (S7)** — Model B never before Model A's hold/KYC/dispute + reserve are proven. |
| 8 | **Agent control** via parity layer (all endpoints) + a secret‑gated **automation layer** (`agent_staking_routes.py`, capability manifest, personas) with consent + kill switch (§19). |

---

## 14. Top 10 enhancement features — improve / impair analysis

Each candidate is rated for what it **improves** and what it **impairs** (the cost, risk, or downside it introduces). **Verdict**: ✅ Adopt · 🟡 Adopt guarded · ⛔ Defer/reject. Adopted items are wired into the config (§14.1) and phases (§14.2).

| # | Feature | Improves | Impairs (risk/downside) | Verdict |
|---|---------|----------|--------------------------|---------|
| 1 | **Auto‑compound rewards** (opt‑in: earned rewards auto‑restake) | Compounding growth; retention; less manual action | More ledger writes; messier instant‑unstake math; can mask flat/zero yield; harder tax export | ✅ Adopt (off by default, user toggle) |
| 2 | **Dynamic APR / yield curve** (display rate scales inversely with total staked) | Self‑balancing; rewards early adopters; payouts always ≤ realized yield | User confusion; "rate dropped" complaints; volatility; harder calculator accuracy | 🟡 Adopt guarded (always framed "estimated, variable") |
| 3 | **Real‑time updates via WebSocket/SSE** for status + monitor | Live, accurate monitor; better UX; fewer polling requests | More server load + scaling/ops complexity; extra attack surface; reconnection edge cases | 🟡 Adopt guarded (SSE first; poll fallback kept) |
| 4 | **Referral staking bonus** (inviter + invitee get a temporary boost) | Viral growth; cheap acquisition | Sybil/self‑referral fraud; dilutes real pool yield; referral = solicitation (regulatory) | 🟡 Adopt guarded (KYC‑gated, capped, anti‑sybil) |
| 5 | **Streak / daily check‑in multiplier** (rig started N days running) | Daily active use; complements longevity | Overlaps longevity; grind fatigue; punishes legitimate breaks | 🟡 Adopt guarded (small cap; merge into longevity, not additive) |
| 6 | **Reward reserve / smoothing fund** (slice of `site_margin` buffers lean intervals) | Smoother payouts; trust; cushions variable yield | Reduces immediate payouts; custodial liability; **never call it "insurance"** | ✅ Adopt (rename "stabilization reserve") |
| 7 | **Milestone badges / achievements** for tiers & totals (reuse existing achievements) | Status, gamification, retention; low cost via existing system | Dev time; can feel gimmicky; no real value | ✅ Adopt (reuse `achievements_service`) |
| 8 | **Background / PWA rig** (service worker keeps rig alive) | Higher uptime; more "real" feel | Battery drain; mobile/app‑store anti‑mining policies; trust + consent issues; abuse | ⛔ Defer (foreground‑only rig; revisit later) |
| 9 | **Optional locked vaults** (fixed‑term stake for higher boost) | Predictable pool; higher yield for committed users | **Directly contradicts the instant‑unstake promise**; liquidity risk; looks like a term‑deposit/security (regulatory) | ⛔ Defer (conflicts with locked decision §13.2) |
| 10 | **Stake‑to‑unlock casino perks** (staked balance grants casino bonuses) | Ecosystem stickiness; cross‑feature value | **Couples real‑money staking to gambling** — serious regulatory/AML exposure; reputational risk | ⛔ Reject (keep staking and casino financially separate) |

**Net:** Adopt 1, 6, 7; adopt‑guarded 2, 3, 4, 5; defer 8, 9; reject 10. The deferred/rejected items are kept here as explicit decisions so they don't get silently reintroduced.

### 14.1 Config additions for adopted features (`data/mn2_staking_config.json`)
```json
{
  "auto_compound": { "enabled_default": false, "min_reward_to_compound": 0.01 },
  "dynamic_apr": { "enabled": true, "target_total_staked": 1000000, "min_apr_percent": 2.0, "max_apr_percent": 8.0 },
  "realtime": { "transport": "sse", "poll_fallback_seconds": 15 },
  "referral": { "enabled": true, "inviter_boost": 1.1, "invitee_boost": 1.1, "duration_minutes": 1440, "max_referrals_per_user_per_day": 5, "requires_verification": true },
  "streak": { "enabled": true, "per_day_bonus": 0.01, "max_bonus": 0.1, "merged_into_longevity": true },
  "stabilization_reserve": { "enabled": true, "fund_from_margin_percent": 25.0, "max_reserve_mn2": 50000 },
  "badges": { "enabled": true, "source": "achievements_service" }
}
```
- **Dynamic APR** replaces a flat display rate: `apr = clamp(target/total_staked × base, min, max)`; the calculator (§6) and status both read it; copy always says "estimated, variable."
- **Auto‑compound** runs inside `accrue_rewards()` after crediting: if enabled and `reward ≥ min_reward_to_compound`, immediately `stake()` the reward (ledger keeps both `staking_reward` + `stake`).
- **Stabilization reserve** is a server‑held bucket funded from margin; `accrue_rewards()` may top up a lean interval from it (capped), never exceeding lifetime realized yield. Surfaced in the monitor aggregates and ops stats.
- **Referral / streak** feed multiplicative, capped multipliers into the same `weight` formula (§4); streak is folded into the longevity multiplier rather than added separately.

### 14.2 Phase placement
- **Phase S4** (extend): badges (#7), stabilization reserve (#6).
- **Phase S5 — Growth & realtime (new):** dynamic APR (#2), SSE realtime (#3), referral (#4, KYC‑gated), streak‑into‑longevity (#5), auto‑compound (#1).
- **Explicitly out (documented decisions):** background/PWA rig (#8), locked vaults (#9), stake‑to‑play casino coupling (#10).

### 14.3 Service / API touchpoints for adopted items
- `mn2_staking_service.py`: `dynamic_apr()`, `compound_if_enabled()`, `apply_referral_boost()`, `reserve_topup()`, plus streak/badge hooks in `accrue_rewards()`.
- New endpoints: `POST /api/mn2/staking/auto-compound` (toggle), `POST /api/mn2/staking/referral` (claim/apply), `GET /api/mn2/staking/stream` (SSE). All auto‑discovered; mirrored in `AGENTS_MN2.md`.
- **Regulatory (§10) extends to these:** referral = capped + KYC + "not a solicitation"; dynamic APR = "estimated/variable, may decrease"; reserve = "stabilization, not insurance, not guaranteed."

---

## 15. User reward tracking table (per‑user, all stats)

A durable, per‑accrual record so every user can audit exactly how each reward was computed, and so the monitor (§7) and calculator (§6) can show real history instead of estimates.

### 15.1 Store: `data/mn2_staking_rewards.jsonl` (append‑only, one row per user per accrual interval)
Idempotent on `(user_id, interval_id)`; never rewrites history. Each row:

| Field | Meaning |
|-------|---------|
| `interval_id` | UTC window key (e.g. `2026-06-03T18:00Z`) — dedupe key |
| `user_id` | staker |
| `staked` | amount staked during the interval |
| `longevity_days`, `longevity_tier`, `longevity_mult` | tier + multiplier applied |
| `uptime_ratio`, `uptime_weight` | rig participation that interval |
| `boost_mult`, `boost_sku` | active shop staking boost (if any) |
| `referral_mult`, `streak_mult` | other multipliers (§14) |
| `effective_apr` | dynamic APR used (§14 #2) |
| `weight` | `staked × longevity × uptime × boost × referral × streak` |
| `pool_share_pct` | `weight / Σ weight` for the interval |
| `pool_budget_mn2` | realized yield budget that interval |
| `reward_mn2` | credited reward |
| `compounded_mn2` | portion auto‑restaked (§14 #1) |
| `reserve_topup_mn2` | added from stabilization reserve (§14 #6) |
| `cumulative_earned_mn2` | running total for the user |
| `balance_after_mn2`, `staked_after_mn2` | post‑accrual snapshot |

### 15.2 API & UI
- `GET /api/mn2/staking/rewards-table?user_id=...&limit=...&from=...&to=...` → paginated rows + summary (`total_earned`, `avg_effective_apr`, `best_interval`, `current_streak`, `tier`).
- `GET /api/mn2/staking/rewards-table.csv` → export for tax/records (ties to §10 tax framing).
- **Wallet UI:** a sortable "Reward history" table under the staking panel (§11) with the summary tiles up top; the §6 calculator pre‑fills from the user's real averages.
- **Reconciliation:** `Σ reward_mn2` over all rows must equal credited `staking_reward` ledger entries — added to `scripts/mn2_reconcile.py` checks.

---

## 16. Explorer stats for a better overview

Pull live MN2 network stats so users see staking in network context. Source order: **own daemon RPC first**, **Chainz CryptoID fallback** (cached, respecting the 1‑req/10s limit — extend `backend/services/mn2_chainz.py`, which already does `getblockcount` + `ticker.usd`).

| Stat | Source | Notes |
|------|--------|-------|
| Block height / sync | RPC `getblockcount` (Chainz `getblockcount`) | already wired |
| MN2/USD price + change | Chainz `ticker.usd` | already wired (cache 10 min) |
| Network stake weight / "staking difficulty" | RPC `getstakinginfo` / `getmininginfo` | drives realistic APR context |
| Masternode count (~117k) | RPC `getmasternodecount` / Chainz | from explorer overview |
| Difficulty / hashrate | RPC `getdifficulty` (Chainz) | network health |
| Circulating supply / rich list / wealth dist. | Chainz | "top holders" context (read‑only) |
| Our pool vs network share | derived: pooled_staked / network_stake_weight | shows our pool's footprint |

- **Service:** extend `mn2_chainz.py` with `chainz_masternode_count()`, `chainz_difficulty()`, and a `network_overview()` aggregator (RPC‑first, Chainz‑fallback, all cached). Add RPC helpers `getstakinginfo`/`getmasternodecount`/`getdifficulty` to `mn2_rpc_client.py`.
- **API:** `GET /api/mn2/network-overview` (no auth, public, cached). Feeds the staking **monitor** (§7), the **wallet** header, and the **reward table** summary (e.g. "your effective APR vs network").
- **Resilience:** never block crediting on explorer availability; serve stale cache; explorer is display‑only (per the integration doc's RPC‑vs‑explorer rule).

---

## 17. PayPal → MN2 on‑ramp (auto‑buy) — trading channel / auction

Goal: a user pays via PayPal and **automatically receives MN2**. Add the resulting volume/price stats to the overview (§16) and monitor (§7).

> ⚠️ **Core risk (must design around):** the repo's own rule — *"Do not mix chargeback‑prone fiat flows with irreversible crypto settlement in one unclear SKU"* (`content/digital_goods/paypal-mn2-rails-onepager.md`). **PayPal is reversible (chargebacks/disputes up to 180 days); MN2 sends are irreversible.** An automatic PayPal→MN2 sale is a prime fraud target. Mitigations below are mandatory, not optional.

### 17.1 Two models

**Model A — Custodial on‑ramp (recommended first):**
- Fixed‑price "Buy MN2" packs (like the casino PayPal packs in `casino_service`/`paypal_routes.py`). User pays USD; on PayPal **capture webhook**, credit `mn2_balance` from the **site treasury** at a quoted, time‑boxed rate (uses §16 price + spread).
- Site is the counterparty → no third‑party seller to defraud. Crypto stays **in‑app** (not withdrawable) until a **hold/clearance window** (e.g. 72h–7d, or until chargeback risk passes / KYC tier met), satisfying the reversibility mismatch.

**Model B — P2P trading channel / auction (later, guarded):**
- Extend the existing `backend/services/shop_auction_service.py` (it already has `create_listing`, `buy_listing`, `place_bid`, `accept_bid`, `price_history`, `_coins_per_mn2`) with an **MN2‑sell** listing type priced in USD, buyer pays via PayPal.
- Requires **seller escrow** (seller's MN2 locked in‑app before listing), automatic transfer to buyer on captured receipt, and chargeback insurance via the stabilization reserve (§14 #6) or seller bond.

### 17.2 Mandatory mitigations (both models)
- **Quote lock + spread:** price quoted from §16 feed, valid ~60s; spread covers volatility + risk.
- **Hold window before withdrawal:** purchased MN2 is stakeable/spendable in‑app but **not withdrawable** until the clearance window passes (defeats buy‑then‑chargeback‑then‑withdraw).
- **KYC/AML tiers + limits:** per‑user daily/lifetime USD caps; higher caps require verification (reuse `mn2_verification` + §10).
- **Webhook verification:** verify PayPal IPN/webhook signature; idempotent on PayPal `capture_id`; never credit on client‑reported success alone.
- **Dispute handling:** on chargeback/dispute webhook → claw back un‑withdrawn MN2, freeze account, debit reserve if already gone; full audit trail.
- **Clear SKU separation:** distinct catalog item tagged `paypal`+`mn2`, never bundled with other goods (per the one‑pager rule).

### 17.3 Data, API & stats
- Store: `data/mn2_onramp_orders.jsonl` — `{ order_id, paypal_capture_id, user_id, usd_amount, quoted_rate, mn2_amount, status: quoted|paid|credited|held|cleared|charged_back, hold_until, created_at }`.
- API:
  - `GET /api/mn2/onramp/quote?usd=...` → locked quote (rate from §16, spread, expiry).
  - `POST /api/mn2/onramp/order` → create PayPal order for a quote.
  - `POST /api/mn2/onramp/webhook` → PayPal capture/dispute handler (signature‑verified, idempotent) → credit/hold/clawback.
  - `GET /api/mn2/onramp/status?order_id=...` → poll.
  - (Model B) reuse/extend auction endpoints for MN2‑sell listings.
- **Add to stats:** §16 `network-overview` and the §7 monitor gain `onramp_volume_usd_24h`, `mn2_sold_24h`, `avg_onramp_rate`, `open_orders`, `chargeback_rate`; the user reward/wallet table (§15) shows the user's own on‑ramp purchases alongside rewards.
- **Ledger:** new entry type `onramp_purchase` (inflow), `onramp_clawback` (reversal); included in reconciliation (§8).

### 17.4 Phase placement
- **Phase S6 — On‑ramp (Model A) + explorer overview + reward table (new):** §15 reward table, §16 network overview, §17 Model A custodial on‑ramp with hold/KYC.
- **Phase S7 — P2P MN2 trading/auction (Model B, guarded):** only after Model A + reserve + dispute handling are proven; escrow + seller bonds required.

---

## 18. Updated phase map

| Phase | Scope |
|-------|-------|
| S1 | Core staking + wallet UI + consent gate |
| S2 | Daemon staking + reward engine (realized yield) |
| S3 | Browser rig + uptime + longevity weighting |
| S4 | Shop boost + calculator + monitor + badges + stabilization reserve |
| S5 | Growth & realtime: dynamic APR, SSE, referral, streak, auto‑compound |
| **S6** | **Reward tracking table (§15) + explorer overview (§16) + PayPal→MN2 on‑ramp Model A (§17)** |
| **S7** | **P2P MN2 trading/auction Model B (§17), guarded** |

> **Decision (locked):** **Model A (custodial on‑ramp) ships first in S6; Model B (P2P auction) follows in S7** — only after Model A's hold/KYC/dispute machinery + stabilization reserve are proven in production.

---

## 19. Agent control of the staking system

Per the **agent‑native** + **project‑rethink** rules: every staking action a user can take in the UI must be achievable by an agent, exposed as **atomic tools** through a **single staking agent surface** (not fragmented blueprints), and discoverable so LLM/MCP/cron agents can drive it autonomously.

### 19.1 Two layers of control
1. **Parity layer (already in the plan):** the per‑user endpoints in §5/§15/§16/§17 work for agents today — any client sends `user_id` (query/body), exactly like `AGENTS_MN2.md` describes for the existing MN2 flows. No extra auth beyond normal user resolution.
2. **Automation layer (new, secret‑gated):** a headless surface for agents acting on behalf of users/personas, mirroring `backend/routes/agent_shop_crypto_routes.py` (`AGENT_MN2_SHOP_SECRET` + `X-Agent-Shop-Key`). New `backend/routes/agent_staking_routes.py` with `AGENT_MN2_STAKING_SECRET` + header `X-Agent-Staking-Key`.

### 19.2 Atomic agent tools (capability manifest)
`GET /api/agent/staking/capabilities` → machine‑readable manifest (verbs, params, auth, limits) so agents self‑discover. Each verb maps to a service call in `mn2_staking_service.py`:

| Verb | Maps to | Notes |
|------|---------|-------|
| `get_status` | `get_stake` | read‑only |
| `stake` | `stake(user_id, amount)` | obeys min/max + consent (§19.4) |
| `unstake` | `unstake(...)` | instant |
| `submit_work` | `submit_work_proof(...)` | agents may run a headless rig worker (default settings) |
| `toggle_auto_compound` | auto‑compound flag (§14 #1) | |
| `claim_referral` | `apply_referral_boost(...)` | KYC‑gated |
| `get_rewards_table` | §15 table | + CSV |
| `get_network_overview` | §16 | public |
| `onramp_quote` / `onramp_order` / `onramp_status` | §17 Model A | KYC + hold apply |
| `simulate` | `estimate_rewards(...)` | calculator, no side effects |

`POST /api/agent/staking/execute` → `{ verb, user_id, params, agent_id }`, secret‑gated, idempotency key supported, logged to agent activity (reuse `agent_activity_tracker`).

### 19.3 Agent personas & autonomy
- `data/agent_staking_agents.json` (like `agent_crypto_wallet_agents.json`): personas with a bound `user_id`, policy (max stake, allowed verbs, auto‑compound on/off, target tier).
- Optional **autonomous loop** (cron/agent): keep the rig heartbeat alive, auto‑restake matured rewards, rebalance toward a target staked amount within policy caps — implemented as a prompt/policy over the atomic tools, not new bespoke logic.
- **MCP/Cursor parity:** since everything is plain HTTP, MCP tools and Cursor agents drive staking with no extra integration.

### 19.4 Agent safety & governance
- **Separate secret** (`AGENT_MN2_STAKING_SECRET`) distinct from user, ops, and shop secrets; rotate independently.
- **Same guardrails as users:** min/max, dynamic limits, KYC tier, rate limits, conservation invariant (§8).
- **Consent (§10):** an agent acting for a user must pass a recorded consent/terms acceptance (version + timestamp) before its first `stake`/`onramp_order`; otherwise the verb is rejected with `consent_required`.
- **Full audit:** every agent action writes `agent_id`, verb, params, and result to the ledger/agent activity log; surfaced (anonymized) in the §7 monitor with an "agent" flag and counted in stats (`agent_staked`, `agent_actions_24h`).
- **Kill switch:** ops can disable the automation layer (config `enabled: false`) without affecting the user parity layer.

### 19.5 Touchpoints
- New: `backend/routes/agent_staking_routes.py`, `data/agent_staking_agents.json`, capability manifest.
- Extend: `mn2_staking_service.py` (verb dispatch is thin — reuse existing functions), `AGENTS_MN2.md` (agent parity + automation section), `MN2_OPS.md` (secret + kill‑switch runbook).
- **Phase placement:** parity layer lands automatically with S1–S6 (the endpoints exist); the **automation layer (`agent_staking_routes.py` + manifest + personas) is its own slice in S4**, then extended in S5/S6 as new verbs (referral, on‑ramp) come online.
