# MN2 Private Control (laptop app)

A **private, passcode-gated** control panel + trading cockpit you run **on your own machine**
(whose IP can reach the exchanges — unlike the geo-blocked cloud host). It centralizes owner
controls and stats behind a lock screen, in a tabbed UI.

## Tabs
- **Overview** — balances per venue/pair, grid positions & PnL, cross-trade signals.
- **Trading** — bot enable/tick + **AI recommendations** (signals ranked by expected profit, nudged by forum-intelligence sentiment) with strong/consider/skip labels and reasons.
- **Profit Monitor (AI)** — an AI summary of *where your profit is*, realized + projected/day + projected/month, and a **profit-sources** table combining trades + signals.
- **Controls** — run/pause the site daemon & bots, agents (Live Watch) — proxied to the site admin API.
- **Shop** — shop-flow snapshot/controls (proxied to the site admin API).
- **Accounting** — grid realized PnL, payout/treasury/fiat valuation.
- **Security** — passcode-lock status, live-gate on/off, vault status, hardening tips.

## Run (from source)
```bash
pip install -r requirements.txt
export TRADER_PASSCODE='choose-a-strong-passcode'   # required to unlock (owner-only)
export SITE_URL=https://your-site.example            # site admin API for controls/signals
export SITE_ADMIN_KEY=<your exchange admin key>
export BINANCE_API_KEY=...  BINANCE_API_SECRET=...   # venue keys (or use the encrypted vault)
python trader_app/app.py                             # -> http://127.0.0.1:8800
```
Open http://127.0.0.1:8800, unlock with your passcode.

## Build a standalone executable

Use the bootstrap script — it creates a dedicated build venv, so it works even on
"externally-managed" systems (Debian/Ubuntu PEP 668, the `error: externally-managed-environment`):

```bash
# Linux / macOS
bash trader_app/build_exe.sh
```
```bat
REM Windows
trader_app\build_exe.bat
```

Output: `dist/MN2PrivateControl/`. Run `MN2PrivateControl` (`.exe` on Windows), open http://127.0.0.1:8800.

> **Do NOT `pip install pyinstaller` system-wide** on Debian/Ubuntu — that triggers
> `error: externally-managed-environment`. The scripts above avoid it by building inside
> `.build-venv`. If `python3 -m venv` fails, first run `sudo apt install -y python3-venv python3-full`.
> (Manual override alternative: `pip install --break-system-packages pyinstaller`, not recommended.)
>
> A **Windows `.exe` must be built on Windows** — PyInstaller does not cross-compile. Run the
> matching script on each target OS (verified on Linux; identical steps on Windows/macOS).

## Privacy / security
- The whole app is behind a **passcode** (`TRADER_PASSCODE`); set a strong one — the default
  `mn2-owner` is flagged insecure in the Security tab.
- All control/accounting data lives **in the app** and is fetched with your admin key; nothing
  private is exposed publicly by the app itself.
- Venue API keys should live in the encrypted vault (`EXCHANGE_VAULT_KEY`), not plaintext.

## Going live (real money)
Paper by default — nothing trades for real until you set **both** `EXCHANGE_ARBITRAGE_LIVE=1`
and `EXCHANGE_GRID_LIVE=1` and fund venue spot wallets. Risk is bounded by the grid config
(`data/exchange_grid_bot_config.json`): per-asset `max_inventory_usd` + global
`hard_loss_cap_usd` (auto-halts). Grid/MM books small wins in ranging markets and **loses in
trends** — risk-capped, not guaranteed profit; and cross-venue arbitrage is fee-dead at retail
size on these venues.

## Config file (optional, instead of env)
`trader_app/config.json`:
```json
{ "site_url": "https://your-site.example", "admin_key": "..." }
```
