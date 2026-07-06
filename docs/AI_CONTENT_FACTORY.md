# AI Content Factory for YouTube Growth + Monetization

This pipeline creates **new content continuously** from live trading signals and feeds your YouTube workflow.

## Components

- `scripts/ai_content_factory.py`
- `cron/ai_content_factory.sh`
- `cron/masternoder-ai-content-factory.cron.d`

It reads:

- `reports/trading_content/trading_content_report_latest.json`

And produces:

- long-form documentary job plans
- short-clip prompt jobs (vertical format meta)
- optional livestream trigger when enough jobs are created
- saved outputs under `reports/ai_content_factory/latest/`

## Why this beats static video paths

- Every run creates fresh concepts from newest metrics.
- Shorts + long-form are generated as separate AI workflows.
- Livestream can be triggered only when enough fresh material exists.

## Run modes

### Plan only (safe)

`python3 scripts/ai_content_factory.py --dry-run --print-json`

### Create generator jobs

`python3 scripts/ai_content_factory.py --print-json`

### Create jobs + auto schedule livestream when gate is met

`python3 scripts/ai_content_factory.py --create-live-on-gate --print-json`

## Cron automation

Install:

- copy `cron/masternoder-ai-content-factory.cron.d` to `/etc/cron.d/masternoder-ai-content-factory`

Runner:

- `cron/ai_content_factory.sh`

Schedule:

- `10 */10 * * *` (every 10 hours)

## Master wired pipeline (recommended)

Use one orchestrator job to run all stages in sequence:

- `cron/content_pipeline_master.sh`
- `cron/masternoder-content-pipeline.cron.d`

Order:

1. trading content report + platform news
2. ensure content API readiness (`cron/ensure_content_api.sh`)
3. AI content factory
4. YouTube content agent

Default behavior: continue even if one stage fails, but return non-zero when any stage failed.
Set `CONTENT_PIPELINE_FAIL_FAST=1` to stop on first failure.

API preflight tuning:

- `CONTENT_API_SYSTEMD_UNIT` (optional systemd unit to restart, e.g. your web app service)
- `CONTENT_API_START_CMD` (fallback tmux start command; default `python3 <repo>/run.py`)
- `CONTENT_API_TMUX_SESSION` (default `content-api-server`)
- `CONTENT_API_WAIT_SEC` (default `45`)

## Env tuning

- `CONTENT_FACTORY_DRY_RUN=1` (plan-only mode)
- `CONTENT_FACTORY_LONG_COUNT=1`
- `CONTENT_FACTORY_SHORT_COUNT=3`
- `CONTENT_FACTORY_CREATE_LIVE_ON_GATE=1`
- `CONTENT_FACTORY_LIVE_START_HOURS=24`
- `CONTENT_FACTORY_USER_ID=youtube_agent`
- `CONTENT_FACTORY_API_BASE=http://127.0.0.1:5000`

## Monetization loop

1. Run trading report generator.
2. Build AI content factory plan/jobs.
3. Generate fresh shorts + long-form outputs.
4. Upload strongest assets to YouTube.
5. Trigger livestream around newly generated assets.
6. Reuse output for X/LinkedIn/newsletter and CTA into paid offerings.
