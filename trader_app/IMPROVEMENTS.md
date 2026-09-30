# MN2 Private Control — Improvement pass (per component)

A round of concrete, tested improvements across every component.

## Auth / login
1. Brute-force **lockout** — 5 failed passcodes per IP within 5 min blocks further attempts.
2. **Session auto-lock** — permanent session with an 8-hour lifetime.
3. **Cookie hardening** — `HttpOnly` + `SameSite=Lax`.
4. **Show-passcode** toggle on the lock screen.
5. Login **alerts** — successful unlocks and failed attempts are recorded (with attempts-left hint).

## Intelligence engine
1. **Confidence score** (0–100) from edge margin over the fee floor + forum signal.
2. **Monthly projection** (`projected_monthly_usd`) alongside per-cycle/daily.
3. **Risk flag** (low/medium/high) — flags illiquid venue routes (NonKYC/XeggeX).
4. **De-dup** — one row per (type, symbol), keeping the best edge.
5. **Input clamping** — order size, cycles, sentiment, mentions bounded to safe ranges.

## Grid bot
1. **Config validation/clamping** — levels, step, size, caps, min-notional forced into sane ranges.
2. **Min-notional guard** — never places orders below the venue minimum (skips dust).
3. **Peak PnL + max-drawdown** tracking per market.
4. Drawdown/peak surfaced in status + positions CSV.
5. (Existing safety retained: inventory cap + hard loss-cap auto-halt.)

## Store / history
1. **Equity stats** — peak, min/max, max-drawdown, net change from history.
2. **Alerts CSV** export.
3. Positions CSV now includes max-drawdown.
4. Bounded files with safe rotation.

## Overview tab
1. Sparkline **trend colouring** (green/red) + min/max/last **labels**.
2. Equity **Δ / peak / max-drawdown** shown by the chart.
3. **Warming** indicator while background data loads.
4. Per-panel freshness timestamp.
5. CSV export (equity, positions).

## Trading tab
1. Recommendations show **confidence** + **risk** + monthly.
2. **Persisted** search + min-bps filters (localStorage).
3. Buttons **disabled while in-flight** (no double-submit).
4. Sortable recommendation table.
5. Grid config editor with validated presets.

## Controls tab
1. **Confirmation dialogs** on destructive site actions (kill switch, run-all).
2. Buttons disabled while the action runs.
3. Recent **alerts** panel + CSV export.
4. Graceful "site unreachable" messaging.

## Profit Monitor / Accounting / Shop / Security
1. Monitor: monthly projection + confidence/risk in the AI summary and sources.
2. Accounting: grid realized + payout/treasury/fiat.
3. Shop: real site endpoints (analytics + payment/integration health) with per-block status.
4. Security: passcode/default/admin-key + live-gate rows + hardening tips.
5. Auto-refresh interval is **persisted** and applies across tabs.

## App infrastructure
1. **Non-blocking background cache** (fixes long load) — refresher thread; requests never wait on scans.
2. `config.json` loaded next-to-exe, embedded-in-exe, CWD, or source; env overrides.
3. Venue credentials from `.env`/config (`{VENUE}_API_KEY`) — enables NonKYC without the vault.
4. Health check cached + shown as a header status dot.
5. Keyboard shortcuts (1–7) + dark/light theme (persisted).
