<!-- ARCHIVED MONETIZATION_INVESTIGATION_CLOSEOUT.md — finished plan removed from active docs. -->

> **Archived:** 2026-06-17. Closeout doc — investigation complete.

# Monetization & COGS investigation — closeout (A+)

**Status:** Engineering hooks shipped; product tiers and PayPal Live remain operational follow-ups.  
**Companion:** [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md) (includes **§0 single metric**, **§10 status**), [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md), [PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md).

---

## 0. Single metric (north star)

*(Duplicated from [MONETIZATION_PAYPAL.md §0](./MONETIZATION_PAYPAL.md#0-single-metric-north-star) — edit both sections when changing.)*

Review **one** headline number each week so the playbook does not sprawl into dozens of KPIs.

### Headline KPI (pick one phase — then stick to it)

| Phase | Primary metric | How to get it |
|-------|----------------|---------------|
| **A — COGS honest** (now) | **Median `ratio_vs_reference_job`** over the last **7 days** in `metering.jsonl` | `python scripts/cogs_metering_report.py` or inspect rows; compare to [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md). Typical healthy band **~0.7–1.5** while the product mix stabilises — **investigate** sustained drift outside that band. |
| **B — Growth** | **Activation rate:** % of new accounts with **≥1** completed **`rich_video`** within **7 days** of signup | Join signup time → first successful job (`job_kind` / job store). Pairs with [MONETIZATION_PAYPAL.md §8.5](./MONETIZATION_PAYPAL.md#85-growth-global-not-dk-only). |
| **C — Paid** (packs/subs live) | **Blended gross margin on paid usage:** revenue attributed to billable jobs **minus** Σ `cogs_usd.total_usd` for those jobs, divided by revenue | **Beyond raw metering:** `metering.jsonl` gives **COGS per `job_id`**, not **which dollars** paid for which jobs. Phase **C** needs **revenue ↔ `job_id`** (or defensible user-period rollups) via **ledger + grants + subscription cycles** — see [MONETIZATION_PAYPAL.md §10 Attribution](./MONETIZATION_PAYPAL.md#10-implementation-status--next-steps). |

**Rule:** use **phase A** until real **`COGS_*`** from invoices and stable jobs exist; add **B** when acquisition matters; switch headline to **C** once PayPal/Stripe revenue is tied to usage.

### Two-line progress lens

| Track | Typical state (early 2026) |
|-------|----------------------------|
| **Measurement & COGS rails** | **Advanced** — LLM usage into metering, p50/p90 report, optional admin stats API. |
| **Monetised product surface** | **Early → mid** — packs, tiers (flagged), subs + shop, **SCR** ledger are in repo; **§8.2–8.5** roadmap: **habit loops** (no **automated** usage-vs-allowance nudges), **paid queue** (no **separate** subsystem; optional **`priority_tier`** future), **metered B2B API** ([MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md)). |

---

## Reference links (canonical)

| Topic | Document / code |
|--------|------------------|
| Revenue models & playbook | [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md) |
| Reference job & env `COGS_*` | [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md) |
| PayPal create/capture | [PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md) |
| Storage vs COGS | [VIDEO_STORAGE_STRATEGY.md](./VIDEO_STORAGE_STRATEGY.md) |
| LLM usage → job totals | `backend/services/llm_service.py` — `accumulate_llm_usage_from_response` |
| Bridge aggregation | `backend/services/video_ai_bridge.py` — `_accumulate_usage` |
| Rich video job config | `backend/services/video_generator_service.py` — `_llm_usage_totals`, `_video_cogs_metrics` |
| Metering log & stats | `backend/services/cogs_metering_service.py` — `record_completed_video_job`, `summarize_metering_jsonl` |
| HTTP (reference + summary + metering) | `backend/routes/cogs_routes.py` |
| CLI report | `scripts/cogs_metering_report.py` |

---

## Conclusion

1. **Unit economics** are now anchored on **real LLM token totals** when providers return `usage` on `LLMResponse`: planning and enhancement calls aggregate into `config["_llm_usage_totals"]`, merged into `_video_cogs_metrics["llm_tokens_actual"]`, and written to `metering.jsonl` with **`llm_tokens_source`: `actual` | `heuristic`** and **`llm_tokens_for_cogs`**. When usage is missing, the existing **heuristic** still applies — so COGS is strictly better, never worse.

2. **Operational visibility**: `summarize_metering_jsonl()` powers **`python scripts/cogs_metering_report.py`** and optionally **`GET /api/system/cogs/metering-stats`** (requires **`COGS_ADMIN_REPORT_KEY`** and header **`X-Cogs-Admin-Key`**). Use **p90** for caps and subscription allowances, not the mean ([MONETIZATION_PAYPAL.md §8.1](./MONETIZATION_PAYPAL.md)).

3. **Remaining high-impact work** (not all automated here): tier **enforcement** before job start, **PayPal Subscriptions**, **queue priority** for paid users, and **storage path** discipline per [VIDEO_STORAGE_STRATEGY.md](./VIDEO_STORAGE_STRATEGY.md).

---

## Button notes (UI / product copy)

Use these as **primary actions** and **labels** so checkout and settings stay aligned with COGS language.

| Button / CTA | Label (suggested) | Notes |
|----------------|-------------------|--------|
| Primary purchase | **Buy credits** | Tie to reference fractions in help text. |
| Secondary | **See usage & limits** | Deep-link to future usage page; until then, link to stats or account. |
| PayPal checkout | **Pay with PayPal** | Must show **final USD** before redirect ([PAYPAL_INTEGRATION_GUIDE.md](./PAYPAL_INTEGRATION_GUIDE.md)). |
| Upgrade | **Upgrade plan** | Maps to Creator/Pro caps when implemented. |
| Admin / ops | **COGS report** | Run `scripts/cogs_metering_report.py` or secured metering-stats API. |

**Microcopy:** *“1 credit ≈ ¼ of a standard generation”* — adjust when `REFERENCE_JOB_SPEC` changes; keep in sync with [REFERENCE_JOB_COGS.md](./REFERENCE_JOB_COGS.md).

---

## Deploy checklist

*(Same block as [MONETIZATION_PAYPAL.md §9](./MONETIZATION_PAYPAL.md#9-deploy-checklist) — edit both when changing.)*

### Minimum (required for COGS + LLM metering in production)

Deploy these paths to the app root (e.g. `/var/www/html/` on the server):

| # | Path |
|---|------|
| 1 | `backend/services/cogs_metering_service.py` |
| 2 | `backend/services/video_ai_bridge.py` |
| 3 | `backend/services/llm_service.py` |
| 4 | `backend/services/video_generator_service.py` |
| 5 | `backend/routes/cogs_routes.py` |
| 6 | `backend/services/monetization_config_service.py`, `monetization_ledger_service.py`, `monetization_tier_service.py` |
| 7 | `backend/routes/shop_routes.py`, `paypal_routes.py`, `missing_endpoints_routes.py` |
| 8 | `data/monetization_config.json` |

Then **restart** the Python/uWSGI stack so routes and services reload.

**Automation:** the repo root **`deploy.py`** already lists the above (plus optional files below) in `FILES_TO_DEPLOY` — run `python deploy.py` from the project root after a pull to upload and restart.

### Optional

| Path | When |
|------|------|
| `scripts/cogs_metering_report.py` | Run **p50/p90** reports on the server via SSH (`python scripts/cogs_metering_report.py`). Not required for the web app to serve traffic. |
| `docs/MONETIZATION_PAYPAL.md`, `docs/MONETIZATION_INVESTIGATION_CLOSEOUT.md`, `docs/REFERENCE_JOB_COGS.md`, other `docs/*.md` | Documentation only; no runtime dependency. |

### Metering stats API (optional)

If you call **`GET /api/system/cogs/metering-stats`**:

1. On the server, set in `.env` (or the environment uWSGI reads):

   `COGS_ADMIN_REPORT_KEY=<long random secret>`

2. Request with the same value:

   - Header: **`X-Cogs-Admin-Key: <secret>`**, or  
   - Query: **`?key=<secret>`**

If **`COGS_ADMIN_REPORT_KEY`** is unset, the endpoint returns **503** (`metering_stats_disabled`). See `.env.example` for the variable name.

### Verify

- `GET /api/system/cogs/summary` — should return reference + rates (no auth).  
- After a completed rich video, **`logs/cogs/metering.jsonl`** should gain rows with **`llm_tokens_source`** when providers return usage.  
- `python scripts/cogs_metering_report.py` — prints aggregates when the log file exists.
