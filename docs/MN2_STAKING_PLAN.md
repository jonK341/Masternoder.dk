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

> **POLICY — daemon is the source of truth; the interface never moves money (locked).** All real value transfer — deposits (crediting), withdrawals, on‑chain sends, staking/minting, reward generation — is performed **by the MN2 daemon over JSON‑RPC**, never by the website UI, the explorer, or any cached stat. The site UI and the self‑hosted explorer are **display‑only**:
> - A deposit is credited **only** when the daemon confirms it on‑chain (deposit scanner reads daemon RPC), regardless of what any page shows.
> - A withdrawal/send succeeds **only** when the daemon broadcasts and confirms it; the UI may show "pending" but must never fabricate a result.
> - **No balance‑affecting operation may depend on the explorer (iquidus/Chainz) or on `network-overview` being reachable.** If the explorer or a stats feed is down, slow, or behind, transactions and crediting must continue unaffected; stats simply degrade to "—". (Same rule as [MN2_EXPLORER_PLAN.md §0](MN2_EXPLORER_PLAN.md) and the RPC‑vs‑explorer rule in [MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md](MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md).)
> - Corollary: if the daemon is unsynced/locked/offline (e.g. peers lost, mnsync incomplete), the correct behavior is that real yield is **0** and transactions wait for the daemon — the UI must reflect reality, not paper over it.

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

**Reward budget (realized_yield):** read the daemon's staking income for the interval (via `mn2_rpc_client.listtransactions` filtering `category in ("stake","generate","immature","mint")`, or a `getbalance`/staking‑account delta), subtract `site_margin_percent`, distribute. `base_apr_percent` is a display/fallback cap only.

> **Per‑txid high‑watermark (required):** coinstake txns persist in `listtransactions` across many hourly intervals, so realized yield must count each coinstake **txid only once**. `_read_realized_yield_mn2()` takes the already‑counted txid set from reserve state (`counted_yield_txids`, capped) and only sums new txids; without this the same yield is re‑counted every interval and over‑distributed (breaks the §8 "never pay > realized yield" invariant). When no new yield is found, accrual falls back to the APR display rate.

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

- **Conservation invariant (implemented S8):** `backend/services/mn2_staking_reconcile_service.py` verifies, against the ledger, that Σ reward rows == `staking_reward` entries, live staked == Σ`stake`−Σ`unstake`, on‑ramp funded/clawed == ledger, and P2P outstanding escrow == escrowed−returned−delivered. Surfaced at `GET/POST /api/mn2/staking/ops/reconcile` (HTTP 409 on hard drift), printed by `scripts/mn2_reconcile.py`, and checked hourly by the accrual cron.
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

### 9.1 Operational status — daemon staking activation (live)

Ops tooling: **`scripts/mn2_enable_staking.py`** (SSH, reuses `deploy_ssh_env` creds). Discovers the running `masternoder2d`, reads RPC creds from `/var/www/html/.env`, and (with `--apply`) sets `staking=1`/`enablestaking=1` in the active datadir config (`/var/www/html/config/masternoder2.conf`) and restarts via systemd. Flags: `--apply`, `--unlock` (needs `MN2_WALLET_PASSPHRASE`), `--addnode IP[,IP...]` (persist peers + live add), `--watch [--watch-min N]` (read‑only sync poll), `--mnsync-reset`.

**This build is PIVX‑style:** `getstakinginfo` is not implemented — the staking RPC is **`getstakingstatus`** (`mn2_rpc_client.staking_health()` already falls back to it, S9). Staking is **gated on masternode sync**: `getstakingstatus.mnsync` must be `true` before `"staking status"` can be `true`.

**Status: STAKING ACTIVE (2026‑06‑03).** `mnsync` reached `FINISHED (999)` and `getstakingstatus` reports `"staking status": true` — the daemon is minting from the ~99,761 MN2 balance. Reached by driving the stuck masternode sync `2→3→4→999` with `scripts/mn2_enable_staking.py --mnsync-finish` (fresh‑peer injection). 9 `addnode=` peers are persisted in `/var/www/html/config/masternoder2.conf`.

App‑side confirmation: `GET /api/mn2/ops/stats` → `staking_health.staking_active: true`, `status: "active"` (held stable across repeated polls), `mature_balance ≈ 99,761`, `immature_balance: 0` until the first coinstake mints.

> **Restart caveat / recovery:** the fulfilled‑request deadlock can recur after a daemon restart if fewer than ~6 peers reconnect before the winners stage. Separately, `masternode-sync.cpp` `Process()` calls `Reset()` whenever `IsSynced() && mnodeman.CountEnabled()==0`, so on windows where the chain shows 0 enabled masternodes the sync briefly resets and re‑finishes (staking blips inactive then active — self‑recovering). If `getstakingstatus.mnsync` is `false` and stays false after a restart, re‑run `python scripts/mn2_enable_staking.py --mnsync-finish` to push it back to `999`.

**Historical (pre‑fix) state:** config had `staking=1`/`enablestaking=1`; wallet unlocked; `validtime/haveconnections/walletunlocked/mintablecoins/enoughcoins` all `true`. The only blocker was `mnsync: false`, parked at the winners stage (`RequestedMasternodeAssets: 3`, `RequestedMasternodeAttempt: 5`, `lastMasternodeWinner: 0`).

**Root cause (confirmed against `MasterNoder2/src/masternode-sync.cpp`, constants `MASTERNODE_SYNC_TIMEOUT=5`, `THRESHOLD=2`):** the `MNW` (winners) stage advances to `BUDGET` either when it receives a real winner vote (`lastMasternodeWinner > 0`) or via a timeout branch (`lastMasternodeWinner == 0 && time-in-stage > 25s → GetNextAsset`). On a 1‑masternode chain there are **no winner broadcasts**, so only the timeout branch can fire — but it sits **after** `if (pnode->HasFulfilledRequest("mnwsync")) continue;`. Once every connected peer has been asked once (`attempt == #peers == 5`), all peers `continue` and the timeout branch becomes unreachable → permanent deadlock. Plain `mnsync reset` just replays the climb and re‑deadlocks on the same peers.

**Fix lever:** `scripts/mn2_enable_staking.py --mnsync-finish` injects **fresh, unfulfilled** peer connections (`addnode <ip> onetry`) in a loop. The sync `Process()` advances **one peer per ~5s tick**; with **≥6 connected peers** the 6th peer is processed at ~30s into the stage — still unfulfilled and now past the 25s timeout → `GetNextAsset` → walks `MNW → BUDGET → FINISHED (999)`. With only 5 peers it parks at `attempt=5` and loses the race. The loop must run uninterrupted ~60–90s.

**Spork facts (confirmed live 2026‑06‑03 via `spork show`):**
- `SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT = 4070908800` → **OFF**, so the winners‑stage timeout *advances* rather than FAILs (good — no FAIL loop; `nCountFailures=0`).
- `SPORK_106_STAKING_SKIP_MN_SYNC = 1703122560` → **ACTIVE but a red herring:** it is **not** wired into this build's staking minter. `MasterNoder2/src/miner.cpp` (the `ThreadStakeMinter` wait loop) hard‑requires `masternodeSync.IsSynced()` (`RequestedMasternodeAssets == 999`) with no spork bypass. Therefore **mnsync MUST reach FINISHED before the daemon will mint** — there is no shortcut; `--mnsync-finish` (or enough fresh peers + a restart) is the path.

---

## 9.2 Account security — withdrawal/stake identity hardening (implemented 2026‑06‑03)

**Vulnerability found & fixed:** the money‑moving endpoints resolved identity via `resolve_user_id(from_body=True, from_query=True)`, which trusts a caller‑supplied `user_id`. With no enforced session, an unauthenticated request like `POST /api/mn2/withdraw {"user_id":"<victim>","address":"<attacker>","amount":…}` could drain another account (the lifecycle middleware does not establish a session when a `user_id` is supplied). **Fix:** `/api/mn2/withdraw`, `/api/mn2/stake`, `/api/mn2/unstake` now resolve identity **server‑side only** (`from_body=False, from_query=False`; session → IP/fingerprint identification) and return `401 auth_required` if unresolved. An attacker passing someone else's id now only ever acts as their own identity. The secret‑gated agent layer (`agent_staking_routes.py`) is unaffected — it calls the service functions directly under `AGENT_MN2_STAKING_SECRET`.

**Layered controls (all implemented 2026‑06‑03):**
1. **Server‑resolved identity** on `withdraw`/`stake`/`unstake` and on the read endpoints `staking/status` + `rewards-table` (no caller‑supplied `user_id`).
2. **Password gate:** withdraw calls `account_security_service.check_real_money_action(user_id, verification_token)`; password‑protected accounts must pass a fresh token from `POST /api/user/security/verify` (`code: password_verification_required`).
3. **KYC allowlist (available, currently OFF):** `withdrawal_requires_verification` in `data/mn2_config.json`. **Set to `false` (2026‑06‑04) so withdrawals are open to all users** — the allowlist is opt‑in for when stricter gating is needed. When set to `true`, only `user_id`s in `data/mn2_verified_users.json` may withdraw. Manage it without guessing ids:
   - **Index to pick from:** `GET /api/mn2/ops/holders?with_balance=1` returns every MN2 user (`user_id`, `deposit_address`, `mn2_balance`, `mn2_staked`, `verified`) sorted by holdings — the list you choose verified users from.
   - **Add/remove:** `POST /api/mn2/ops/verify-user {user_id|address, action:"add"|"remove"}` — pass either the internal `user_id` or the user's **deposit `address`** (resolved to its owner via the deposit‑address map). Ops‑secret gated. Set `withdrawal_requires_verification:false` to disable the allowlist entirely.
4. **New‑address cooling‑off:** `withdrawal_new_address_cooldown_hours: 2` — a never‑before‑used payout address is registered and held 2h (`backend/services/mn2_withdrawal_guard.py`, `data/mn2_withdrawal_addresses.json`, `code: address_cooldown`). Reused addresses pass immediately.

**Files:** `backend/routes/mn2_routes.py`, `backend/routes/mn2_staking_routes.py`, `backend/services/mn2_withdrawal_guard.py`, `data/mn2_config.json`, `data/mn2_verified_users.json`.

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
| **S7** | **P2P MN2 trading/auction Model B (§17)** — now **enabled** |
| **S8** | **Conservation invariant + reconcile service** (`mn2_staking_reconcile_service.py`, `/api/mn2/staking/ops/reconcile`, `scripts/mn2_reconcile.py`, hourly cron drift alert) |
| **S9** | **Daemon staking health/ops** (`rpc_client.staking_health()` → `staking_active`, weight, expected‑time, mature/immature in `/api/mn2/ops/stats`) — **daemon activation live, see §9.1** (`scripts/mn2_enable_staking.py`; PIVX `getstakingstatus`; staking gated on `mnsync`) |
| **S10** | **Agent personas + autonomous loop** (`mn2_staking_agents_service.py`, `data/agent_staking_agents.json`, `run_agent`/`run_all`, ops `run-all` cron, agent flag + `agent_staked_mn2`/`agent_actions_24h` in monitor) |

> **Decision (locked):** **Model A (custodial on‑ramp) ships first in S6; Model B (P2P auction) follows in S7.** As of S7 the P2P market is **enabled** (`p2p.enabled: true`) — sellers are still KYC‑gated, buyer MN2 stays in the hold window, and the §8 reconcile (S8) + reserve guard the books.
>
> **S8–S10 (hardening):** S8 makes the books self‑checking (every `stake/unstake/reward/onramp/p2p` move must reconcile, hard drift → HTTP 409 + cron alert); S9 surfaces whether the daemon is actually minting; S10 lets headless/cron/LLM personas drive staking within per‑persona policy caps under the same consent + guardrails as users, with a kill switch (`agent.automation_enabled`).

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

---

## 20. Roadmap v2 — 25 new feature ideas (2026‑06‑04)

S1–S10 shipped the core: staking, daemon yield, rig, monitor, reward table, on‑ramp, P2P, reconcile, daemon health, agents, and the withdrawal‑security hardening (§9.2). §14 already decided on auto‑compound, dynamic APR, SSE, referral, streak, reserve, badges (and deferred PWA rig / locked vaults / casino coupling). **The 25 below are net‑new and explicitly do not repeat §14.** Each notes effort (S ≤1d · M ≤1wk · L >1wk) and the main risk; most reuse existing services (`mn2_staking_service`, `mn2_ledger`, §15 reward table, §16 overview, `mn2_verification`, `achievements_service`).

### 20.1 Wallet & user experience
| # | Feature | Reuses | Effort | Main risk |
|---|---------|--------|--------|-----------|
| 1 | **Staking dashboard charts** — earnings‑over‑time, projected‑vs‑actual, tier progress bars from §15 rows | §15 reward table | M | none material; client‑side render |
| 2 | **Reward notifications & weekly digest** — email/push on accrual, tier‑up, large reward; opt‑in | existing mailer / notifications | S | spam/consent; throttle + unsubscribe |
| 3 | **Goal planner** — "reach X MN2 by date" → required stake/APR, fed by §6 calculator | §6 calculator | S | over‑promising; label "estimate" |
| 4 | **Fiat value toggle** — show MN2 worth in USD/EUR everywhere using §16 price | §16 overview | S | stale price; show "as of" + source |
| 5 | **Withdrawal address book** — user pre‑approves/labels payout addresses; trusted ones skip the 2h cooldown after first clearance | §9.2 guard | M | self‑service weakens cooldown; require step‑up to add |

### 20.2 Growth & social
| # | Feature | Reuses | Effort | Main risk |
|---|---------|--------|--------|-----------|
| 6 | **Public staking leaderboard** — opt‑in handle, totals/tier; anti‑doxxing (no balances unless opted) | monitor aggregates | S | privacy; opt‑in only, hide amounts |
| 7 | **Staking teams/pools** — friends pool longevity for a team multiplier + team board | longevity engine | L | collusion/sybil; cap team boost |
| 8 | **Seasonal competitions** — time‑boxed leaderboards with MN2 prize pool from margin | reserve/margin | M | prize = promo/regulatory; T&Cs + caps |
| 9 | **Tier‑up bonus** — one‑time MN2 grant when crossing a longevity tier | longevity + ledger | S | yield dilution; fund from margin only |
| 10 | **Share cards / OG images** — auto "I'm staking N MN2" image for socials | §16 + renderer | S | brand/claims; no yield promises on card |

### 20.3 Trust & transparency
| # | Feature | Reuses | Effort | Main risk |
|---|---------|--------|--------|-----------|
| 11 | **Proof‑of‑reserves page** — pooled custodial balance vs total user liabilities, with the on‑chain staking address linked | §8 reconcile, RPC | M | exposes shortfall if books drift; gate on reconcile=green |
| 12 | **Realized‑yield report** — daemon staking income vs rewards paid vs site margin, per period | §9 health, §15 | M | reveals margin; frame as transparency |
| 13 | **On‑chain block log** — list blocks minted by the pool's staking address (explorer deep‑links) | §16 explorer | S | none; read‑only |
| 14 | **Personal audit log** — user views/exports their own ledger entries (stake/unstake/reward/onramp) | `mn2_ledger` | S | PII in export; scope to self only |

### 20.4 Monetization & treasury
| # | Feature | Reuses | Effort | Main risk |
|---|---------|--------|--------|-----------|
| 15 | **Gift / internal MN2 transfer** — send MN2 to another user; inherits hold gate | ledger + hold gate | M | money‑transmission optics; KYC + caps + audit |
| 16 | **VIP tiers** — higher lifetime stake → tighter on‑ramp spread + priority support | on‑ramp pricing | S | complexity; keep tiers few |
| 17 | **Treasury dashboard (ops)** — hot/cold split, float, buy‑back/burn levers, margin take | §9 + reserve | M | ops‑only; never user‑facing |
| 18 | **"Pro staker" subscription** — monthly fee unlocks advanced analytics + projections (not yield) | monetization config | M | must NOT sell yield; analytics only (regulatory) |

### 20.5 Reliability, security & compliance
| # | Feature | Reuses | Effort | Main risk |
|---|---------|--------|--------|-----------|
| 19 | **Daemon failover / hot standby** — second staking node, auto‑promote on outage; protects the only real yield source | §9 health, `mn2_enable_staking.py` | L | double‑spend/stake conflict; strict single‑active lock |
| 20 | **Hot/cold sweep automation** — keep only a float hot, sweep surplus to cold at thresholds | RPC + ops | M | key custody; manual confirm above cap |
| 21 | **Withdrawal anomaly detection** — velocity/new‑device/large‑amount scoring → step‑up verify or hold | §9.2 gates, security svc | M | false positives; tunable thresholds |
| 22 | **Step‑up auth on risky actions** — email/2FA challenge on first new‑address withdraw or > threshold | account security svc | M | UX friction; only above risk score |
| 23 | **Tax/accounting export** — year‑end statement + Koinly/CoinTracker CSV from §15 + ledger | §15 CSV, ledger | S | tax‑advice optics; "informational, not advice" |
| 24 | **Agent strategy marketplace** — users pick a vetted staking‑bot persona (§19) to manage their stake within policy caps | §19 agents | L | misaligned bots; sandbox + caps + kill switch |
| 25 | **Rig integrity / anti‑abuse v2** — proof‑of‑work challenge in the rig worker + server attestation to deter fake uptime farms | §3 rig, work proof | M | arms race; keep weighting capped so abuse ≈ low value |

---

## 21. Top 10 to implement next (re‑thought 2026‑06‑04)

Curated from §20 for **value ÷ (effort × risk)**, sequenced so trust/transparency and security land before growth levers that increase exposure. Verdict: ✅ do next · 🟡 do guarded.

| Rank | Idea (§20 #) | Why now | Effort | Verdict |
|------|--------------|---------|--------|---------|
| 1 | **Proof‑of‑reserves + realized‑yield report** (#11, #12) — **✅ SHIPPED 2026‑06‑04** | Trust foundation; turns the §8 reconcile + §9 health we already built into a public, regulator‑friendly artifact; prerequisite for scaling deposits | M | ✅ done |
| 2 | **Staking dashboard charts** (#1) — **✅ SHIPPED 2026‑06‑06** | Highest user‑visible value, near‑zero risk; §15 data already exists, just needs a view | M | ✅ done |
| 3 | **Withdrawal anomaly detection + step‑up** (#21, #22) — **✅ SHIPPED 2026‑06‑06** | Directly extends the §9.2 hardening; with the allowlist now off, this is the smart risk control that scales | M | ✅ done |
| 4 | **Personal audit log + tax export** (#14, #23) — **✅ SHIPPED 2026‑06‑07** | Cheap, compliance‑positive, leans on `mn2_ledger` + §15 CSV; pairs with #1 | S | ✅ done |
| 5 | **Reward notifications & weekly digest** (#2) | Retention engine; low effort over existing accrual cron | S | ✅ |
| 6 | **Gift / internal MN2 transfer** (#15) | Engagement + viral seeding of new wallets; reuses ledger + hold gate | M | 🟡 (KYC + caps + audit) |
| 7 | **Public leaderboard + share cards** (#6, #10) | Growth flywheel once #1/#3 make exposure safe; opt‑in, amounts hidden | S | 🟡 (privacy opt‑in) |
| 8 | **Withdrawal address book** (#5) | UX relief for the 2h cooldown we just shipped; trusted‑address management | M | 🟡 (step‑up to add) |
| 9 | **Daemon failover / hot standby** (#19) | Protects the single real‑yield source; reliability debt worth paying before volume grows | L | 🟡 (strict single‑active lock) |
| 10 | **Goal planner + fiat toggle** (#3, #4) | Polishes the wallet; pure reuse of §6 calculator + §16 price | S | ✅ |

### 21.1 #1 Proof‑of‑reserves — shipped (2026‑06‑04)
- **Service:** `backend/services/mn2_proof_of_reserves_service.py` — `proof_of_reserves()` (on‑chain custodial assets via `getwalletinfo`/`getbalance` + stabilization reserve vs Σ user liquid+staked liabilities read straight from the file‑backed points store; coverage ratio; reconcile verdict gates the "fully backed" claim) and `yield_report()` (lifetime realized yield vs rewards paid vs site margin, plus per‑day from `mn2_staking_rewards.jsonl`). Short TTL cache so the public page can't hammer RPC.
- **API (public):** `GET /api/mn2/staking/proof-of-reserves` and `GET /api/mn2/staking/yield-report` (`?force=1` bypasses cache).
- **Page:** `/proof-of-reserves/` (registered in `all_page_routes.py` PAGES); green/amber/red banner driven by coverage + reconcile + on‑chain reachability.
- **Treasury funding (new ops tool):** `POST/GET /api/mn2/ops/treasury-address` (ops‑secret) → fresh daemon‑wallet address recorded in `data/mn2_treasury_addresses.json`. **Not** added to the deposit‑scanner map, so funding it raises reserves WITHOUT creating a user liability — the correct way to back existing in‑app balances. (Do **not** fund deposit‑pool addresses for this — the scanner would credit them to an account and liabilities would rise in lockstep.)
- **First run finding:** liabilities ≈ 812,955 MN2 across 4 holders vs ≈ 1 MN2 on‑chain — the large in‑app balances were unbacked. Resolution chosen: fund the treasury address (~855k MN2) to reach coverage ≥ 1.0.

### 21.2 #2 Staking dashboard charts — shipped (2026‑06‑06)
- **Where:** the wallet staking card (`profile/index.html`, `#profile-mn2-staking-card`), new "Earnings dashboard" block above the reward‑history table.
- **What:** two dependency‑free `<canvas>` charts in `static/js/mn2-staking.js` — (1) cumulative earnings (actual line + dashed projected‑trend line at the average per‑interval reward), (2) per‑interval reward bars — plus a legend with intervals/total/avg/avg‑APR. DPR‑aware crisp rendering, redraws on resize, shows an empty state until the first accrual.
- **Bugfix:** the reward history fetched a malformed URL (`rewards-table&limit=25` with no `?`), so it silently 404'd; now `?limit=200` and the table shows the latest 25.

### 21.3 #3 Withdrawal anomaly detection + step‑up — shipped (2026‑06‑06)
- **Service:** `backend/services/mn2_withdrawal_risk.py` — `assess(user_id, address, amount, balance, config)` scores ledger‑derived signals (new payout address, large absolute amount, ≥X% of balance, withdrawal velocity in a window) into `low | elevated | high`; every assessment is appended to `logs/mn2_withdrawal_risk.jsonl`.
- **Route integration:** `mn2_withdraw` now, after the balance check, requires a fresh password verification token on `elevated`/`high` risk **even if the user turned real‑money protection off** (`code: step_up_required`); `high` risk on a password‑less account is blocked with advice to set one (`code: risk_blocked`). Fail‑open on service error.
- **Helpers:** added `account_security_service.verify_action_token()` + `has_password()` (public) so step‑up can enforce regardless of the user's `require_password_real_money` setting.
- **Config:** `withdrawal_risk` block in `data/mn2_config.json` (enabled, `step_up_score`, `block_score`, `large_amount_mn2`, `large_balance_fraction`, `velocity_window_minutes`, `velocity_count_threshold`).
- **Ops:** `GET /api/mn2/ops/withdrawal-risk?limit=&min_level=` (ops‑secret) to review recent flagged attempts.

### 21.4 #4 Personal audit log + tax export — shipped (2026‑06‑07)
- **Route:** `GET /api/mn2/statement` (server‑resolved identity only; `401 auth_required` for guests). Walks the user's full `mn2_ledger` chronologically, assigns each event a signed `delta_mn2` (inflow: `deposit`, `staking_reward`, `onramp_purchase`, `unstake`, `p2p_buy`, `p2p_escrow_return`; outflow: `withdrawal`, `shop_payment`, `onramp_clawback`, `stake`, `p2p_sell_escrow`) and a derived `running_balance_mn2`. Returns rows (newest‑first), `current_balance_mn2`, and `summary.by_type` + `summary.by_year` (inflow/outflow/net/events). `?year=YYYY` filters rows; `?format=csv` returns `mn2_statement_<year>.csv` (chronological) for accounting/tax import. Includes a "not tax advice / derived view" disclaimer.
- **Privacy hardening:** `GET /api/mn2/transactions` switched from `from_query=True` to server‑resolved identity so a caller can no longer read another account's ledger via `?user_id=`.
- **UI:** profile MN2 wallet card gains a "Statement & tax export" block — year selector (auto‑populated from `by_year`), CSV export link (year‑aware), current‑balance/event summary, and a date/type/change/running‑balance table.

**Sequencing:** Wave 1 (trust + safety): #1, #3, #4 — make the system provably honest and safe with withdrawals open to all. Wave 2 (delight + retention): #2, #2(dash), #10. Wave 3 (growth): #6, #7, #8. Wave 4 (scale infra): #9. **Deferred from §20:** teams (#7‑pools), seasonal prizes (#8), VIP/Pro subscription (#16, #18), treasury automation (#17, #20), agent marketplace (#24) — revisit after Wave 1–2 prove the books and the audits hold.

> **Decisions carried forward:** still **no** locked vaults, **no** staking↔casino financial coupling, **no** selling yield (the Pro subscription #18 sells analytics, never returns). New money‑movement features (#15 gift, #6 leaderboard exposure) ship **only after** the proof‑of‑reserves page (#1) is live and reconcile is green.
