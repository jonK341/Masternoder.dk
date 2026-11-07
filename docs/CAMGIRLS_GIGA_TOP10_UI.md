# Camgirls Giga UI — Top 10 intelligence upgrades

Ten front-end upgrades shipped with `camgirls-giga-top10.css` + `camgirls-giga-intel.js` and `GET /api/camgirls/intel/top10`.

| # | Upgrade | Tech |
|---|---------|------|
| 1 | **Giga hero command center** | Live telemetry from intel API (roster, agents, scale %) |
| 2 | **Top 10 intelligence board** | Neural score rank + per-row tech chips |
| 3 | **Spotlight carousel** | Top 3 hosts with portrait hero |
| 4 | **Neural vibe filters** | Cosmic / Studio / Signal / Legacy grid filter |
| 5 | **Holographic cards** | Glass panels, hover lift, rank badges |
| 6 | **Intel ticker** | Marquee of platform intelligence stack |
| 7 | **Command palette** | `⌘K` / `Ctrl+K` jump to performer |
| 8 | **Roster orbital ring** | SVG progress toward 250 target |
| 9 | **Agent constellation copy** | Top 10 panel links performers → agents |
| 10 | **MN2 mesh rail** | Per-card agent / MN2 / wallet audit chips |

## API

`GET /api/camgirls/intel/top10` — returns `top10[]` with `score`, `vibe`, `technologies`, `intel_summary`, plus `scale` and `intel_stack`.

## Studio themes (5 palettes)

Sticky **Theme** dock: **Cosmic** (default), **Velvet**, **Signal**, **Aurora**, **Champagne** (light). Persists in `localStorage` (`cg_studio_theme_v1`). Styles split across:

- `static/css/camgirls-themes.css` — tokens + dock + `data-cg-theme` overrides
- `static/css/camgirls-studio-base.css` — catalog cards, chat, studio controls (replaces inline CSS in `camgirls/index.html`)
- `static/css/camgirls-giga-top10.css` — intel layer (uses shared tokens)

Early boot script in `camgirls/index.html` sets `html.cg-giga[data-cg-theme]` before paint. JS: `static/js/camgirls-themes.js`.

## Deploy

Included in `python scripts/deploy.py camgirls` manifest (CSS, JS, `camgirls_ui_intel_service.py`).
