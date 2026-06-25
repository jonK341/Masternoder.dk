# Discord Interactions Endpoint (MasterNoder2)

Discord can deliver slash commands, buttons, and other interactions via HTTP POST instead of the Gateway. This repo exposes the **Interactions Endpoint URL** used when you save that field in the [Discord Developer Portal](https://discord.com/developers/applications).

Reference: [Interactions and Activities](https://discord.com/developers/docs/interactions/overview) · [Request Verification](https://discord.com/developers/docs/interactions/receiving-and-responding#security-and-authorization)

---

## Interactions Endpoint URL (paste in Developer Portal)

**General Information → Interactions Endpoint URL:**

```
https://masternoder.dk/api/discord/interactions
```

When you save this URL, Discord sends a signed `PING` (`type: 1`). The server must respond with `{"type": 1}` (PONG). Signature verification uses your app **Public Key** from the same page.

---

## Required environment variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DISCORD_PUBLIC_KEY` | **Yes (production)** | 64-character hex Ed25519 public key from Developer Portal → General Information. Used to verify `X-Signature-Ed25519` + `X-Signature-Timestamp` on every POST. |
| `DISCORD_CLIENT_ID` | For slash commands later | Same as **Application ID** in the portal. Not read by the interactions route today; needed when registering commands via Discord API. |

Optional (outbound Discord — not the interactions endpoint itself):

- `DISCORD_BOT_TOKEN` — bot API calls, linked roles, future command registration
- `DISCORD_WEBHOOK_URL` / `DISCORD_CHANNEL_ID_*` — outbound posts (news, casino fan-out)
- `DISCORD_OPS_SECRET` — cron/ops routes under `/api/discord/*`

See `.env.example` (Discord section) and `docs/DISCORD_LINKED_ROLES.md` for linked-role OAuth vars.

**Public key format:** 64 hex chars; optional `0x` prefix and surrounding quotes are stripped. If unset locally, signature verify is skipped (tests only — **always set on production**).

---

## What the endpoint supports today

| Interaction `type` | Name | Response |
|--------------------|------|----------|
| `1` | PING | `200` + `{"type": 1}` |
| Other | — | `501` + `unsupported_interaction_type` |

**Slash commands:** not implemented yet. Casino activity reaches Discord via **webhook fan-out** (`POST /api/discord/casino/fanout` cron), not slash commands. Planned examples for a future pass: `/casino status`, `/casino jackpot`.

**Related routes (same blueprint):**

- `GET /api/discord/status` — webhook + interactions public-key diagnostics
- `POST /api/discord/post` — ops outbound message
- `POST /api/discord/casino/fanout` — casino activity → `#casino`
- Linked roles — see `docs/DISCORD_LINKED_ROLES.md`

Implementation: `backend/routes/discord_routes.py` · tests: `tests/unit/test_discord_interactions.py`

---

## Setup checklist

1. **Discord app** — use the same application as `DISCORD_CLIENT_ID` / bot.
2. **Copy Public Key** — Developer Portal → **General Information** → Public Key → set on server as `DISCORD_PUBLIC_KEY` (must match portal exactly).
3. **Deploy env + reload** — ensure production `.env` has the key, then reload uWSGI (e.g. `python scripts/deploy.py …` or your usual deploy path including `backend/routes/discord_routes.py`).
4. **Paste Interactions Endpoint URL** — `https://masternoder.dk/api/discord/interactions` → Save. Discord should show verification success (signed PING/PONG).
5. **Verify** — `GET https://masternoder.dk/api/discord/status` should show:
   - `interactions_public_key_configured: true`
   - `interactions_public_key_valid_length: true`
   - `interactions_endpoint: https://masternoder.dk/api/discord/interactions`
6. **Optional local signed probe** — `python scripts/_discord_signed_ping_local.py` (dev) or `python scripts/_discord_prod_signed_probe.py` (prod sanity check).

---

## Security notes

- Signatures are verified with Ed25519: `verify(signature, timestamp + raw_body)` per Discord docs.
- `signal_processor_middleware` skips JSON pre-processing on `/api/discord/interactions` so the raw body matches Discord’s signature.
- Nginx must forward `X-Signature-Ed25519` and `X-Signature-Timestamp` to uWSGI (inspect with `scripts/_nginx_discord_headers_remote.py` if verification fails behind the proxy).

---

## Deploy needed?

**Yes**, if production does not yet have:

- `backend/routes/discord_routes.py` (interactions route + signature verify), or
- `DISCORD_PUBLIC_KEY` in server `.env`, or
- a uWSGI reload after env changes.

After deploy, save the Interactions Endpoint URL in the portal (step 4 above). No separate Discord Gateway connection is required for HTTP interactions.
