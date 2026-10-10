# Server vs Local Comparison & Deploy Summary

**Date:** 2026-02-18

---

## File Comparison Results (before deploy)

Run: `python scripts/compare_server_local_files.py`

| Finding | Count |
|---------|-------|
| Total compared | 23 |
| Missing on server | 5 (register_intelligence package) |
| Missing locally | 0 |
| Size differences | 9 |

### Files that were missing on server (now deployed)
- `backend/services/register_intelligence/__init__.py`
- `backend/services/register_intelligence/route_discovery.py`
- `backend/services/register_intelligence/frontend_api_scanner.py`
- `backend/services/register_intelligence/orchestrator.py`
- `backend/services/register_intelligence/missing_route_resolver.py`

### Size differences (local had newer content)
- `src/app/__init__.py`, `backend/route_loader.py`, `backend/middleware/auto_fix_404_middleware.py`
- `vidgenerator/lab/index.html`, `unified-generator-battle.js`, `trigger-based-actions.js`
- `video_generator_service.py`, `generator_context_service.py`, `content_categories.json`

---

## Deploy Completed

- **35 files uploaded** including register_intelligence, path_mappings fix, and all route/generator files
- **ensure_flask_routes_registered** ran (sets PYTHONPATH for python-proxy and uwsgi-vidgenerator)
- **Services restarted:** python-proxy, uwsgi-vidgenerator, uwsgi, nginx

---

## Verify Routes on Production

```bash
# Test generator endpoints
curl -s -o /dev/null -w "%{http_code}" https://masternoder.dk/vidgenerator/api/generator/test
curl -s -o /dev/null -w "%{http_code}" https://masternoder.dk/vidgenerator/api/unified/status
curl -s -o /dev/null -w "%{http_code}" https://masternoder.dk/vidgenerator/api/monetization/top-50
```

Or run: `python scripts/hard_test_generator_urls.py --quick`

---

## Generator Buttons

- **AI Clip Generator** – short clips via `/api/generator/ai-clips`
- **Video Generator** – full documentaries via `/api/unified/generate-video`
- **Magic Generate** – 1-click video via `/api/generator/magic-generate`

See `docs/GENERATOR_BUTTONS_DECISION.md` for details.
