# Star Map 25 upgrade — finish & deploy

**Status:** Complete. Use this doc to verify the upgrade and deploy the files.

---

## 1. What was delivered

| Deliverable | Location | Purpose |
|-------------|----------|--------|
| **50 implementation projects** | `docs/STARMAP_25_50_PROJECTS.md` | Backlog: data, API, UI, 3D, shop, trophies, analytics, agent tools |
| **50 projects × agent mapping** | `data/starmap25_agent_projects.json` | Each project has `task_id`, `description`, `suggested_agent` (content_generator_agent, learning_agent, analytics_agent) |
| **Assign 50 to agents** | `POST /api/debugger/tasks/assign-starmap50` | Assigns all 50 projects to the three agents by suggested_agent |
| **Assign 25/50 via rulebook** | `POST /api/debugger/tasks/assign-rulebook-todo` | Body `{ "only_starmap25": true, "use_starmap50": true }` or `max_tasks: 50` uses 50-project list |
| **Generator UI** | `generator/index.html` | Button “Assign 50 Star Map projects to agents” calls assign-starmap50 |
| **Backend loader** | `backend/routes/debugger_agent_tasks_routes.py` | `_load_starmap50_projects()`, `assign_starmap50()`, extended `assign_rulebook_todo` |

---

## 2. Deploy manifest (starmap25)

Deploy with:

```bash
python scripts/deploy.py starmap25
```

Or full deploy then restart:

```bash
python scripts/deploy_all_and_restart_uwsgi.py --manifest starmap25
```

**Manifest includes:**  
`starmap25/index.html`, `generator/index.html`, `backend/routes/star_map_routes.py`, `backend/routes/debugger_agent_tasks_routes.py`, `data/star_map_25.json`, `data/starmap25_agent_projects.json`, `data/star_map_25_investigations.json` (if present), and docs.

---

## 3. Post-deploy checklist

- [ ] **Monitor page** — Open `/starmap25/` (or `/vidgenerator/starmap25/`). Grid loads, progress X/25 and points shown.
- [ ] **API** — `GET /api/star-map/25` returns 25 points; `GET /api/star-map/25/status?user_id=default_user` returns `investigated_ids`, `total_points_earned`.
- [ ] **Investigate** — `POST /api/star-map/25/investigate` with `{ "user_id": "test", "point_id": "terra_sol" }` returns success and awards points once.
- [ ] **Generator** — Open `/generator/`. Click “Assign 50 Star Map projects to agents”; status shows “Assigned 50 Star Map projects to content_generator_agent, learning_agent, analytics_agent”.
- [ ] **Assign 25** — “Assign 25 tasks to agents” still works (rulebook + starmap25 mix or starmap-only with `only_starmap25` + `use_starmap50`).

---

## 4. Files touched (for deploy)

| File | Role |
|------|------|
| `starmap25/index.html` | Star Map 25 monitor UI |
| `generator/index.html` | Assign 25 + Assign 50 Star Map buttons |
| `backend/routes/star_map_routes.py` | Star Map 25 API |
| `backend/routes/debugger_agent_tasks_routes.py` | assign-starmap50, _load_starmap50_projects, assign_rulebook_todo extended |
| `data/star_map_25.json` | 25 points source of truth |
| `data/starmap25_agent_projects.json` | 50 projects + suggested_agent |
| `docs/STARMAP_25_50_PROJECTS.md` | 50-project spec |
| `docs/STARMAP25_UPGRADE_FINISH.md` | This finish doc |

---

## 5. Restart

After uploading, restart the app so new routes and logic load:

```bash
# On server
sudo systemctl restart uwsgi-vidgenerator
```

Or from deploy script: `python scripts/deploy_all_and_restart_uwsgi.py` restarts after upload.

---

*Star Map 25 upgrade finish. Deploy with `python scripts/deploy.py starmap25` or full deploy including starmap25.*
