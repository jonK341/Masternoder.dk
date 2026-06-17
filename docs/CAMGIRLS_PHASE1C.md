# Camgirls Phase 1c — production onboarding

Replace demo performers with real catalog entries. **Payout addresses come from the MN2 daemon** (`getnewaddress`), not performer JSON.

## Prerequisites

- Age gate live: `POST /api/camgirls/age-verify`
- MN2 daemon running with RPC auth (see [MN2_OPS.md](MN2_OPS.md))
- Ops secret set: `MN2_OPS_SECRET` (or local-only from 127.0.0.1)

## Option A — JSON batch (recommended)

1. Copy `data/camgirls_performers_production.template.json` — fill display names, bios, prices (no payout address).
2. Validate and apply:

```powershell
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.json --dry-run
python scripts/camgirls_onboard_performers.py --file data/camgirls_performers_production.json
python scripts/camgirls_onboard_performers.py --deactivate-demos
```

3. Provision daemon payout addresses (on server where daemon RPC works):

```powershell
python scripts/camgirls_provision_payout_addresses.py --remote --ask-pass
# or locally on server:
python scripts/camgirls_provision_payout_addresses.py
python scripts/deploy.py camgirls --ask-pass
```

Addresses are stored in `data/camgirls_payout_addresses.json` (one per performer, owned by the daemon wallet).

## Option B — Ops API (remote)

```bash
# Upsert performer (daemon address auto-provisioned when RPC available)
curl -s -X POST -H "X-Ops-Secret: $MN2_OPS_SECRET" -H "Content-Type: application/json" \
  -d '{"id":"performer_nova","display_name":"…","unlock_price_mn2":50,"chat_price_mn2":2,"active":true}' \
  https://masternoder.dk/api/camgirls/ops/performers

# List / provision payout addresses
curl -s -H "X-Ops-Secret: $MN2_OPS_SECRET" http://127.0.0.1:5000/api/camgirls/ops/payout-addresses
curl -s -X POST -H "X-Ops-Secret: $MN2_OPS_SECRET" http://127.0.0.1:5000/api/camgirls/ops/payout-addresses
```

## Phase 2 chat (shipped)

- `POST /api/camgirls/chat` — body `{ "performer_id", "message" }`
- Requires age verification + prior unlock
- Default **2 MN2/message** (override per performer with `chat_price_mn2`)

## Deploy

```powershell
python scripts/deploy.py camgirls --ask-pass
python scripts/camgirls_post_deploy_verify.py --remote-only --ask-pass
```

## Checklist before go-live

- [ ] Production performers in JSON (no manual payout addresses)
- [ ] `--deactivate-demos` run
- [ ] Daemon payout addresses provisioned (`camgirls_provision_payout_addresses.py`)
- [ ] Unlock/tip/chat smoke test with test user MN2 balance
- [ ] Age gate copy reviewed for jurisdiction

## Discord cross-road

Unlock/tip/chat events emit to `activity_events.jsonl` (`camgirl_unlock`, `camgirl_tip`, `camgirl_chat`) and surface in the M8 alert funnel (#53).

When announcing a new performer:

```bash
curl -s -X POST -H "X-Ops-Secret: $SECRET" -H "Content-Type: application/json" \
  -d '{"title":"New performer","summary":"…","href":"/camgirls/","channel":"market"}' \
  http://127.0.0.1:5000/api/discord/m8/partner-spotlight
```

See [DISCORD_CROSSROADS.md](DISCORD_CROSSROADS.md).
