# MN2 Private Control — Upgrades (50)

Every item below is implemented in this app (backend `trader_app/app.py`, `intelligence.py`,
`store.py`; UI `templates/dashboard.html`; build `build_exe.*`).

## Build & packaging
1. Fix `error: externally-managed-environment` (PEP 668) — build inside a dedicated venv.
2. `build_exe.sh` one-command Linux/macOS build (bootstraps `.build-venv`).
3. `build_exe.bat` one-command Windows `.exe` build.
4. Build venv is reused across runs (faster rebuilds).
5. README: `apt install python3-venv python3-full` guidance for Debian/Ubuntu.
6. README: documented `--break-system-packages` fallback.
7. `.gitignore` for build artifacts (`.build-venv/`, `dist/`, `build/`, `*.spec`).
8. PyInstaller onedir bundle with templates + config JSONs + hidden imports.

## App infrastructure
9. Owner-only **passcode** lock screen (`TRADER_PASSCODE`).
10. Logout / lock action.
11. Frozen-mode template path fix (works inside the packaged binary).
12. Per-tab lazy data loaders (only fetch the active tab).
13. **Auto-refresh** interval selector (3s / 5s / 10s / pause).
14. **Dark/light theme** toggle (persisted in localStorage).
15. **Keyboard shortcuts** 1–7 to switch tabs.
16. Header **health dot** (site reachability via `/api/health`).
17. Per-panel **last-updated** timestamps.

## Overview tab
18. **Equity/PnL sparkline** (canvas) rendered from history.
19. PnL/equity **history store** (`store.py`, JSONL, auto-trimmed).
20. Throttled **snapshot recording** on each overview poll.
21. **CSV export** — equity history (`/api/export/history.csv`).
22. **CSV export** — positions (`/api/export/positions.csv`).
23. **Sortable** balances / positions / signals tables (click headers).
24. Total balance KPI · 25. Realized PnL KPI (color-coded) · 26. Projected/day KPI.

## Trading tab
27. Signal **search/filter** box.
28. **Min-bps filter** control.
29. **AI recommendations** table with strong/consider/skip labels + reasons.
30. **Forum-intelligence** sentiment nudge in recommendation scoring.
31. Expected-per-cycle + **projected daily** profit per recommendation.
32. **Grid config editor** (levels, step, size, max-inventory, loss-cap, assets).
33. **Save config** from the UI (`/api/config/save`).
34. Preset — **Conservative** · 35. Preset — **Balanced** · 36. Preset — **Aggressive**.
37. **Kill** button (disable grid bot) · 38. **Run tick** button · 39. **Enable/Disable** toggle.

## Profit Monitor (AI) tab
40. **AI profit summary** — "where your profit is" (heuristic, optional LLM hook).
41. Realized + **projected/day** + **projected/month** headline figures.
42. **Profit-sources** table combining trades + signals into projected profit.
43. **Profit goal** input + progress bar in the header.

## Controls / Shop / Accounting
44. **Run all bots** (site proxy) · 45. **Daemon tick** (site proxy) · 46. **Kill switch** (site proxy).
47. **Agents Live Watch** panel.
48. **Shop flow** snapshot panel (site admin proxy).
49. **Accounting** tab — grid realized PnL + payout/treasury/fiat valuation.

## Alerts & Security
50. **Alerts** system: bell with count, recent-alerts panel, **browser notifications**, and
    automatic alerts on grid **halt** / **kill** / config changes — plus a **Security** tab
    (passcode status, default-passcode warning, admin-key presence, live-gate on/off, hardening tips).
