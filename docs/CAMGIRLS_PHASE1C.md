# Camgirls Phase 1c — production onboarding

Replace demo performers with real catalog entries and verified payout addresses.

## Prerequisites

- Age gate live: `POST /api/camgirls/age-verify`
- Ops secret set: `MN2_OPS_SECRET` (or local-only from 127.0.0.1)
- MN2 wallet rails working for unlock/tip/chat debits

## Option A — JSON batch (recommended)

1. Copy `data/camgirls_performers_production.template.json` and fill in real values.
2. Validate:

```powershell
python scripts/camgirls_onboard_performers.py --file data/your_performers.json --dry-run
```

3. Apply locally or on server (same app process / data dir):

```powershell
python scripts/camgirls_onboard_performers.py --file data/your_performers.json
```

## Option B — Ops API (remote)

```bash
curl -s -X POST -H "X-Ops-Secret: $MN2_OPS_SECRET" -H "Content-Type: application/json" \
  -d '{"id":"performer_1","display_name":"…","unlock_price_mn2":50,"chat_price_mn2":2,"payout_address":"J…","active":true}' \
  https://masternoder.dk/api/camgirls/ops/performers
```

## Phase 2 chat (shipped)

- `POST /api/camgirls/chat` — body `{ "performer_id", "message" }`
- Requires age verification + prior unlock
- Default **2 MN2/message** (override per performer with `chat_price_mn2`)
- UI: **Chat** button on unlocked cards at `/camgirls/`

## Deploy

```powershell
python scripts/deploy.py camgirls --ask-pass
```

## Checklist before go-live

- [ ] Fill `data/camgirls_performers_production.template.json` with real performers
- [ ] Run onboard script (see commands below)
- [ ] Deactivate demos: `python scripts/camgirls_onboard_performers.py --deactivate-demos`
- [ ] Payout addresses verified on-chain
- [ ] Unlock/tip/chat smoke test with test user MN2 balance
- [ ] Post-deploy verify: `python scripts/camgirls_post_deploy_verify.py`
- [ ] Age gate copy reviewed for jurisdiction

## Onboard commands

```powershell
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.template.json --dry-run
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.template.json
python scripts/camgirls_onboard_performers.py --deactivate-demos
python scripts/deploy.py camgirls --ask-pass
python scripts/camgirls_post_deploy_verify.py
```
