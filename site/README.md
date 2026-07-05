# site/ — web-facing files

All browser-served HTML and static assets live here. **Public URLs stay at the domain root** (`/generator`, not `/site/pages/generator`).

| Path | URL |
|------|-----|
| `index.html` | `/` |
| `service-worker.js` | `/service-worker.js` |
| `static/` | `/static/` |
| `pages/<name>/` | `/<name>/` |

See `docs/SITE_STRUCTURE.md` for the full domain map.
