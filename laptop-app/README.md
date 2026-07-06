# Profit Daemon Control — Laptop App

Owner-only Electron desktop app for the MasterNoder profit daemon. It is the
laptop counterpart to the public `/profit/` web monitor: it shows the full
owner status, controls trading, sweeps payouts, and can run the daemon locally.

See `docs/PROFIT_DAEMON_LAPTOP_APP.md` in the repo root for the web-vs-laptop
function split, auth model, and migration plan.

## What it does

- **Connect** to your server with the owner admin key (`EXCHANGE_ADMIN_KEY`).
  The key is stored via Electron `safeStorage` (OS keychain on macOS/Windows,
  libsecret on Linux) and sent only as the `X-Exchange-Admin-Key` header. It is
  never written in plaintext and never enters the renderer process.
- **Status dashboard** — full owner view of `/api/profit-daemon/status`
  (daemon health, loops, readiness, auto-sweep).
- **Instances panel** — `/api/profit-daemon/instances` with a red conflict
  banner when more than one daemon instance is active (double-tick warning).
- **Controls** — kill-switch toggle and "run all bots once".
- **Payout** — payout status and a confirmed manual PayPal sweep.
- **Local daemon runner** — starts `scripts/all_profit_daemons.py` from your
  repo checkout with `PROFIT_DAEMON_REPORT_URL` + `EXCHANGE_ADMIN_KEY` set so
  this instance reports to the server. **Refuses to start live** while another
  live instance is already active on the server.

## Security model

- Admin key: OS keychain via `safeStorage`; header-only transport; kept out of
  the renderer (all API calls run in the main process over IPC).
- The server rejects query-string keys and compares timing-safely, so the key
  is only ever useful over HTTPS headers.
- Start the daemon in `paper` mode by default; `live` requires an explicit
  confirm and passes the server-side conflict gate.
- `contextIsolation` on, `nodeIntegration` off, a strict CSP, and a minimal
  `contextBridge` surface in `preload.js`.

## Run (development)

```bash
cd laptop-app
npm install
npm start
# On Linux containers without a sandbox namespace:
npm run start:nosandbox
```

Then enter your server URL (e.g. `https://your-server.example`) and the owner
admin key. For the local daemon runner, set "Repo root" to your local
repository checkout.

## Packaging

Not wired yet. Add `electron-builder` or `electron-forge` as a follow-up to
produce signed `.dmg` / `.exe` artifacts. The app has no runtime dependencies
beyond Electron, so packaging is straightforward.
