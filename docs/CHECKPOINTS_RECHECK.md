# Checkpoints recheck – verified and enriched

**Purpose:** Single place to verify all previous work and see how to recheck or enhance each area.

**Quick recheck:** `python scripts/test_url_timing.py` (set `BASE_URL=https://masternoder.dk` for production).  
**After deploy:** `python scripts/deploy_all_and_restart_uwsgi.py --no-upload` (restart only) then run URL timing again.

---

## 1. RESEARCH_AI_SYSTEMS.md

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| §1–7 AI section titles | OK | — | Open doc, confirm "AI" in §1–7 headings | Doc has quick-reference box at top (see RESEARCH_AI_SYSTEMS.md) |
| §8 API provider links table | OK | High | Check table has links for all env vars; open one link | Each row: env, AI/brug, clickable link |
| §9 File reference | OK | Medium | Grep for llm_service, tts_service, agent_research | §9 table maps area → service + routes file |
| §10 Production & loading | OK | High | Run test_url_timing.py; read §10 for 404 fix list | §10 includes troubleshooting and CHECKPOINTS_RECHECK ref |
| §11 Optional API keys (easy add) | OK | Medium | Copy block from §11 into .env; uncomment one line | §11 references Agent Support → Resources |
| §12 Profile & AI connections | OK | Medium | From Profile click "API keys & support"; from Agents click "API keys & optional keys" | Flow diagram in §12 |
| §13 Videre research | OK | Low | Read §13 for next steps | §13 lists LLM, aggregator, tracker, video, profile↔agents |

**Verify:** `head -n 30 docs/RESEARCH_AI_SYSTEMS.md` and open §8 table.

---

## 2. .env and .env.example

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| .env top comment | OK | Medium | First comment in .env points to .env.example + §8 | — |
| .env provider link lines | OK | High | Inline links for LLM, Video, TTS, Auth, Optional | — |
| .env.example structure | OK | High | Sections: Flask, AI LLM, Video/Image, TTS, Auth, Storage, Optional, Notifications | .env.example has "Quick start" hint at top |
| .env.example per-var links | OK | High | Each main var has `# https://...` above or beside | — |
| Optional easy-add block | OK | Medium | Block has 6+ optional vars with inline links | Comment says "Get keys: Profile → Agent Support → Resources" |

**Verify:** `grep -n "API_KEY\|# https" .env.example | head -40`

---

## 3. Agent skillset (new agents with AI skills and styles)

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| New agents in _default_skillsets | OK | High | Backend loads; GET /vidgenerator/api/agent-skillset/all returns agents | 9 AI-focused agents: LLM Orchestrator, Video AI, TTS Narration, Intelligence Aggregator, Agent Research Tracker, Content AI, Security Audit, Performance, Support Ticket |
| style / accent_color / design | OK | Low | In agent_skillset.py search for "style": "neon" etc. | Each new agent has distinct style (neon, cinema, warm, dashboard, dark, creative, alert, speed, friendly) |
| Attached to profiles | OK | High | Profile page "My Agents" loads; agents page shows list | user_agent_skills + agent_skillset back profile and agents UI |

**Verify:** `curl -s https://masternoder.dk/vidgenerator/api/agent-skillset/all | python -m json.tool | head -80`

---

## 4. add_agent_skill_sets_to_pages.py (enhanced)

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| Scope | OK | Medium | `python scripts/add_agent_skill_sets_to_pages.py --dry-run` (default: vidgenerator) | Use `--all-pages` to include full project |
| Options | OK | Medium | `python scripts/add_agent_skill_sets_to_pages.py --help` | Version, defer, media, backup, report path |
| Report | OK | Low | After run: `type logs\add_agent_skill_sets_report.json` | JSON has updated_count, skipped_count, error_count, options |
| data-agent-skill-sets | OK | Low | In modified HTML, `<html` has `data-agent-skill-sets="enriched"` | — |
| Backup | OK | Low | Run with `--backup`; check `logs/agent_skill_sets_backup/<ts>/` | — |

**Verify:** `python scripts/add_agent_skill_sets_to_pages.py --dry-run` then inspect report.

---

## 5. deploy_all_and_restart_uwsgi.py

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| Deploy all files | OK | High | `python scripts/deploy_all_and_restart_uwsgi.py --dry-run` (lists files) | Use `--manifest profile loading` to deploy only those |
| Stop uwsgi, record time | OK | High | Script stops uwsgi first; uwsgi_stopped_at used for grace period | — |
| Wait ≥5s before freeing port | OK | High | UWSGI_OFF_GRACE_SECS = 5; if elapsed < 5, script waits | Ensures gunicorn is killed only after grace period |
| Kill gunicorn on 5000 | OK | High | After wait: stop vidgenerator-gunicorn, pkill gunicorn, then fuser/kill :5000 | — |
| Start uwsgi, verify :5000 | OK | High | systemctl start uwsgi; curl :5000; nginx reload | — |

**Verify:** After deploy, run `python scripts/test_url_timing.py` with BASE_URL to production.

---

## 5b. URL timing 404s – investigation and fallbacks

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| 404 cause | OK | High | Production 404s usually mean dedicated blueprints not registered or old code on server | Routes exist in battle_routes, user_account_routes, user_profile_routes, gallery_routes, trophies_routes, agent_automation_routes |
| Fallbacks | OK | High | `missing_endpoints_routes.py` registers first and has fallbacks for all URL-timing endpoints | Front page init, battle/stats, agent-skillset/all, profile/aggregated, user/identity, account-summary/points, gallery/recent-temp, trophies/list, battle/pvp/trophies |
| Deploy order | OK | Medium | Deploy `backend/routes/missing_endpoints_routes.py` so fallbacks are active | Full deploy includes it; after deploy, run test_url_timing.py again |

**Verify:** Run `python scripts/test_url_timing.py`; if 404s persist, the app process may be using cached code. Run full deploy (`python scripts/deploy_all_and_restart_uwsgi.py`) or on server: `systemctl stop uwsgi uwsgi-vidgenerator python-proxy; sleep 5; systemctl start uwsgi uwsgi-vidgenerator python-proxy`.

---

## 6. Agent Support (backend + UI)

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| ai_api_providers | OK | High | Open /vidgenerator/agent_support → Resources tab | 13 providers with name, link, env; includes optionals |
| useful_docs | OK | Medium | Resources tab "Useful links" section | PayPal, GitHub OAuth, arXiv; doc links to CHECKPOINTS_RECHECK and RESEARCH_AI_SYSTEMS |
| api_endpoints | OK | Low | Listed under API Endpoints | Full /vidgenerator/api/ paths |
| tools | OK | Low | Debugger, AI Agents, Aggregator (internal links) | — |
| get_support_resources merge | OK | High | Old support.json still gets ai_api_providers from defaults | Merge keeps defaults for ai_api_providers, useful_docs if saved empty |
| renderResources | OK | High | All four sections render; no "No resources" when backend OK | Handles both object and legacy string format for tools/docs |

**Verify:** Open https://masternoder.dk/vidgenerator/agent_support → Resources. Check "AI API providers" and "Useful links".

---

## 7. Navigation and UI links

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| Victory/Danish Tech Tree removed | OK | Low | Nav toolbar has no these entries | — |
| Agent Support title | OK | Low | Hover Agent Support in nav: "Tickets, AI API keys, tools" | — |
| Profile My Agents links | OK | High | Profile → My Agents card: Full Agent Report, Agent skills, API keys & support | Three links present; API keys & support goes to agent_support |
| Agents page Connections | OK | High | Agents page: Connections strip with Profile, API keys & optional keys, Debugger | Short description text for "why" these links |

**Verify:** Click Profile → My Agents; click Agents → Connections. All links reach correct pages.

---

## 8. URL timing (production)

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| Front page URLs | Partial | High | 3/6 return 200 (init, battle, agent-skillset → 404) | test_url_timing.py prints OK/FAIL and time per URL |
| Profile URLs | Partial | High | 9 OK, 9 FAIL (see §9) | Bind session OK; Profile aggregated, User identity, Account summary, Gallery, Trophies, Battle PVP → 404 |
| 404 deploy checklist | OK | High | After run: `logs/production_404_deploy_checklist.txt` | Lists endpoint → suggested route file |
| test_url_timing.py | OK | High | Results in logs/url_timing_results.json | Script documents FRONT_PAGE_URLS and PROFILE_PAGE_URLS in comments |

**Verify:** `python scripts/test_url_timing.py` (optionally `set BASE_URL=https://masternoder.dk`). Check exit code and printed Failed list. Current: 9 OK, 9 Failed.

---

## 9. Production 404s (action needed)

| Endpoint | Fix | Route file / note |
|----------|-----|-------------------|
| **Front page init** | Register route for GET `/vidgenerator/api/frontpage/init` | backend/routes/missing_endpoints_routes.py |
| **Battle stats** | Register route for GET `/vidgenerator/api/battle/stats` | backend/routes/battle_routes.py |
| **Agent skillset all** | Register route for GET `/vidgenerator/api/agent-skillset/all` | backend/routes/agent_automation_routes.py |
| **Profile aggregated** | Register route GET `/vidgenerator/api/user/profile/<user_id>/aggregated` | user_profile_routes.py; check register_blueprints.py |
| **User identity** | Register route for GET `/vidgenerator/api/user/identity` | backend/routes/user_account_routes.py |
| **Account summary points** | Register route for GET `/vidgenerator/api/user/account-summary/points` | backend/routes/user_account_routes.py |
| **Gallery recent** | Register route GET `/vidgenerator/api/gallery/recent-temp` | backend/routes/gallery_routes.py |
| **Trophies list** | Register route for GET `/vidgenerator/api/trophies/list` | backend/routes/trophies_routes.py |
| **Battle PVP trophies** | Register route for GET `/vidgenerator/api/battle/pvp/trophies` | backend/routes/battle_routes.py |

**Enrichment:** See RESEARCH_AI_SYSTEMS.md §10 (Production & loading) and PAGES_AND_FUNCTIONS_AUDIT.md §4 (Recommended Fixes) for fallback behaviour. Ensure APPLICATION_ROOT or blueprint url_prefix is `/vidgenerator` so paths match. After fixing: run `test_url_timing.py` again and confirm 404s are gone.

---

## 10. PAGES_AND_FUNCTIONS_AUDIT.md

| Check | Status | Severity | How to verify | Enrichment |
|-------|--------|----------|---------------|------------|
| Front page table | OK | High | Table matches FRONT_PAGE_URLS in test_url_timing.py | Doc links to CHECKPOINTS_RECHECK for full recheck |
| Profile page table | OK | High | Table matches PROFILE_PAGE_URLS | Note on production 404s and fallbacks |
| Fallbacks note | OK | High | §2 describes missing_endpoints fallbacks | — |
| Run audit command | OK | High | §5 has command + BASE_URL for production | — |

**Verify:** Compare PAGES_AND_FUNCTIONS_AUDIT tables with FRONT_PAGE_URLS / PROFILE_PAGE_URLS in scripts/test_url_timing.py.

---

## Quick commands

```bash
# URL timing (local or production)
python scripts/test_url_timing.py
set BASE_URL=https://masternoder.dk && python scripts/test_url_timing.py

# Agent skill sets (dry-run or run)
python scripts/add_agent_skill_sets_to_pages.py --dry-run
python scripts/add_agent_skill_sets_to_pages.py --version 20260305

# Deploy and restart (dry-run or full)
python scripts/deploy_all_and_restart_uwsgi.py --dry-run
python scripts/deploy_all_and_restart_uwsgi.py
```

---

## Cross-references

| Doc | Section | Purpose |
|-----|---------|---------|
| RESEARCH_AI_SYSTEMS.md | §8 | All API keys and provider links |
| RESEARCH_AI_SYSTEMS.md | §10 | Production & loading; 404 fix list |
| RESEARCH_AI_SYSTEMS.md | §11–12 | Optional keys; Profile & AI connections |
| PAGES_AND_FUNCTIONS_AUDIT.md | §1–2 | Front and profile URL tables |
| PAGES_AND_FUNCTIONS_AUDIT.md | §5 | Run audit command |
| CHECKPOINTS_RECHECK.md | §9 | Production 404 fix steps |
| DEPLOY_PREP.md | — | Recheck summary, fix_404 manifest, deploy commands, verify |

---

**Summary:** All implemented checkpoints are present and consistent. Enrichments add: "How to verify", "Enrichment" notes, severity, quick commands, and cross-references. Outstanding: production 404s (§9) — 9 endpoints (front page init, battle stats, agent skillset all, profile aggregated, user identity, account summary points, gallery recent, trophies list, battle PVP trophies). Use `logs/production_404_deploy_checklist.txt` after each URL timing run.
