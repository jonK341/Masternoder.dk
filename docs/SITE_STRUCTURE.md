# Site structure — domain paths and filesystem layout

**Goal:** Clean project root, predictable URLs on `masternoder.dk`, one deploy path.

---

## Domain URL map (public)

| URL | Serves | Filesystem |
|-----|--------|------------|
| `/` | Home page | `site/index.html` |
| `/generator/`, `/battle/`, `/shop/`, … | Feature pages | `site/pages/<name>/index.html` |
| `/static/css/…`, `/static/js/…` | Assets | `site/static/` |
| `/api/health`, `/api/battle/stats`, … | JSON APIs | `backend/routes/` (Flask) |
| `/dashboard/master_control/` | Admin dashboards | `site/pages/dashboard/…` |
| `/vidgenerator/*` | **301/308 redirect** → `/*` | (no files — legacy bookmarks) |

### Page categories (navigation grouping)

| Group | Pages | URL examples |
|-------|-------|----------------|
| **Create** | generator, gallery, editor, podcast | `/generator/`, `/gallery/` |
| **Play** | game, battle, casino, battlegrounds, champions-league | `/game/`, `/battle/` |
| **Account** | profile, user, trophies, shop | `/profile/`, `/shop/` |
| **Platform** | lab, debugger, aggregator, agents, command-center | `/lab/`, `/debugger/` |
| **Economy** | exchange, market, profit, monetization, proof-of-reserves | `/exchange/`, `/market/` |
| **Content** | compendium, news, quests, social | `/compendium/`, `/news/` |

URLs stay flat at the domain root (`/generator`, not `/pages/generator`). The `site/pages/` folder is filesystem-only.

---

## Project root layout (after reorganization)

```
/workspace/                    # deploy root → /var/www/html/
├── wsgi.py                    # uWSGI entry
├── run.py                     # local dev
├── deploy.py                  # SFTP deploy
├── uwsgi.ini, requirements*.txt
├── src/                       # Flask app factory
├── backend/                   # routes + services
├── site/                      # ★ all web-facing files
│   ├── index.html             # /
│   ├── service-worker.js
│   ├── static/                # → /static/
│   └── pages/                 # → /<page>/
│       ├── generator/
│       ├── battle/
│       └── …
├── data/                      # JSON configs
├── scripts/                   # ops + deploy helpers
├── deploy/nginx/              # version-controlled nginx template
├── docs/                      # documentation
├── tests/
└── vidgenerator/              # legacy: python_proxy + calculator src only
```

### What stays out of `site/`

| Path | Why |
|------|-----|
| `backend/`, `src/` | Python application code |
| `data/`, `instance/` | Runtime data / SQLite |
| `scripts/`, `docs/` | Not served to browsers |
| `videos/` | Generator output (served via API, not static tree) |

---

## Deploy checklist

1. Upload code: `python deploy.py` or `python scripts/deploy_all_and_restart_uwsgi.py`
2. Ensure nginx proxies `/` → `127.0.0.1:5000`: `python scripts/fix_nginx_root_proxy.py`
3. Restart app: `sudo systemctl restart uwsgi-vidgenerator`
4. Verify: `curl -s https://masternoder.dk/api/health`

---

## Adding a new page

1. Create `site/pages/my-feature/index.html`
2. Add `'my-feature'` to `PAGES` in `backend/routes/all_page_routes.py`
3. Deploy and test `https://masternoder.dk/my-feature/`

Use absolute paths in HTML: `/static/css/…`, `/api/…`, `/other-page/`.

---

## Legacy `/vidgenerator/` prefix

Old links and bookmarks use `/vidgenerator/generator`, `/vidgenerator/api/…`, etc.

Flask returns **301** (pages) or **308** (API, preserves POST) to the root path.  
**Do not** create new links with `/vidgenerator/` — use root URLs only.

See also: `docs/DEPLOYMENT_PLAN.md` §6.
