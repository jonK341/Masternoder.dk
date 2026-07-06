# Profit Daemon — Laptop Control App: Function Split & Migration Plan

Status: security groundwork implemented (owner/public status split, header-only
admin auth, instance registry with double-tick detection). This document is the
contract for building the laptop control app and for deciding what stays on the
web.

## 1. Principle

The web stays the **public window** (monitoring, marketing, marketplace).
The laptop app becomes the **owner console** (control, money, secrets).
Anything that can move money, change trading behavior, or reveal balances is
owner-only and belongs in the laptop app (or Business Control as the web
fallback), authenticated with `X-Exchange-Admin-Key`.

## 2. Function split

### Stays on the web — public, no auth

| Function | Endpoint | Notes |
|---|---|---|
| Daemon health (online, loop ages, mode, profile) | `GET /api/profit-daemon/status` (public view) | Sanitized: no balances, payout amounts, treasury, host, instance detail |
| Profit readiness + blockers list | same | Titles only |
| Profit news feed | `GET /api/profit-daemon/news` | Already public by design |
| Daemon rentals catalog | `GET /api/profit-daemon/rentals` | Marketplace content |
| Critical top-25 read | `GET /api/exchange/profit-path/critical-top25` | Read-only |

### Moves to the laptop app — owner-only (admin key header)

| Function | Endpoint | Why owner-only |
|---|---|---|
| Full status: venue balances, sweepable USD, treasury stash, host, server state | `GET /api/profit-daemon/status` (owner view) | Funding intelligence; tells attackers exactly what is where |
| Daemon instance list (hosts, PIDs, conflict detail) | `GET /api/profit-daemon/instances` | Infrastructure detail |
| Kill-switch / pause bots / supervisor | `POST /api/exchange/control-board/*` | Changes trading behavior |
| Manual tick / run-all bots | `POST /api/exchange/control-board/run` | Triggers live orders |
| PayPal sweep + payout config | `POST /api/exchange/payout/*` | Moves money |
| Secrets vault management | `/api/exchange/arbitrage/vault/*` | API credentials |
| Critical top-25 checklist writes | `POST /api/exchange/profit-path/critical-top25/check` | Gates the readiness score (now admin-gated) |
| Swap rotation / daemon mesh triggers | `POST /api/exchange/swap-rotation/execute`, `/api/exchange/daemon-mesh/run` | Live capital movement |

Business Control (`/business-control`) keeps working as the browser fallback
for all of the above — same key, same endpoints.

### Never over HTTP (laptop app shells out or SSHes)

- systemd start/stop of the daemon process (`systemctl … masternoder-profit-daemon`)
- `.env` editing, vault passphrase entry
- Deploys (`scripts/deploy_profit_daemon_server.py`)

Deliberately: an HTTP endpoint that can start/stop the daemon or edit env is a
bigger attack surface than the value it adds. The laptop app can wrap SSH for
these instead.

## 3. Auth model for the laptop app

- One shared secret: `EXCHANGE_ADMIN_KEY` (env on server, keychain/OS keystore
  in the laptop app — not sessionStorage, not plaintext config).
- Sent only as `X-Exchange-Admin-Key` header. Query-string keys are rejected
  server-side (they leak into access logs and Referer headers).
- Server compares with `hmac.compare_digest` (timing-safe) —
  `backend/services/exchange_admin_auth.py`.
- All owner endpoints already return 401 JSON on bad/missing key, so the app
  can key-gate on any 401.

Recommended app-side handling: prompt once, store in OS keychain, send per
request over HTTPS only, wipe on logout.

## 4. Running the daemon on the laptop (migration / merge)

The daemon stack runs identically on the laptop (`run_daemons.cmd`,
`python scripts/all_profit_daemons.py`) and the server (systemd). The danger
when moving between them is **both running at once** — duplicate live orders
and duplicate PayPal sweeps against the same venue accounts.

Protection now built in:

1. Every daemon instance registers itself on each heartbeat
   (`data/crypto_exchange/profit_daemon_instances.json` via
   `profit_daemon_instance_service`).
2. A laptop instance also reports to the server when
   `PROFIT_DAEMON_REPORT_URL` (+ `EXCHANGE_ADMIN_KEY`) is set in the laptop
   `.env`: `POST /api/profit-daemon/heartbeat` (admin-gated).
3. `monitor_status()` exposes `daemon_instances` with
   `active_count` and a `conflict` flag when >1 instance is alive inside the
   stale window. The `/profit/` page shows a red warning bar; the laptop app
   should refuse to start live mode while `conflict` or while another live
   instance is active (`GET /api/profit-daemon/instances`).

Migration checklist (server → laptop, or laptop → server):

1. `systemctl stop masternoder-profit-daemon` (or Ctrl+C the laptop daemon).
2. Wait one stale window (`PROFIT_DAEMON_STALE_SEC`, default 300s) or check
   `GET /api/profit-daemon/instances` shows 0 active.
3. Start the daemon on the new machine.
4. Verify exactly one active instance and `conflict: false`.

## 5. What the laptop app should implement (v1)

1. Status dashboard — poll owner `GET /api/profit-daemon/status` (full view).
2. Instance panel — `GET /api/profit-daemon/instances`, red banner on conflict.
3. Kill-switch + pause/resume — existing control-board endpoints.
4. Payout panel — payout status + manual sweep with confirm dialog.
5. Local daemon runner — wrap `python scripts/all_profit_daemons.py` with
   `PROFIT_DAEMON_REPORT_URL` set, refuse live mode when another live instance
   is active.
6. Secrets: admin key in OS keychain; venue keys stay in the encrypted vault
   on whichever machine runs the daemon.

### Status: shipped (v1)

The v1 app lives in `laptop-app/` (Electron). All six items above are
implemented:

- Connection gate validates the admin key against the owner API before
  entering; key stored via `safeStorage` (OS keychain), header-only transport,
  kept in the main process (never in the renderer).
- Status dashboard, instances panel with conflict banner, kill-switch + run
  tick, payout status + confirmed sweep, and a local daemon runner that refuses
  to start live while a live instance is active on the server.
- `contextIsolation` on, `nodeIntegration` off, strict CSP, minimal
  `contextBridge` surface. See `laptop-app/README.md` to run it.
- Not yet done: signed installers (add `electron-builder`), packaging, and
  auto-update. Tracked as follow-ups.

## 6. Security changes shipped with this plan

- `GET /api/profit-daemon/status` is now split: public = sanitized
  (no Binance/NonKYC balances, no sweepable USD, no treasury stash, no host,
  no server state), owner = full payload via admin key.
- `POST /api/exchange/profit-path/critical-top25/check` now requires the
  admin key (was unauthenticated write).
- Admin key accepted from headers only; `?admin_key=` query support removed.
- Timing-safe key comparison, centralized in `exchange_admin_auth.py`.
- New admin-gated endpoints: `POST /api/profit-daemon/heartbeat`,
  `GET /api/profit-daemon/instances`.
